#!/usr/bin/env bash

set -x

terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} init
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color

if [[ "${TF_VAR_create_load_balancer}" == true ]]; then
  terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} output -raw load_balancer_url > ${TF_VAR_tf_workspace}/load_balancer_url
fi

exit $?
