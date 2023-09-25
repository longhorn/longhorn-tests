#!/usr/bin/env bash

set -x

source test_framework/scripts/kubeconfig.sh
source test_framework/scripts/cleanup.sh

terraform_setup(){
  if [[ ${TF_VAR_k8s_distro_name} == "aks" ]] || [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
    DISTRO=${TF_VAR_k8s_distro_name}
  fi

  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color

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


if [[ "${BASH_SOURCE[0]}" -ef "$0" ]]; then
  CLUSTER_READY=false
  MAX_RETRY=3
  RETRY=0
  while [[ "${CLUSTER_READY}" == false ]] && [[ ${RETRY} -lt ${MAX_RETRY} ]]; do
    terraform_setup
    set_kubeconfig
    if ! kubectl get pods -A | grep -q 'Running'; then
      cleanup
      RETRY=$((RETRY+1))
    else
      CLUSTER_READY=true
    fi
  done
  if [[ "${CLUSTER_READY}" == false ]]; then
    exit 1
  fi
fi
