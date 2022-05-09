#!/usr/bin/env bash

set -x

if [[ ${TF_VAR_arch} == "amd64" ]]; then
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color
  
  if [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE] ]]; then
      terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color -refresh-only
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} output -raw rke_config > ${TF_VAR_tf_workspace}/rke.yml
    sleep 30
    rke up --config ${TF_VAR_tf_workspace}/rke.yml
  fi
else
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} init
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color
fi

exit $?
