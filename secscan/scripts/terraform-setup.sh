#!/bin/ash 

cd "${TF_VAR_tf_workspace}/terraform/digitalocean"

terraform init 
terraform apply -auto-approve -no-color -var-file=do.tfvars 
