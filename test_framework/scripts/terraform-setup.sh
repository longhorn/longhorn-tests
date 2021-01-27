#!/usr/bin/env bash

set -x

terraform init  ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
terraform apply -auto-approve -no-color ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}

if [[ ${TF_VAR_arch} == "amd64" ]]; then
	terraform refresh ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	terraform output rke_config > ${TF_VAR_tf_workspace}/rke.yml
	rke up --config ${TF_VAR_tf_workspace}/rke.yml
fi
