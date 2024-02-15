#!/usr/bin/env bash

set -x

if [[ ${TF_VAR_k8s_distro_name} == "aks" ]] || [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
  DISTRO=${TF_VAR_k8s_distro_name}
fi

if [[ ${TF_VAR_arch} == "amd64" ]]; then
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color
  if [[ ${TF_VAR_k8s_distro_name} =~ [rR][kK][eE] ]]; then
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color -refresh-only
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw rke_config > ${TF_VAR_tf_workspace}/rke.yml
    sleep 30
    rke up --config ${TF_VAR_tf_workspace}/rke.yml
  fi
else
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color
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

exit $?
