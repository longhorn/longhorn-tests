#!/usr/bin/env bash

terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws init
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws apply -auto-approve -no-color
