#!/bin/bash
ACCESS_MODE_RWO="ReadWriteOnce"
ACCESS_MODE_RWX="ReadWriteMany"
CONFIG_FILE="config.yaml"
OUTPUT_FILE="data.output"
DEPLOYMENT_TEMPLATE="deployment.yaml"
STATEFULSET_TEMPLATE="statefulset.yaml"
RWO_DEPLOYMENT_WORKLOAD_PREFIX="test-data-rwo-deployment-"
RWX_DEPLOYMENT_WORKLOAD_PREFIX="test-data-rwx-deployment-"
RWO_STATEFULSET_NAME="test-data-rwo-statefulset"
RWX_STATEFULSET_NAME="test-data-rwx-statefulset"
RETRY_COUNTS=60
RETRY_INTERVAL=5
RETRY_INTERVAL_LONG=10

######################################################
# Log
######################################################
export RED='\x1b[0;31m'
export GREEN='\x1b[38;5;22m'
export CYAN='\x1b[36m'
export YELLOW='\x1b[33m'
export NO_COLOR='\x1b[0m'

if [ -z "${LOG_TITLE}" ]; then
  LOG_TITLE=''
fi
if [ -z "${LOG_LEVEL}" ]; then
  LOG_LEVEL="INFO"
fi

debug() {
  if [[ "${LOG_LEVEL}" == "DEBUG" ]]; then
    local log_title
    if [ -n "${LOG_TITLE}" ]; then
     log_title="(${LOG_TITLE})"
    else
     log_title=''
    fi
    echo -e "${GREEN}[DEBUG]${log_title} ${NO_COLOR}$1"
  fi
}

info() {
  if [[ "${LOG_LEVEL}" == "DEBUG" ]] ||\
     [[ "${LOG_LEVEL}" == "INFO" ]]; then
    local log_title
    if [ -n "${LOG_TITLE}" ]; then
     log_title="(${LOG_TITLE})"
    else
     log_title=''
    fi
    echo -e "${CYAN}[INFO] ${log_title} ${NO_COLOR}$1"
  fi
}

warn() {
  if [[ "${LOG_LEVEL}" == "DEBUG" ]] ||\
     [[ "${LOG_LEVEL}" == "INFO" ]] ||\
     [[ "${LOG_LEVEL}" == "WARN" ]]; then
    local log_title
    if [ -n "${LOG_TITLE}" ]; then
     log_title="(${LOG_TITLE})"
    else
     log_title=''
    fi
    echo -e "${YELLOW}[WARN] ${log_title} ${NO_COLOR}$1"
  fi
}

error() {
  if [[ "${LOG_LEVEL}" == "DEBUG" ]] ||\
     [[ "${LOG_LEVEL}" == "INFO" ]] ||\
     [[ "${LOG_LEVEL}" == "WARN" ]] ||\
     [[ "${LOG_LEVEL}" == "ERROR" ]]; then
    local log_title
    if [ -n "${LOG_TITLE}" ]; then
     log_title="(${LOG_TITLE})"
    else
     log_title=''
    fi
    echo -e "${RED}[ERROR]${log_title} ${NO_COLOR}$1"
  fi
}

