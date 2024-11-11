#!/usr/bin/env bash

set -x

if [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "harvester" ]]; then
  source pipelines/utilities/vpn.sh
  connect_to_vpn
fi

if [[ ${TF_VAR_arch} == "amd64" ]]; then
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color
  if [[ ${TF_VAR_k8s_distro_name} == "rke" ]]; then
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color -refresh-only
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw rke_config > test_framework/rke.yml
    sleep 30
    rke up --config test_framework/rke.yml
  fi
else
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color
fi

if [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "aws" ]]; then
  if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw load_balancer_url > test_framework/load_balancer_url
  fi
  if [[ "${TF_VAR_k8s_distro_name}" == "k3s" ]]; then
    terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw instance_mapping | jq 'map({(.name | split(".")[0]): .id}) | add' | jq -s add > /tmp/instance_mapping
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
fi

exit $?
