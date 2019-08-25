#!/bin/bash

docker build --no-cache -f ./test_framework/Dockerfile.setup -t "${JOB_NAME}${BUILD_NUMBER}" .
