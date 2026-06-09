#!/bin/bash

set -x

mkdir -p /junit-reports /templates

if [[ "${LONGHORN_VERSION}" =~ "oci://dp.apps.rancher.io/charts/suse-storage" ]]; then
  set +x
  helm registry login dp.apps.rancher.io --username "${APPCO_USERNAME}" --password "${APPCO_PASSWORD}"
  set -x
  helm pull "${LONGHORN_VERSION}" --untar --untardir "${PWD}"
  yq '.images[].image' ./suse-storage/images-lock.yaml > "longhorn-images.txt"
elif [[ "${LONGHORN_VERSION}" =~ ".txt" ]]; then
  wget -O longhorn-images.txt "${LONGHORN_VERSION}"
else
  wget "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_VERSION}/deploy/longhorn-images.txt"
fi

IMAGES=($(< longhorn-images.txt))

wget -O /templates/junit.tpl https://raw.githubusercontent.com/longhorn/longhorn-tests/master/secscan/templates/junit.tpl

docker image prune -af
docker login -u "${APPCO_USERNAME}" -p "${APPCO_PASSWORD}" dp.apps.rancher.io

for IMAGE in "${IMAGES[@]}"; do
	IMAGE_NAME=`echo "${IMAGE}" | awk -F"/" '{print $NF}' | tr ':' '-'`
	sed "s/LONGHORN_IMAGE_NAME/${IMAGE_NAME}/" /templates/junit.tpl > /templates/junit-${IMAGE_NAME}.tpl
  # docker pull the private image first, then run trivy against the already-pulled image
  docker pull ${IMAGE}
  trivy image \
    --severity "${SEVERITY}" \
    --format template \
    --template "@/templates/junit-${IMAGE_NAME}.tpl" \
    -o "/junit-reports/${IMAGE_NAME}-junit-report.xml" \
    "${IMAGE}"
done
