#!/bin/bash

docker build --no-cache -f ./pipelines/e2e/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
