create_instance_mapping_configmap(){
  kubectl create configmap instance-mapping --from-file=/tmp/instance_mapping
}
