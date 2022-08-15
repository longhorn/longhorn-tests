#!/bin/bash 

DOCKER_VERSION=20.10

echo PubkeyAcceptedKeyTypes=+ssh-rsa >> /etc/ssh/sshd_config
service ssh reload

sudo apt-get update 
sudo apt-get install -y build-essential git nfs-common

if [ -b "/dev/xvdh" ]; then
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi

until (curl https://releases.rancher.com/install-docker/${DOCKER_VERSION}.sh | sudo sh); do
  echo 'docker did not install correctly'                                          
  sleep 2   
done

sudo usermod -aG docker ubuntu
