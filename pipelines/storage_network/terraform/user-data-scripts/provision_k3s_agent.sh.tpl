#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client cryptsetup go
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

modprobe uio
modprobe uio_pci_generic
modprobe vfio_pci
modprobe nvme-tcp
modprobe dm_crypt
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
nvme-tcp
dm_crypt
EOF

echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf

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
