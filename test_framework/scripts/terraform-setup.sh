#!/usr/bin/env bash

set -x

if [[ ${TF_VAR_arch} == "amd64" ]]; then
	terraform init  ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	terraform apply -auto-approve -no-color ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	terraform refresh ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	terraform output rke_config > ${TF_VAR_tf_workspace}/rke.yml
	rke up --config ${TF_VAR_tf_workspace}/rke.yml
	exit $?
else
	terraform init  ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	terraform apply -auto-approve -no-color ${TF_VAR_tf_workspace}/terraform/aws/${DISTRO}
	exit $?
fi
