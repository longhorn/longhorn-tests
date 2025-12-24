create_controlplane_public_ip_configmap(){
  ip="$(tr -d '\n' < /tmp/controlplane_public_ip)"

  kubectl create configmap controlplane-public-ip --from-literal=controlplane_public_ip="${ip}"
}
