#!/bin/bash

docker build --no-cache -f ./cleanup/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
