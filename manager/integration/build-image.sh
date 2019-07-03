#!/bin/bash

REPO=${REPO:-longhornio}

version=$(./scripts/version)
image="$REPO/longhorn-manager-test:${version}"
docker build -t ${image} .
mkdir -p bin
echo ${image} > bin/latest_image
echo Built image ${image}
