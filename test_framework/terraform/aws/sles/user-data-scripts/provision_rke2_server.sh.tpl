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
sudo zypper install -y open-iscsi nfs-client jq iptables

sudo mkdir -p /etc/certs
sudo ln -s /var/lib/ca-certificates/ca-bundle.pem /etc/certs/ca-certificates.crt
sudo ln -s /var/lib/ca-certificates/pem /etc/ssl/certs

sudo systemctl -q enable iscsid
sudo systemctl start iscsid

ipv6_public_ip=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
private_ipv4=$(hostname -I | awk '{print $1}')

if [[ "${network_stack}" == "ipv6" || "${network_stack}" == dual-stack-* ]]; then
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

case "${network_stack}" in
  ipv6)
    rke2_server_public_ip="$ipv6_public_ip"
    ;;
  dual-stack-ipv6-first)
    rke2_server_public_ip="$ipv6_public_ip"
    dual_stack_node_ip="$ipv6_public_ip,$private_ipv4"
    dual_stack_external_ip="$ipv6_public_ip,${control_plane_ipv4}"
    dual_stack_cluster_cidr="fd00:10::/56,10.42.0.0/16"
    dual_stack_service_cidr="fd00:20::/112,10.43.0.0/16"
    ;;
  dual-stack-ipv4-first)
    rke2_server_public_ip="${control_plane_ipv4}"
    dual_stack_node_ip="$private_ipv4,$ipv6_public_ip"
    dual_stack_external_ip="${control_plane_ipv4},$ipv6_public_ip"
    dual_stack_cluster_cidr="10.42.0.0/16,fd00:10::/56"
    dual_stack_service_cidr="10.43.0.0/16,fd00:20::/112"
    ;;
  *)
    rke2_server_public_ip="${control_plane_ipv4}"
    ;;
esac

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="server" INSTALL_RKE2_VERSION="${rke2_version}" sh -

mkdir -p /etc/rancher/rke2

cat << EOF > /etc/rancher/rke2/config.yaml
write-kubeconfig-mode: "0644"
token: ${rke2_cluster_secret}
tls-san:
  - $rke2_server_public_ip
node-taint:
  - "node-role.kubernetes.io/control-plane:NoSchedule"
EOF

if [[ "${network_stack}" == "ipv6" ]]; then
  cat << EOF >> /etc/rancher/rke2/config.yaml
advertise-address: $rke2_server_public_ip
node-ip: "$rke2_server_public_ip"
cluster-cidr: fd00:10::/56
service-cidr: fd00:20::/112
EOF
elif [[ "${network_stack}" == dual-stack-* ]]; then
  cat << EOF >> /etc/rancher/rke2/config.yaml
tls-san:
  - ${control_plane_ipv4}
  - $ipv6_public_ip
node-ip: "$dual_stack_node_ip"
node-external-ip: "$dual_stack_external_ip"
cluster-cidr: "$dual_stack_cluster_cidr"
service-cidr: "$dual_stack_service_cidr"
EOF
fi

if [[ "${cni}" != "default" ]]; then
  cat << EOF >> /etc/rancher/rke2/config.yaml
cni: ${cni}
EOF
fi

# RKE2 IPv6-only Cilium networking:
# https://docs.rke2.io/networking/basic_network_options#ipv6-setup
if [[ "${network_stack}" == "ipv6" && "${cni}" == "cilium" ]]; then
  mkdir -p /var/lib/rancher/rke2/server/manifests
  cat << EOF > /var/lib/rancher/rke2/server/manifests/rke2-cilium-config.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: rke2-cilium
  namespace: kube-system
spec:
  valuesContent: |-
    routingMode: tunnel
    tunnelProtocol: vxlan
    underlayProtocol: ipv6
EOF
fi

if [ "${cis_hardening}" == true ]; then
    cat << EOF > /etc/sysctl.d/60-rke2-cis.conf
vm.panic_on_oom=0
vm.overcommit_memory=1
kernel.panic=10
kernel.panic_on_oops=1
EOF
    systemctl restart systemd-sysctl
    useradd -r -c "etcd user" -s /sbin/nologin -M etcd -U
    cat << EOF >> /etc/rancher/rke2/config.yaml
profile: "cis"
kube-apiserver-arg:
  - 'service-account-extend-token-expiration=false'
EOF
fi

systemctl enable rke2-server.service
systemctl start rke2-server.service

# TODO: It looks like "set -e" will break the intended functionality of the remaining code. Consider a refactor.
set +e

RETRY=0
MAX_RETRY=180
until (KUBECONFIG=/etc/rancher/rke2/rke2.yaml /var/lib/rancher/rke2/bin/kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for rke2 startup'
  sleep 5
  if [ $RETRY -eq $MAX_RETRY ]; then
    break
  fi
  RETRY=$((RETRY+1))
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi
