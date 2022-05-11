#!/usr/bin/env bash

# terminate any terraform processes
TERRAFORM_PIDS=( `ps aux | grep -i terraform | grep -v grep | awk '{printf("%s ",$1)}'` )
if [[ -n ${TERRAFORM_PIDS[@]} ]] ; then
	for PID in "${TERRAFORM_PIDS[@]}"; do
		kill "${TERRAFORM_PIDS}"
	done
fi

# wait 30 seconds for graceful terraform termination
sleep 30

terraform -chdir=./airgap/terraform destroy -auto-approve -no-color
