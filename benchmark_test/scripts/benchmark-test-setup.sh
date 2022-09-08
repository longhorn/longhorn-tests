#!/usr/bin/env bash

set -x
set -e

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}

set_kubeconfig_envvar(){
  ARCH=${1}
  BASEDIR=${2}

  if [[ ${ARCH} == "amd64" ]] ; then
    if [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE] ]]; then
      export KUBECONFIG="${BASEDIR}/kube_config_rke.yml"
    elif [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE]2 ]]; then
      export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/rke2.yaml"
    else
      export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/k3s.yaml"
    fi
  elif [[ ${ARCH} == "arm64"  ]]; then
    export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/k3s.yaml"
  fi
}


wait_local_path_provisioner_status_running(){
  local RETRY_COUNTS=10  # in seconds
  local RETRY_INTERVAL="10s"

  RETRIES=0
  while [[ -n `kubectl get pods -n local-path-storage --no-headers | awk '{print $3}' | grep -v Running` ]]; do
    echo "local-path-provisioner is still installing ... re-checking in 10s"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: local-path-provisioner installation timeout"; exit 1 ; fi
  done
}


install_local_path_provisioner(){
  kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.22/deploy/local-path-storage.yaml
  wait_local_path_provisioner_status_running
}


generate_longhorn_yaml_manifest(){
  MANIFEST_BASEDIR="${1}"

  LONGHORN_REPO_URI=${LONGHORN_REPO_URI:-"https://github.com/longhorn/longhorn.git"}
  LONGHORN_REPO_BRANCH=${LONGHORN_REPO_BRANCH:-"master"}
  LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

  CUSTOM_LONGHORN_MANAGER_IMAGE=${CUSTOM_LONGHORN_MANAGER_IMAGE:-"longhornio/longhorn-manager:master-head"}
  CUSTOM_LONGHORN_ENGINE_IMAGE=${CUSTOM_LONGHORN_ENGINE_IMAGE:-"longhornio/longhorn-engine:master-head"}

  CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE:-""}

  git clone --single-branch \
            --branch ${LONGHORN_REPO_BRANCH} \
            ${LONGHORN_REPO_URI} \
            ${LONGHORN_REPO_DIR}

  cat "${LONGHORN_REPO_DIR}/deploy/longhorn.yaml" > "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # get longhorn default images from yaml manifest
  LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`

  # replace longhorn images with custom images
  sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use instance-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use share-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use backing-image-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi
}


wait_longhorn_status_running(){
  local RETRY_COUNTS=10  # in minutes
  local RETRY_INTERVAL="1m"

  RETRIES=0
  while [[ -n `kubectl get pods -n longhorn-system --no-headers | awk '{print $3}' | grep -v Running` ]]; do
    echo "Longhorn is still installing ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done
}


install_longhorn(){
  LONGHORN_MANIFEST_FILE_PATH="${1}"

  kubectl apply -f "${LONGHORN_MANIFEST_FILE_PATH}"
  wait_longhorn_status_running
}


adjust_test_size(){
  PVC_SIZE="$((TEST_SIZE/10+TEST_SIZE))Gi"
  TEST_SIZE="${TEST_SIZE}G"
  yq -i e "select(.kind == \"PersistentVolumeClaim\").spec.resources.requests.storage=\"${PVC_SIZE}\"" "${TF_VAR_tf_workspace}/scripts/fio-longhorn.yaml"
  yq -i e "select(.kind == \"PersistentVolumeClaim\").spec.resources.requests.storage=\"${PVC_SIZE}\"" "${TF_VAR_tf_workspace}/scripts/fio-local-path.yaml"
  yq -i e "select(.kind == \"Job\").spec.template.spec.containers[0].env[2].value=\"${TEST_SIZE}\"" "${TF_VAR_tf_workspace}/scripts/fio-longhorn.yaml"
  yq -i e "select(.kind == \"Job\").spec.template.spec.containers[0].env[2].value=\"${TEST_SIZE}\"" "${TF_VAR_tf_workspace}/scripts/fio-local-path.yaml"
}


adjust_replica_count(){
  COUNT=${1}
  REPLACEMENT="numberOfReplicas: \"${COUNT}\""
  sed -i -r "s/numberOfReplicas: \"[0-9]+\"/${REPLACEMENT}/" "${TF_VAR_tf_workspace}/longhorn.yaml"
  kubectl apply -f "${TF_VAR_tf_workspace}/longhorn.yaml"
  if [[ -z `kubectl get sc longhorn -o yaml | grep "${REPLACEMENT}"` ]]; then
    echo "set ${REPLACEMENT} error!"
    exit 1
  else
    echo "set ${REPLACEMENT} succeed!"
  fi
}


wait_fio_running(){
  local RETRY_COUNTS=10  # in seconds
  local RETRY_INTERVAL="10s"

  RETRIES=0
  while [[ -n `kubectl get pods -l kbench=fio --no-headers | awk '{print $3}' | grep -v Running` ]]; do
    echo "wait for kbench running ... re-checking in 10s"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: wait for kbench running timeout"; exit 1 ; fi
  done
}


run_fio_cmp_test(){
  kubectl apply -f "${TF_VAR_tf_workspace}/scripts/fio-cmp.yaml"
  wait_fio_running
  kubectl logs -l kbench=fio -f
  kubectl delete -f "${TF_VAR_tf_workspace}/scripts/fio-cmp.yaml"
}


run_fio_local_path_test(){
  kubectl apply -f "${TF_VAR_tf_workspace}/scripts/fio-local-path.yaml"
  wait_fio_running
  kubectl logs -l kbench=fio -f
  kubectl delete -f "${TF_VAR_tf_workspace}/scripts/fio-local-path.yaml"
}


run_fio_longhorn_test(){
  COUNT=${1}
  yq -i 'select(.spec.template != null).spec.template.spec.containers[0].env[0].value="longhorn-'${COUNT}'-replicas"' "${TF_VAR_tf_workspace}/scripts/fio-longhorn.yaml"
  kubectl apply -f "${TF_VAR_tf_workspace}/scripts/fio-longhorn.yaml"
  wait_fio_running
  kubectl logs -l kbench=fio -f
  kubectl delete -f "${TF_VAR_tf_workspace}/scripts/fio-longhorn.yaml"
}


main(){
  set_kubeconfig_envvar ${TF_VAR_arch} ${TF_VAR_tf_workspace}

  adjust_test_size

  install_local_path_provisioner

  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
  install_longhorn "${TF_VAR_tf_workspace}/longhorn.yaml"

  run_fio_local_path_test

  adjust_replica_count 3
  run_fio_longhorn_test 3

  adjust_replica_count 2
  kubectl cordon "$(kubectl get nodes | awk 'NR!=1 && $3!~/control-plane/ {print $1}' | awk 'NR==3')"
  run_fio_longhorn_test 2

  adjust_replica_count 1
  kubectl cordon "$(kubectl get nodes | awk 'NR!=1 && $3!~/control-plane/ {print $1}' | awk 'NR==2')"
  run_fio_longhorn_test 1

}

main
