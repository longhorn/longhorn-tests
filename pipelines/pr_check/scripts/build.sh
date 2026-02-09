#!/bin/bash

docker build --no-cache -f ./pipelines/pr_check/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
