#!/bin/bash

docker build --no-cache -f ./pipelines/storage_network/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
