#!/bin/bash
set -x

LONGHORN_UNINSTALL_URI="${1}"
LONGHORN_DEPLOY_URI="${2}"
LONGHORN_NAMESPACE="longhorn-system"
LONGHORN_UNINSTALL_JOB="longhorn-uninstall"

wait_uninstall_job_complete(){
  local RETRY_COUNTS=10
  local RETRY_INTERVAL="30s"

  # In v1.3.x, uninstall job worked in default namespace. V1.4.x changed to namespace longhorn-system
  if [[ `kubectl get job -n ${LONGHORN_NAMESPACE} | grep longhorn-uninstall` ]]
  then
    LONGHORN_UNINSTALL_JOB_NAMESPACE=${LONGHORN_NAMESPACE}
  else
    LONGHORN_UNINSTALL_JOB_NAMESPACE="default"
  fi

  RETRIES=0
  while [[ -n `kubectl get job ${LONGHORN_UNINSTALL_JOB} -n ${LONGHORN_UNINSTALL_JOB_NAMESPACE} --no-headers | awk '{print $2}' | grep -v "1/1"` ]]; do
    echo "Longhorn is still uninstalling ... re-checking in ${RETRY_INTERVAL}"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))
    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then
      echo "Error: longhorn uninstall job timeout"
      exit 1
    fi
  done
  echo "Longhorn uninstall job completed"

}

wait_lh_namespace_terminated(){
  local RETRY_COUNTS=10
  local RETRY_INTERVAL="30s"

  RETRIES=0
  while [[ -n `kubectl get ns --no-headers | awk '{print $1}' | grep ${LONGHORN_NAMESPACE}` ]]; do
    echo "Namespace ${LONGHORN_NAMESPACE} is still terminating ... re-checking in ${RETRY_INTERVAL}"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))
    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then
      echo "Error: Namespace ${LONGHORN_NAMESPACE} terminate timeout"
      exit 1
    fi
  done
  echo "Namespace ${LONGHORN_NAMESPACE} terminated"

}

check_no_longorn_crd_remain(){
  COUNT=`kubectl get crd | grep longhorn | wc -l`
  echo "There are $COUNT Longhorn CRDs present"
  if [ $COUNT -gt 0 ]; then
    exit 1
  fi

}

kubectl create -f "${LONGHORN_UNINSTALL_URI}"
wait_uninstall_job_complete

kubectl delete -f "${LONGHORN_DEPLOY_URI}"
kubectl delete -f "${LONGHORN_UNINSTALL_URI}"
wait_lh_namespace_terminated
check_no_longorn_crd_remain