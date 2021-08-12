#!/bin/bash 

DOCKER_VERSION=20.10

apt-get update && apt-get install -y build-essential git

curl https://releases.rancher.com/install-docker/${DOCKER_VERSION}.sh | sh
