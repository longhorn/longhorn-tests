create_harvester_secret(){
  LAB_URL_BASE64=`echo -n "${TF_VAR_lab_url}" | base64`
  LAB_ACCESS_KEY_BASE64=`echo -n "${TF_VAR_lab_access_key}" | base64`
  LAB_SECRET_KEY_BASE64=`echo -n "${TF_VAR_lab_secret_key}" | base64`
  LAB_CLUSTER_ID_BASE64=`echo -n "$(cat /tmp/cluster_id)" | base64`

  yq e -i '.data.LAB_URL |= "'${LAB_URL_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"
  yq e -i '.data.LAB_ACCESS_KEY |= "'${LAB_ACCESS_KEY_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"
  yq e -i '.data.LAB_SECRET_KEY |= "'${LAB_SECRET_KEY_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"
  yq e -i '.data.LAB_CLUSTER_ID |= "'${LAB_CLUSTER_ID_BASE64}'"' "pipelines/templates/host_provider_cred_secrets.yml"

  kubectl apply -f "pipelines/templates/host_provider_cred_secrets.yml"
}