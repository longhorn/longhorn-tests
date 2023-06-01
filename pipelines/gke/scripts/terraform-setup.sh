#!/usr/bin/env bash

set -x

gcloud auth activate-service-account --project=${TF_VAR_gcp_project} --key-file=${TF_VAR_gcp_auth_file}
gcloud auth list

terraform -chdir=${TF_VAR_tf_workspace}/terraform init
terraform -chdir=${TF_VAR_tf_workspace}/terraform apply -auto-approve -no-color

exit $?
