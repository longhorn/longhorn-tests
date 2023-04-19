#!/bin/bash
set -e

if [[ -z "$TF_VAR_build_engine_aws_access_key" ]]; then
    echo "Must provide TF_VAR_build_engine_aws_access_key in environment" 1>&2
    exit 1
fi

if [[ -z "$TF_VAR_build_engine_aws_secret_key" ]]; then
    echo "Must provide TF_VAR_build_engine_aws_secret_key in environment" 1>&2
    exit 1
fi

if [[ -z "$TF_VAR_docker_id" ]]; then
    echo "Must provide TF_VAR_docker_id in environment" 1>&2
    exit 1
fi

if [[ -z "$TF_VAR_docker_password" ]]; then
    echo "Must provide TF_VAR_docker_password in environment" 1>&2
    exit 1
fi

if [[ -z "$TF_VAR_docker_repo" ]]; then
    echo "Must provide TF_VAR_docker_repo in environment" 1>&2
    exit 1
fi

# if commit_id is empty, we can directly check longhorn-engine:master-head's api version
if [[ -z "${TF_VAR_commit_id}" ]]; then

  docker login -u="${TF_VAR_docker_id}" -p="${TF_VAR_docker_password}"
  docker pull longhornio/longhorn-engine:master-head
  version=`docker run longhornio/longhorn-engine:master-head longhorn version --client-only`
  CLIAPIVersion=`echo $version | jq -r ".clientVersion.cliAPIVersion"`
  CLIAPIMinVersion=`echo $version | jq -r ".clientVersion.cliAPIMinVersion"`
  ControllerAPIVersion=`echo $version | jq -r ".clientVersion.controllerAPIVersion"`
  ControllerAPIMinVersion=`echo $version | jq -r ".clientVersion.controllerAPIMinVersion"`
  DataFormatVersion=`echo $version | jq -r ".clientVersion.dataFormatVersion"`
  DataFormatMinVersion=`echo $version | jq -r ".clientVersion.dataFormatMinVersion"`
  echo "latest engine version: ${version}"

  upgrade_image="${TF_VAR_docker_repo}:upgrade-test.$CLIAPIVersion-$CLIAPIMinVersion"\
".$ControllerAPIVersion-$ControllerAPIMinVersion"\
".$DataFormatVersion-$DataFormatMinVersion"

  if [[ $(docker manifest inspect "${upgrade_image}") != "" ]]; then
    echo "latest engine test images have already published"
    exit 0
  fi
fi

trap ./scripts/cleanup.sh EXIT

# Build amd64 images
export TF_VAR_build_engine_arch="amd64"
export TF_VAR_build_engine_aws_instance_type="t2.micro"
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu init
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu apply -auto-approve -no-color
./scripts/cleanup.sh

# Build arm64 images
export TF_VAR_build_engine_arch="arm64"
export TF_VAR_build_engine_aws_instance_type="a1.medium"
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu init
terraform -chdir=${TF_VAR_tf_workspace}/terraform/aws/ubuntu apply -auto-approve -no-color

echo "Done"