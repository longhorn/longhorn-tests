#!/bin/bash

sudo zypper ref -y
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi docker nfs-client
sudo usermod -aG docker ec2-user
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

mkfs.ext4 -E nodiscard /dev/nvme1n1
mkdir /mnt/sda1
mount /dev/nvme1n1 /mnt/sda1

mkdir /mnt/sda1/local
mkdir /opt/local-path-provisioner
mount --bind /mnt/sda1/local /opt/local-path-provisioner

mkdir /mnt/sda1/longhorn
mkdir /var/lib/longhorn
mount --bind /mnt/sda1/longhorn /var/lib/longhorn
