#!/usr/bin/env bash

set -x

# terraform encountered a self-signed untrusted certificate when attempting to connect to the HAL API
# underlying HTTP request became stuck during SSL/TLS certificate validation, eventually leading to a timeout.
# we need to temporarily trust or ignore the HAL self-signed certificate
if [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "harvester" ]]; then
  openssl s_client -showcerts -connect rancher.10.115.253.200.sslip.io:443 </dev/null 2>/dev/null | openssl x509 -outform PEM > /tmp/rancher.crt
  cp /tmp/rancher.crt /usr/local/share/ca-certificates/rancher.crt
  update-ca-certificates
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  while ! terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve; do
    echo "Terraform failed, retrying in 10 seconds..."
    sleep 10
  done
else
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color
fi

if [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "aws" ]]; then
  if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw load_balancer_url > test_framework/load_balancer_url
  fi
  if [[ "${TF_VAR_k8s_distro_name}" == "k3s" || "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw instance_mapping | jq 'map({(.name | split(".")[0]): .id}) | add' | jq -s add > /tmp/instance_mapping
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw public_ip_mapping | jq 'map({(.name | split(".")[0]): .ip}) | add' | jq -s add > /tmp/public_ip_mapping
  fi
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw controlplane_public_ip > /tmp/controlplane_public_ip
elif [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "harvester" ]]; then
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw kube_config > test_framework/kube_config.yaml
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw cluster_id > /tmp/cluster_id
  until [ "$(KUBECONFIG=${PWD}/test_framework/kube_config.yaml kubectl get nodes -o jsonpath='{.items[*].status.conditions}' | jq '.[] | select(.type  == "Ready").status' | grep -ci true)" -eq 4 ]; do
    echo "waiting for harvester cluster nodes to be running"
    sleep 2
  done
  KUBECONFIG=${PWD}/test_framework/kube_config.yaml kubectl get nodes --no-headers --selector=node-role.kubernetes.io/control-plane -owide | awk '{print $6}' > /tmp/controlplane_public_ip
  KUBECONFIG=${PWD}/test_framework/kube_config.yaml kubectl get nodes --no-headers -ojson | jq '.items[].metadata.name' | tr -d '"' > /tmp/instance_mapping
  jq -Rn 'reduce inputs as $line ({}; .[$line] = $line)' /tmp/instance_mapping | sponge /tmp/instance_mapping
  KUBECONFIG=${PWD}/test_framework/kube_config.yaml kubectl get nodes -o json | jq '
  .items
  | map({
      (.spec.providerID | split("/")[-1]):
      (
        .status.addresses[]
        | select(.type=="InternalIP")
        | .address
      )
    })
  | add
' > /tmp/public_ip_mapping
fi

exit $?
