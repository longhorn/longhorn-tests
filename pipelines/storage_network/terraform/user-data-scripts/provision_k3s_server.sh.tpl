#!/bin/bash

set -e

# Sometimes, registration fails on the first boot, which causes the default repositories to be missing from zypper,
# preventing it from installing any packages.
# In some cases, even manually executing systemctl restart guestregister can fail.
sudo systemctl restart guestregister || true
if ! SUSEConnect --status 2>/dev/null | grep -q "Registered"; then
  sudo systemctl enable guestregister.service || true
  sudo registercloudguest --force-new || true
fi
sudo zypper --gpg-auto-import-keys ref
sudo zypper install -y open-iscsi nfs-client cryptsetup device-mapper samba jq git go

sudo mkdir -p /etc/certs
sudo ln -s /var/lib/ca-certificates/ca-bundle.pem /etc/certs/ca-certificates.crt
sudo ln -s /var/lib/ca-certificates/pem /etc/ssl/certs

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

ipv6_public_ip=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
private_ipv4=$(hostname -I | awk '{print $1}')

case "${network_stack}" in
  ipv6)
    k3s_server_public_ip="$ipv6_public_ip"
    ;;
  dual-stack-ipv6-first)
    k3s_server_public_ip="$ipv6_public_ip"
    dual_stack_node_ip="$ipv6_public_ip,$private_ipv4"
    # NOTE: the AWS Elastic IP (control_plane_ipv4) is NAT'd and is not
    # assigned to any local network interface, so it must not be used for
    # --node-ip/--node-external-ip (kubelet validates these against the
    # host's interfaces). Use the actual private ipv4 address instead, and
    # only use the elastic IP for --tls-san below.
    dual_stack_external_ip="$ipv6_public_ip,$private_ipv4"
    dual_stack_cluster_cidr="fd00:10::/56,10.42.0.0/16"
    dual_stack_service_cidr="fd00:20::/112,10.43.0.0/16"
    ;;
  dual-stack-ipv4-first)
    k3s_server_public_ip="${control_plane_ipv4}"
    dual_stack_node_ip="$private_ipv4,$ipv6_public_ip"
    # See note above: do not use the NAT'd Elastic IP here.
    dual_stack_external_ip="$private_ipv4,$ipv6_public_ip"
    dual_stack_cluster_cidr="10.42.0.0/16,fd00:10::/56"
    dual_stack_service_cidr="10.43.0.0/16,fd00:20::/112"
    ;;
  *)
    k3s_server_public_ip="${control_plane_ipv4}"
    ;;
esac

K3S_EXEC="server \
  --tls-san $k3s_server_public_ip \
  --write-kubeconfig-mode 644 \
  --token ${k3s_cluster_secret}"

if [[ "${network_stack}" == "ipv6" ]]; then
  K3S_EXEC="$K3S_EXEC \
    --node-ip $k3s_server_public_ip \
    --flannel-ipv6-masq \
    --cluster-cidr=fd00:10::/56 \
    --service-cidr=fd00:20::/112"
elif [[ "${network_stack}" == dual-stack-* ]]; then
  K3S_EXEC="$K3S_EXEC \
    --tls-san ${control_plane_ipv4} \
    --tls-san $ipv6_public_ip \
    --node-ip $dual_stack_node_ip \
    --node-external-ip $dual_stack_external_ip \
    --flannel-ipv6-masq \
    --cluster-cidr=$dual_stack_cluster_cidr \
    --service-cidr=$dual_stack_service_cidr"
fi

if [[ "${network_stack}" == "ipv6" || "${network_stack}" == dual-stack-* ]]; then
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
