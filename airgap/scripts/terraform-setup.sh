#!/usr/bin/env bash

set -x

terraform -chdir=./airgap/terraform init
terraform -chdir=./airgap/terraform apply -auto-approve -no-color

exit $?
