#!/bin/bash

docker build -f ./test_framework/Dockerfile.setup -t "${JOB_NAME}${BUILD_NUMBER}" .
