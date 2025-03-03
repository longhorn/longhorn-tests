#!/bin/bash

docker build --no-cache -f ./pipelines/appco/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
