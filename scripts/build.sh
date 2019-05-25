#!/bin/bash

docker build -f Dockerfile.setup -t "${JOB_NAME}${BUILD_NUMBER}" .
