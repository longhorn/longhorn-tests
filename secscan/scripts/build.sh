#!/bin/bash

docker build --no-cache -f ./secscan/Dockerfile.setup -t "${JOB_NAME}${BUILD_NUMBER}" .
