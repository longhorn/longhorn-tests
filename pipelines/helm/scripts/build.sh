#!/bin/bash

docker build --no-cache -f ./pipelines/helm/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
