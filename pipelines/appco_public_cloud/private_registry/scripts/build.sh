#!/bin/bash

docker build --no-cache -f ./pipelines/appco_public_cloud/private_registry/Dockerfile.setup -t "private-registry-${JOB_BASE_NAME}-${BUILD_NUMBER}" .
