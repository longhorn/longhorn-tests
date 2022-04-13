#!/usr/bin/env bash

set -x
set -e


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
  wget "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_VERSION}/deploy/longhorn.yaml" -P ${TF_VAR_tf_workspace}
  kubectl apply -f "${TF_VAR_tf_workspace}/longhorn.yaml"
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
  install_longhorn

  run_fio_local_path_test

  adjust_replica_count 1
  run_fio_longhorn_test 1

  adjust_replica_count 2
  run_fio_longhorn_test 2

  adjust_replica_count 3
  run_fio_longhorn_test 3

}

main
