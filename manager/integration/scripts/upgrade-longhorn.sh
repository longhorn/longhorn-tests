#!/bin/bash

set -x

LONGHORN_REPO_URI="${1}"
LONGHORN_REPO_BRANCH="${2}"
CUSTOM_LONGHORN_MANAGER_IMAGE="${3}"
CUSTOM_LONGHORN_ENGINE_IMAGE="${4}"
CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${5}"
CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${6}"
CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${7}"

LONGHORN_REPO_DIR="/tmp/longhorn"
rm -rf "${LONGHORN_REPO_DIR}/"
LONGHORN_MANIFEST="/tmp/longhorn.yml"

LONGHORN_NAMESPACE="longhorn-system"

wait_longhorn_status_running(){
  # retry for 10 minutes
  local RETRY_COUNTS=10
  local RETRY_INTERVAL="1m"
                                                                      
  RETRIES=0
  while [[ -n `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers | awk '{print $3}' | grep -v "Running\|Completed"` ]]; do
    echo "Longhorn is still installing ... re-checking in ${RETRY_INTERVAL}"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))
    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then
      echo "Error: longhorn installation timeout"
      exit 1
    fi
  done
  echo "Longhorn finished installing"
}

git clone --single-branch \
          --branch ${LONGHORN_REPO_BRANCH} \
          ${LONGHORN_REPO_URI} \
          ${LONGHORN_REPO_DIR}

cat "${LONGHORN_REPO_DIR}/deploy/longhorn.yaml" > "${LONGHORN_MANIFEST}"
sed -i ':a;N;$!ba;s/---\n---/---/g' "${LONGHORN_MANIFEST}"

LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${LONGHORN_MANIFEST}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${LONGHORN_MANIFEST}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${LONGHORN_MANIFEST}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${LONGHORN_MANIFEST}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${LONGHORN_MANIFEST}"| head -1 | sed -e 's/^"//' -e 's/"$//'`

CUSTOM_LONGHORN_MANAGER_IMAGE=${CUSTOM_LONGHORN_MANAGER_IMAGE:-"${LONGHORN_MANAGER_IMAGE}"}
CUSTOM_LONGHORN_ENGINE_IMAGE=${CUSTOM_LONGHORN_ENGINE_IMAGE:-"${LONGHORN_ENGINE_IMAGE}"}
CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE:-"${LONGHORN_INSTANCE_MANAGER_IMAGE}"}
CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE:-"${LONGHORN_SHARE_MANAGER_IMAGE}"}
CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE:-"${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"}

# replace longhorn images with custom images
sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST}"
sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${LONGHORN_MANIFEST}"
sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST}"
sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST}"
sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST}"

kubectl apply -f "${LONGHORN_MANIFEST}"
wait_longhorn_status_running
