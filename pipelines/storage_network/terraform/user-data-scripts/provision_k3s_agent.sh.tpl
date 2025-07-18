#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client cryptsetup go
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

# TODO: It looks like "set -e" will break the intended functionality of the remaining code. Consider a refactor.
set +e

if [[ "${network_stack}" == "ipv6" ]]; then
  tee /etc/sysctl.d/99-ipv6.conf > /dev/null <<EOF
net.ipv6.conf.eth0.accept_ra = 2
net.ipv6.conf.eth1.accept_ra = 2
net.ipv6.conf.default.accept_ra = 2
net.ipv6.conf.all.forwarding = 1
net.ipv6.conf.eth1.forwarding = 1
net.ipv6.conf.all.proxy_ndp = 1
net.ipv6.conf.eth0.proxy_ndp = 1
net.ipv6.conf.eth1.proxy_ndp = 1
net.ipv6.conf.cni0.proxy_ndp = 1
EOF
  sysctl --system
  cat <<EOF > /etc/resolv.conf
nameserver 2606:4700:4700::1111
nameserver 2001:4860:4860::8888
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
  chattr +i /etc/resolv.conf || true
  IP=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
else
  IP=$(hostname -I | awk '{print $1}')
fi

# TODO: It looks like "set -e" will break the intended functionality of the remaining code. Consider a refactor.
set +e

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --node-ip=$IP --token ${k3s_cluster_secret}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done

if [[ "${thick_plugin}" == true ]]; then
  mkdir -p /etc/cni
  ln -s /var/lib/rancher/k3s/agent/etc/cni/net.d /etc/cni/net.d
  mkdir -p /opt/cni
  ln -s /var/lib/rancher/k3s/data/cni /opt/cni/bin
fi

mkdir -p /tmp/gocache
export GOCACHE=/tmp/gocache
git clone https://github.com/c3y1huang/cni-plugins.git
cd cni-plugins
git checkout 6888978
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /var/lib/rancher/k3s/data/cni/ipvlan ./plugins/main/ipvlan
