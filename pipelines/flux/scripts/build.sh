#!/bin/bash

docker build --no-cache -f ./pipelines/flux/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
