#!/usr/bin/env bash

set -x

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

if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw load_balancer_url > test_framework/load_balancer_url
fi

if [[ "${TF_VAR_k8s_distro_name}" == "k3s" ]]; then
  terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw instance_mapping | jq 'map({(.name | split(".")[0]): .id}) | add' | jq -s add > /tmp/instance_mapping
fi

exit $?
