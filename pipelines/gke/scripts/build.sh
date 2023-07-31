#!/bin/bash

docker build --no-cache -f ./pipelines/gke/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
