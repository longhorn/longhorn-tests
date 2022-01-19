#!/usr/bin/env bash

if [[ ! -v TF_VAR_build_engine_aws_access_key ]]; then
	export TF_VAR_build_engine_aws_access_key="AKIAZKQ2ZGMOAKJCJC7Z"
fi

if [[ ! -v TF_VAR_build_engine_aws_secret_key ]]; then
	export TF_VAR_build_engine_aws_secret_key="tMgFT0Xgt56RLtoQ9q6VZY8a3g4V97g/V3qu22gZ"
fi

if [[ ! -v TF_VAR_tf_workspace ]]; then
	export TF_VAR_tf_workspace="$(dirname $(dirname -- $(readlink -fn -- "$0")))"
fi

# terminate any terraform processes
TERRAFORM_PIDS=( `ps aux | grep -i terraform | grep -v grep | awk '{printf("%s ",$1)}'` )
if [[ -n ${TERRAFORM_PIDS[@]} ]] ; then
	for PID in "${TERRAFORM_PIDS[@]}"; do
		kill "${TERRAFORM_PIDS}"
	done
fi

# wait 30 seconds for graceful terraform termination
sleep 30

terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu destroy -auto-approve -no-color
