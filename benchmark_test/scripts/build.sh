#!/bin/bash

docker build --no-cache -f ./benchmark_test/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
