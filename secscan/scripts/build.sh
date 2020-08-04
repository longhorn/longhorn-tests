#!/bin/bash

docker build --no-cache -f ./secscan/Dockerfile.setup -t "${JOB_BASE_NAME}${BUILD_NUMBER}" .
