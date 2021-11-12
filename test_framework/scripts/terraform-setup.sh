#!/usr/bin/env bash

set -x

if [[ ${TF_VAR_arch} == "amd64" ]]; then
	terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} init
	terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color
    terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color -refresh-only
	terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} output rke_config > ${TF_VAR_tf_workspace}/rke.yml
	sleep 30
	rke up --config ${TF_VAR_tf_workspace}/rke.yml
else
	terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} init
	terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/${DISTRO} apply -auto-approve -no-color
fi

exit $?
