#!/bin/bash

docker build --no-cache -f ./pipelines/fleet/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
