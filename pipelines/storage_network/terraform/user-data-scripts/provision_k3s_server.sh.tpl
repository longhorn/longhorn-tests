#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client jq cryptsetup
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

if [ -b "/dev/nvme1n1" ]; then
  mkfs.ext4 -E nodiscard /dev/nvme1n1
  mkdir /mnt/sda1
  mount /dev/nvme1n1 /mnt/sda1

  mkdir /mnt/sda1/local
  mkdir /opt/local-path-provisioner
  mount --bind /mnt/sda1/local /opt/local-path-provisioner

  mkdir /mnt/sda1/longhorn
  mkdir /var/lib/longhorn
  mount --bind /mnt/sda1/longhorn /var/lib/longhorn
elif [ -b "/dev/xvdh" ]; then
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --tls-san ${k3s_server_public_ip} --write-kubeconfig-mode 644 --token ${k3s_cluster_secret}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

RETRY=0
MAX_RETRY=180
until (kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for k3s startup'
  sleep 5
  if [ $RETRY -eq $MAX_RETRY ]; then
    break
  fi
  RETRY=$((RETRY+1))
done

if [[ "${thick_plugin}" == true ]]; then
  ln -s /var/lib/rancher/k3s/agent/etc/cni/net.d /etc/cni
  ln -s /var/lib/rancher/k3s/data/current/bin /opt/cni
fi

curl -OL https://github.com/containernetworking/plugins/releases/download/v1.3.0/cni-plugins-linux-amd64-v1.3.0.tgz
tar -zxvf cni-plugins-linux-amd64-v1.3.0.tgz
cp ipvlan /var/lib/rancher/k3s/data/current/bin/