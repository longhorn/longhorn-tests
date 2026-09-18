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
sudo zypper install -y open-iscsi nfs-client jq

sudo mkdir -p /etc/certs
sudo ln -s /var/lib/ca-certificates/ca-bundle.pem /etc/certs/ca-certificates.crt
sudo ln -s /var/lib/ca-certificates/pem /etc/ssl/certs

sudo systemctl -q enable iscsid
sudo systemctl start iscsid

ipv6_public_ip=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
private_ipv4=$(hostname -I | awk '{print $1}')

case "${network_stack}" in
  ipv6)
    k3s_server_public_ip="$ipv6_public_ip"
    ;;
  dual-stack-ipv6-first)
    k3s_server_public_ip="$ipv6_public_ip"
    dual_stack_node_ip="$ipv6_public_ip,$private_ipv4"
    dual_stack_external_ip="$ipv6_public_ip,${control_plane_ipv4}"
    dual_stack_cluster_cidr="fd00:10::/56,10.42.0.0/16"
    dual_stack_service_cidr="fd00:20::/112,10.43.0.0/16"
    ;;
  dual-stack-ipv4-first)
    k3s_server_public_ip="${control_plane_ipv4}"
    dual_stack_node_ip="$private_ipv4,$ipv6_public_ip"
    dual_stack_external_ip="${control_plane_ipv4},$ipv6_public_ip"
    dual_stack_cluster_cidr="10.42.0.0/16,fd00:10::/56"
    dual_stack_service_cidr="10.43.0.0/16,fd00:20::/112"
    ;;
  *)
    k3s_server_public_ip="${control_plane_ipv4}"
    ;;
esac

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
  echo -e "net.ipv6.conf.eth0.accept_ra = 2\nnet.ipv6.conf.default.accept_ra = 2\nnet.ipv6.conf.all.forwarding = 1" | tee /etc/sysctl.d/99-ipv6.conf
  sysctl --system
  cat <<EOF > /etc/resolv.conf
nameserver 2606:4700:4700::1111
nameserver 2001:4860:4860::8888
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
  chattr +i /etc/resolv.conf || true
fi

if [[ "${cni}" != "default" ]]; then
  K3S_EXEC="$K3S_EXEC \
    --flannel-backend=none \
    --disable-network-policy"
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="$K3S_EXEC" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

until kubectl get nodes >/dev/null 2>&1; do
  echo "Waiting for k3s startup"
  sleep 5
done


if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi