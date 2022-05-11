#!/bin/bash

docker build --no-cache -f ./airgap/Dockerfile.setup -t "airgap-${JOB_BASE_NAME}-${BUILD_NUMBER}" .
