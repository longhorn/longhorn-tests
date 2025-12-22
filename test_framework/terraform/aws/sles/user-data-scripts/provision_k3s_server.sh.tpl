#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client jq

sudo mkdir -p /etc/certs
sudo ln -s /var/lib/ca-certificates/ca-bundle.pem /etc/certs/ca-certificates.crt
sudo ln -s /var/lib/ca-certificates/pem /etc/ssl/certs

sudo systemctl -q enable iscsid
sudo systemctl start iscsid

if [[ "${network_stack}" == "ipv6" ]]; then
  k3s_server_public_ip=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
else
  k3s_server_public_ip="${control_plane_ipv4}"
fi

K3S_EXEC="server \
  --node-taint node-role.kubernetes.io/control-plane:NoSchedule \
  --tls-san $k3s_server_public_ip \
  --write-kubeconfig-mode 644 \
  --token ${k3s_cluster_secret}"

if [[ "${network_stack}" == "ipv6" ]]; then
  K3S_EXEC="$K3S_EXEC \
    --node-ip $k3s_server_public_ip \
    --flannel-ipv6-masq \
    --cluster-cidr=fd00:10::/56 \
    --service-cidr=fd00:20::/112"
  echo -e "net.ipv6.conf.eth0.accept_ra = 2\nnet.ipv6.conf.default.accept_ra = 2" | tee /etc/sysctl.d/99-ipv6.conf
  sysctl --system
  cat <<EOF > /etc/resolv.conf
nameserver 2606:4700:4700::1111
nameserver 2001:4860:4860::8888
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
  chattr +i /etc/resolv.conf || true
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="$K3S_EXEC" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
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

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi