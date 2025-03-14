#!/usr/bin/env bash

set -x

gcloud auth activate-service-account --project=${TF_VAR_gcp_project} --key-file=${TF_VAR_gcp_auth_file}
gcloud auth list

terraform -chdir=pipelines/gke/terraform init
terraform -chdir=pipelines/gke/terraform apply -auto-approve -no-color

exit $?
