create_aws_secret(){
  AWS_ACCESS_KEY_ID_BASE64=`echo -n "${TF_VAR_lh_aws_access_key}" | base64`
  AWS_SECRET_ACCESS_KEY_BASE64=`echo -n "${TF_VAR_lh_aws_secret_key}" | base64`
  AWS_DEFAULT_REGION_BASE64=`echo -n "${TF_VAR_aws_region}" | base64`

  yq e -i '.data.AWS_ACCESS_KEY_ID |= "'${AWS_ACCESS_KEY_ID_BASE64}'"' "pipelines/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_SECRET_ACCESS_KEY |= "'${AWS_SECRET_ACCESS_KEY_BASE64}'"' "pipelines/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_DEFAULT_REGION |= "'${AWS_DEFAULT_REGION_BASE64}'"' "pipelines/templates/aws_cred_secrets.yml"

  kubectl apply -f "pipelines/templates/aws_cred_secrets.yml"
  kubectl apply -f "pipelines/templates/aws_cred_secrets.yml" -n kube-system
}