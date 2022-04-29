#!/bin/bash

docker build --no-cache -f ./mirror_csi_images/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
