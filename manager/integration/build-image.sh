#!/bin/bash

version=$(./scripts/version)
image="rancher/longhorn-manager-test:${version}"
docker build -t ${image} .
mkdir -p bin
echo ${image} > bin/latest_image
echo Built image ${image}
