#!/bin/bash

set -x

SEVERITY=${1}
LONGHORN_VERSION=${2}

mkdir -p /junit-reports /templates

wget "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_VERSION}/deploy/longhorn-images.txt"
IMAGES=($(< longhorn-images.txt))

wget -O /templates/junit.tpl https://raw.githubusercontent.com/longhorn/longhorn-tests/master/secscan/templates/junit.tpl

for IMAGE in "${IMAGES[@]}"; do
	IMAGE_NAME=`echo "${IMAGE}" | awk -F"/" '{print $NF}' | tr ':' '-'`
	sed "s/LONGHORN_IMAGE_NAME/${IMAGE_NAME}/" /templates/junit.tpl > /templates/junit-${IMAGE_NAME}.tpl

	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /templates/junit-${IMAGE_NAME}.tpl:/contrib/junit.tpl -v /junit-reports:/root/ aquasec/trivy image  --severity ${SEVERITY} --format template --template "@/contrib/junit.tpl" -o /root/${IMAGE_NAME}-junit-report.xml ${IMAGE}

done

