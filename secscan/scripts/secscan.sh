#!/bin/bash

SEVERITY=${1}

mkdir -p /junit-reports /templates

REPO="longhornio"
IMAGES=("longhorn-manager" "longhorn-engine" "longhorn-instance-manager" "longhorn-ui" "longhorn-share-manager" "backing-image-manager")
TAG="master"

wget -O /templates/junit.tpl https://raw.githubusercontent.com/longhorn/longhorn-tests/master/secscan/templates/junit.tpl

for IMAGE in ${IMAGES[@]}; do
	sed "s/LONGHORN_IMAGE_NAME/${IMAGE}/" /templates/junit.tpl > /templates/junit-${IMAGE}.tpl

	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /templates/junit-${IMAGE}.tpl:/contrib/junit.tpl -v /junit-reports:/root/ aquasec/trivy image  --severity ${SEVERITY} --format template --template "@/contrib/junit.tpl" -o /root/${IMAGE}-junit-report.xml ${REPO}/${IMAGE}:${TAG}

done

