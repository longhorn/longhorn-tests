#!/usr/bin/env bash

set -x

terraform -chdir=pipelines/storage_network/terraform init
terraform -chdir=pipelines/storage_network/terraform apply -auto-approve -no-color

NETWORK_INTERFACE_IDS=$(terraform -chdir=pipelines/storage_network/terraform output -json network_interface_ids | tr -d '"')
for id in ${NETWORK_INTERFACE_IDS}; do
  aws ec2 modify-network-interface-attribute --network-interface-id "${id}" --no-source-dest-check
done

terraform -chdir=pipelines/storage_network/terraform output -raw controlplane_public_ip > /tmp/controlplane_public_ip
terraform -chdir=pipelines/storage_network/terraform output -raw instance_mapping | jq 'map({(.name | split(".")[0]): .id}) | add' | jq -s add > /tmp/instance_mapping

exit $?
