#!/bin/bash 

DOCKER_VERSION=19.03

sudo apt-get update 
sudo apt-get install -y build-essential git 

until (curl https://releases.rancher.com/install-docker/${DOCKER_VERSION}.sh | sudo sh); do
  echo 'docker did not install correctly'                                          
  sleep 2   
done

sudo usermod -aG docker ubuntu
