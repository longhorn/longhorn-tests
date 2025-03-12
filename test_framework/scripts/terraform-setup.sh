#!/usr/bin/env bash

set -x

source test_framework/scripts/kubeconfig.sh

terraform_setup(){
  if [[ ${TF_VAR_k8s_distro_name} == "aks" ]] || [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
    DISTRO=${TF_VAR_k8s_distro_name}
  fi

  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color

  if [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "aws" ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw controlplane_public_ip > /tmp/controlplane_public_ip
  elif [[ ${LONGHORN_TEST_CLOUDPROVIDER} == "harvester" ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw kube_config > ${TF_VAR_tf_workspace}/kube_config.yaml
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw cluster_id > /tmp/cluster_id
    until [ "$(KUBECONFIG=${TF_VAR_tf_workspace}/kube_config.yaml kubectl get nodes -o jsonpath='{.items[*].status.conditions}' | jq '.[] | select(.type  == "Ready").status' | grep -ci true)" -eq 4 ]; do
      echo "waiting for harvester cluster nodes to be running"
      sleep 2
    done
    KUBECONFIG=${TF_VAR_tf_workspace}/kube_config.yaml kubectl get nodes --no-headers --selector=node-role.kubernetes.io/control-plane -owide | awk '{print $6}' > /tmp/controlplane_public_ip
    KUBECONFIG=${TF_VAR_tf_workspace}/kube_config.yaml kubectl get nodes --no-headers -ojson | jq '.items[].metadata.name' | tr -d '"' > /tmp/instance_mapping
    jq -Rn 'reduce inputs as $line ({}; .[$line] = $line)' /tmp/instance_mapping | sponge /tmp/instance_mapping
  fi

  if [[ ${TF_VAR_k8s_distro_name} == "rke" ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color -refresh-only
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw rke_config > ${TF_VAR_tf_workspace}/rke.yml
    sleep 30
    rke up --config ${TF_VAR_tf_workspace}/rke.yml
  fi

  if [[ ${TF_VAR_k8s_distro_name} == "aks" ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw kubeconfig > ${TF_VAR_tf_workspace}/aks.yml
    sleep 120
  fi

  if [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw kubeconfig > ${TF_VAR_tf_workspace}/eks.yml
  fi

  if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw load_balancer_url > ${TF_VAR_tf_workspace}/load_balancer_url
  fi
}

terraform_setup
set_kubeconfig
