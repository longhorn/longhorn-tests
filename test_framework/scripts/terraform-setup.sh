#!/usr/bin/env bash

set -x

if [[ ${TF_VAR_k8s_distro_name} == "gke" ]]; then
  gcloud auth activate-service-account --project=${TF_VAR_gcp_project} --key-file=${TF_VAR_gcp_auth_file}
  gcloud auth list
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

if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw load_balancer_url > ${TF_VAR_tf_workspace}/load_balancer_url
fi

exit $?
