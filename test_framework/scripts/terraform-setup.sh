#!/bin/ash 

terraform init  ${TF_VAR_tf_workspace}/terraform/digitalocean
terraform apply -auto-approve -no-color ${TF_VAR_tf_workspace}/terraform/digitalocean
terraform output > ${TF_VAR_tf_workspace}/terraform.output
