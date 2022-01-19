#!/usr/bin/env bash

set -x

terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu init
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu apply -auto-approve -no-color
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu apply -auto-approve -no-color -refresh-only
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu output -raw config > ${TF_VAR_tf_workspace}/config.yml
sleep 30

exit $?