######################################################
# Check Logics
######################################################
check_local_dependencies() {
  local targets=($@)

  local all_found=true
  for ((i=0; i<${#targets[@]}; i++)); do
    local target=${targets[$i]}
    if [ "$(which $target)" = "" ]; then
      all_found=false
      error "Not found: $target"
    fi
  done
  
  if [ "$all_found" = "false" ]; then
    msg="Please install missing dependencies: ${targets[@]}."
    info "$msg"
    exit 1
  fi

  msg="Required dependencies '${targets[@]}' are installed."
  info "$msg"
}

check_config_input() {
    NAMESPACE=$(yq eval '.namespace' config.yaml)
    STORAGE_SIZE=$(yq eval '.storage' config.yaml)
    STORAGE_CLASS_NAME=$(yq eval '.storageClass' config.yaml)
    DATA_SIZE_IN_MB=$(yq eval '.dataSizeInMb' config.yaml)
    STATEFULSET_RWO_REPLICAS=$(yq eval '.statefulSet.rwo.replicas' config.yaml)
    STATEFULSET_RWX_REPLICAS=$(yq eval '.statefulSet.rwx.replicas' config.yaml)
    DEPLOYMENT_RWO_COUNTS=$(yq eval '.deployment.rwo.pvCounts' config.yaml)
    DEPLOYMENT_RWX_COUNTS=$(yq eval '.deployment.rwx.pvCounts' config.yaml)
    DEPLOYMENT_RWX_REPLICAS=$(yq eval '.deployment.rwx.deploymentReplicas' config.yaml)

    msg="$CONFIG_FILE is not correct, please check"
    # varialbe = "null" when yq not find yaml field
    [ "$STORAGE_SIZE" = "null" -o ${#STORAGE_SIZE} -eq 0 ] && error "$msg" && exit 2
    [ "$NAMESPACE" = "null" -o ${#NAMESPACE} -eq 0 ] && error "$msg" && exit 2
    [ "$STORAGE_CLASS_NAME" = "null" -o ${#STORAGE_CLASS_NAME} -eq 0 ] && error "$msg" && exit 2
    [ "$DATA_SIZE_IN_MB" = "null" -o ${#DATA_SIZE_IN_MB} -eq 0 ] && error "$msg" && exit 2
    [ "$STATEFULSET_RWO_REPLICAS" = "null" -o ${#STATEFULSET_RWO_REPLICAS} -eq 0 ] && error "$msg" && exit 2
    [ "$STATEFULSET_RWX_REPLICAS" = "null" -o ${#STATEFULSET_RWX_REPLICAS} -eq 0 ] && error "$msg" && exit 2
    [ "$DEPLOYMENT_RWO_COUNTS" = "null" -o ${#DEPLOYMENT_RWO_COUNTS} -eq 0 ] && error "$msg" && exit 2
    [ "$DEPLOYMENT_RWX_COUNTS" = "null" -o ${#DEPLOYMENT_RWX_COUNTS} -eq 0 ] && error "$msg" && exit 2
    [ "$DEPLOYMENT_RWX_REPLICAS" = "null" -o ${#DEPLOYMENT_RWX_REPLICAS} -eq 0 ] && error "$msg" && exit 2
}

check_kubernetes_resources() {
    if ! kubectl get storageclass "$STORAGE_CLASS_NAME" &> /dev/null; then
        msg="StorageClass '$STORAGE_CLASS_NAME' does not exist."
        error "$msg"
        exit 1
    fi

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        msg="Namespace '$NAMESPACE' does not exist."
        error "$msg"
        exit 1
    fi  
}

wait_workload_ready() {
  local workload_type=$1
  local workload_name=$2
  local workload_replicas=$3
  local retries=0
  while [[ -n `kubectl -n $NAMESPACE get $workload_type --no-headers | grep $workload_name | awk '{print $2}' | grep -v $workload_replicas/$workload_replicas` ]]; do
    msg="Pod is still creating ... re-checking in ${RETRY_INTERVAL}s"
    info "$msg"
    sleep ${RETRY_INTERVAL}
    retries=$((RETRIES+1))

    if [[ ${retries} -eq ${RETRY_COUNTS} ]]; then echo "Error: Pod create timeout"; exit 1 ; fi
  done


}

record_pod_data() {
    local pattern="$1"
    local pod_names=($(kubectl -n $NAMESPACE get pods | grep $pattern | cut -d ' ' -f1))
    # wait md5sum stable in case data is large
    for pod_name in "${pod_names[@]}"; do
      for ((i=0; i<=$RETRY_COUNTS; i++)); do
        local md5_temp1=$(kubectl -n $NAMESPACE exec -it $pod_name -- /bin/sh -c "md5sum /mnt/data/data" | cut -d ' ' -f1)
        sleep ${RETRY_INTERVAL_LONG}
        local md5_temp2=$(kubectl -n $NAMESPACE exec -it $pod_name -- /bin/sh -c "md5sum /mnt/data/data" | cut -d ' ' -f1)
        if [ "${md5_temp1}" != "${md5_temp2}" ]; then
          continue
        else
          local md5=${md5_temp1}
          break
        fi
      done
      msg="${pod_name} data md5: ${md5}"
      info "$msg"
      echo $pod_name >> $OUTPUT_FILE
      echo $md5 >> $OUTPUT_FILE
      echo "" >> $OUTPUT_FILE
    done
}

######################################################
# Workloads
######################################################
create_deployments() {
    local deployment_type=$1
    if [ "${deployment_type}" == "rwo" ]; then
        local deployment_replica=1
        local access_mode=$ACCESS_MODE_RWO
        local deployment_cnt=$DEPLOYMENT_RWO_COUNTS
        local deployment_prefix=$RWO_DEPLOYMENT_WORKLOAD_PREFIX
    elif [ "${deployment_type}" == "rwx" ]; then
        local deployment_replica=$DEPLOYMENT_RWX_REPLICAS
        local access_mode=$ACCESS_MODE_RWX
        local deployment_cnt=$DEPLOYMENT_RWX_COUNTS
        local deployment_prefix=$RWX_DEPLOYMENT_WORKLOAD_PREFIX
    fi

    local command="[\"-c\", \"if [ ! -f /mnt/data/data ]; then dd if=/dev/urandom of=/mnt/data/data bs=1M count=${DATA_SIZE_IN_MB}; fi; trap : TERM INT; sleep infinity & wait\"]" 
    for (( i=1; i<=$deployment_cnt; i++)) do
        local deployment_name="${deployment_prefix}$i"
        local pvc_name="pvc-${deployment_name}"

        yq -i e "select(.kind == \"PersistentVolumeClaim\").metadata.name = \"${pvc_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"PersistentVolumeClaim\").metadata.namespace = \"${NAMESPACE}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"PersistentVolumeClaim\").spec.accessModes[0] = \"${access_mode}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"PersistentVolumeClaim\").spec.resources.requests.storage = \"${STORAGE_SIZE}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"PersistentVolumeClaim\").spec.storageClassName = \"${STORAGE_CLASS_NAME}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").metadata.name = \"${deployment_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").metadata.namespace = \"${NAMESPACE}\"" "${DEPLOYMENT_TEMPLATE}" 
        yq -i e "select(.kind == \"Deployment\").metadata.labels.name = \"${deployment_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.replicas = ${deployment_replica}" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.selector.matchLabels.name = \"${deployment_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.template.metadata.labels.name = \"${deployment_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.template.spec.containers[0].name = \"${deployment_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.template.spec.volumes[0].persistentVolumeClaim.claimName = \"${pvc_name}\"" "${DEPLOYMENT_TEMPLATE}"
        yq -i e "select(.kind == \"Deployment\").spec.template.spec.containers[0].args = ${command}" "${DEPLOYMENT_TEMPLATE}"
        kubectl apply -f ${DEPLOYMENT_TEMPLATE}
        wait_workload_ready "deployment" $deployment_name $deployment_replica

    done

    record_pod_data $deployment_prefix
}

create_statefulsets() {
    local stateful_type=$1
    local command="[\"-c\", \"dd if=/dev/urandom of=/mnt/data/data bs=1M count=${DATA_SIZE_IN_MB}; trap : TERM INT; sleep infinity & wait\"]"
    if [ "${stateful_type}" == "rwo" ]; then
      local statefulset_cnt=$STATEFULSET_RWO_REPLICAS
      local access_mode=$ACCESS_MODE_RWO
      local statefulset_name=$RWO_STATEFULSET_NAME
    elif [ "${stateful_type}" == "rwx" ]; then
      local statefulset_cnt=$STATEFULSET_RWX_REPLICAS
      local access_mode=$ACCESS_MODE_RWX
      local statefulset_name=$RWX_STATEFULSET_NAME
    fi

    if [ "$statefulset_cnt" -eq 0 ]; then
      return
    fi
  
    yq -i e "select(.kind == \"StatefulSet\").metadata.name = \"${statefulset_name}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").metadata.namespace = \"${NAMESPACE}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.selector.matchLabels.app = \"${statefulset_name}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.serviceName = \"${statefulset_name}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.template.metadata.labels.app = \"${statefulset_name}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.replicas = ${statefulset_cnt}" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.template.spec.containers[0].name = \"${statefulset_name}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.template.spec.containers[0].args = ${command}" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.volumeClaimTemplates[0].spec.accessModes[0] = \"${access_mode}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.volumeClaimTemplates[0].spec.storageClassName = \"${STORAGE_CLASS_NAME}\"" "${STATEFULSET_TEMPLATE}"
    yq -i e "select(.kind == \"StatefulSet\").spec.volumeClaimTemplates[0].spec.resources.requests.storage = \"${STORAGE_SIZE}\"" "${STATEFULSET_TEMPLATE}"
    kubectl apply -f ${STATEFULSET_TEMPLATE}

    wait_workload_ready "statefulset" $statefulset_name $statefulset_cnt
    record_pod_data $statefulset_name
}

######################################################
# Main logics
######################################################
echo "" > $OUTPUT_FILE
DEPENDENCIES=("kubectl" "yq")
check_local_dependencies "${DEPENDENCIES[@]}"
check_config_input
check_kubernetes_resources
create_statefulsets "rwo"
create_statefulsets "rwx"
create_deployments "rwo"
create_deployments "rwx"
