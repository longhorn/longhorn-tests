#!/bin/bash

source pipelines/utilities/longhorn_namespace.sh

create_aws_secret(){
  get_longhorn_namespace

  AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${TF_VAR_lh_aws_access_key}}"
  AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${TF_VAR_lh_aws_secret_key}}"
  AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-${TF_VAR_aws_region}}

  AWS_ACCESS_KEY_ID_BASE64=`echo -n "${AWS_ACCESS_KEY_ID}" | base64`
  AWS_SECRET_ACCESS_KEY_BASE64=`echo -n "${AWS_SECRET_ACCESS_KEY}" | base64`
  AWS_DEFAULT_REGION_BASE64=`echo -n "${AWS_DEFAULT_REGION}" | base64`

  yq e -i '.data.AWS_ACCESS_KEY_ID |= "'${AWS_ACCESS_KEY_ID_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"
  yq e -i '.data.AWS_SECRET_ACCESS_KEY |= "'${AWS_SECRET_ACCESS_KEY_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"
  yq e -i '.data.AWS_DEFAULT_REGION |= "'${AWS_DEFAULT_REGION_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"

  kubectl apply -f "pipelines/templates/host_provider_cred_secrets.yml"
  kubectl apply -f "pipelines/templates/host_provider_cred_secrets.yml" -n "${LONGHORN_NAMESPACE}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
