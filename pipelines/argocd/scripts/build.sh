#!/bin/bash

docker build --no-cache -f ./pipelines/argocd/Dockerfile.setup -t "${JOB_BASE_NAME}-${BUILD_NUMBER}" .
