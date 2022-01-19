#!/bin/bash

docker build --no-cache -f ./build_engine_test_images/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
