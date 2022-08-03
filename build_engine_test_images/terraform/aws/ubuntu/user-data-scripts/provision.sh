#!/bin/bash 

DOCKER_VERSION=20.10

sudo apt-get update 
sudo apt-get install -y build-essential git nfs-common jq docker.io

sudo usermod -aG docker ubuntu
