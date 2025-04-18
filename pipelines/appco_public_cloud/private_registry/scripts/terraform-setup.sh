#!/usr/bin/env bash

set -x

terraform -chdir=./pipelines/appco_public_cloud/private_registry/terraform init
terraform -chdir=./pipelines/appco_public_cloud/private_registry/terraform/ apply -auto-approve -no-color

exit $?
