install_litmus(){
  kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v1.13.8.yaml
}

install_experiments(){
  kubectl apply -f https://raw.githubusercontent.com/litmuschaos/chaos-charts/v1.13.x/charts/kube-aws/ec2-terminate-by-id/experiment.yaml
  kubectl apply -f https://raw.githubusercontent.com/litmuschaos/chaos-charts/v1.13.x/charts/kube-aws/ec2-terminate-by-id/rbac.yaml
}

create_instance_mapping_configmap(){
  kubectl create configmap instance-mapping --from-file=/tmp/instance_mapping
}

create_cloud_secret(){
  sed -i "s%aws_access_key_id =%aws_access_key_id = ${TF_VAR_lh_aws_access_key}%g" "pipelines/templates/cloud_secret.yml"
  sed -i "s%aws_secret_access_key =%aws_secret_access_key = ${TF_VAR_lh_aws_secret_key}%g" "pipelines/templates/cloud_secret.yml"

  kubectl apply -f "pipelines/templates/cloud_secret.yml"
}