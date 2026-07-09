#!/bin/bash

K3S_EXEC="server \
  --node-taint node-role.kubernetes.io/control-plane:NoSchedule \
  --tls-san ${k3s_server_public_ip} \
  --write-kubeconfig-mode 644 \
  --token ${k3s_cluster_secret}"

if [[ "${cni}" != "default" ]]; then
  K3S_EXEC="$K3S_EXEC \
    --flannel-backend=none \
    --disable-network-policy"
fi

curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="$K3S_EXEC" INSTALL_K3S_VERSION="${k3s_version}" sh -
sudo systemctl start k3s

until kubectl get nodes >/dev/null 2>&1; do
  echo "Waiting for k3s startup"
  sleep 5
done

if [[ "${cni}" == "calico" ]]; then
  kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.0/manifests/calico.yaml
elif [[ "${cni}" == "cilium" ]]; then
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
  curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
  chmod 700 get_helm.sh
  ./get_helm.sh
  helm install cilium oci://quay.io/cilium/charts/cilium \
    --version 1.19.5 \
    --set operator.replicas=1 \
    --set mtu=9001 \
    --set bpf.masquerade=true \
    --set hostFirewall.enabled=false \
    --set endpointRoutes.enabled=true \
    --set ipam.mode=kubernetes \
    --namespace kube-system
fi

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/suse/.ssh/authorized_keys
fi