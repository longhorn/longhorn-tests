#!/usr/bin/env bash

# terminate any terraform processes
TERRAFORM_PIDS="`ps aux | grep -i terraform | grep -v grep | awk {'print $1'} | tr \"\n\" \" \" `" 
if [[ -n TERRAFORM_PIDS ]] ; then
  kill  "${TERRAFORM_PIDS}"
fi

# wait 30 seconds for graceful terraform termination
sleep 30

terraform destroy -auto-approve -no-color ${TF_VAR_tf_workspace}/terraform/aws
