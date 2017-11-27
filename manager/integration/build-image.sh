#!/bin/bash

version=$(./scripts/version)
image="rancher/longhorn-manager-test:${version}"
docker build -t ${image} .
echo Built image ${image}
