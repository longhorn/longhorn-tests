#!/bin/bash

docker build --no-cache -f ./test_framework/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
