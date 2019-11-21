#!/bin/bash 

LONGHORN_MANAGER_REPO_URI="https://github.com/longhorn/longhorn-manager.git"
LONGHORN_MANAGER_BRANCH="master"
LONGHORN_MANAGER_TMPDIR="/tmp/longhorn-manager"

LONGHORN_MANIFEST="/tmp/longhorn-master.yml"

UPGRADE_IMAGE_TAG=${1:-"master"}

check_longhorn_status() {
  RETRIES=0
  while [[ -n "`kubectl get pods -n longhorn-system  | grep "instance-manager-.*\|longhorn-\(manager\|driver\|csi\)\|engine-image-.*" | awk '{print $3}' | grep -v Running`"  ]]; do
    sleep 1m
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}


mkdir -p ${LONGHORN_MANAGER_TMPDIR}

git clone --quiet --single-branch --branch ${LONGHORN_MANAGER_BRANCH} ${LONGHORN_MANAGER_REPO_URI} ${LONGHORN_MANAGER_TMPDIR}

for FILE in `find "${LONGHORN_MANAGER_TMPDIR}/deploy/install" -type f -name "*\.yaml" | sort`; do
    cat "${FILE}" >> "${LONGHORN_MANIFEST}"
    echo "---"    >> "${LONGHORN_MANIFEST}"
done

LONGHORN_MANAGER_IMAGE_TAG=`grep -io "longhornio\/longhorn-manager:.*$" "${LONGHORN_MANIFEST}" | head -1 | awk -F ":" '{print $2}'`
LONGHORN_ENGINE_IMAGE_TAG=`grep -io "longhornio\/longhorn-engine:.*$" "${LONGHORN_MANIFEST}" | head -1 | awk -F ":" '{print $2}'`


sed -i 's/longhornio\/longhorn-manager:'${LONGHORN_MANAGER_IMAGE_TAG}'/longhornio\/longhorn-manager:'${UPGRADE_IMAGE_TAG}'/' "${LONGHORN_MANIFEST}"
sed -i 's/longhornio\/longhorn-engine:'${LONGHORN_ENGINE_IMAGE_TAG}'/longhornio\/longhorn-engine:'${UPGRADE_IMAGE_TAG}'/' "${LONGHORN_MANIFEST}"

kubectl apply -f "${LONGHORN_MANIFEST}" > /dev/null

check_longhorn_status
