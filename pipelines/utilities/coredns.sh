patch_coredns_ipv6_name_servers(){
  if [[ "${TF_VAR_k8s_distro_name}" == "k3s" ]]; then
    kubectl -n kube-system get configmap coredns -o yaml > coredns.yaml.backup
    sed -i 's|forward \. /etc/resolv.conf|forward . 2606:4700:4700::1111 2606:4700:4700::1001 1.1.1.1 8.8.8.8|' coredns.yaml.backup
    kubectl -n kube-system apply -f coredns.yaml.backup
    kubectl -n kube-system rollout restart deployment coredns
  elif [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
    kubectl -n kube-system get configmap rke2-coredns-rke2-coredns -o yaml > rke2-coredns.yaml.backup
    sed -i 's|/etc/resolv.conf|2606:4700:4700::1111 2606:4700:4700::1001 1.1.1.1 8.8.8.8|' rke2-coredns.yaml.backup
    kubectl -n kube-system apply -f rke2-coredns.yaml.backup
    kubectl -n kube-system rollout restart deployment rke2-coredns-rke2-coredns
  fi
}

scale_up_coredns(){
  if [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
    kubectl get configmap -n kube-system rke2-coredns-rke2-coredns-autoscaler -oyaml | sed 's/\"min\": 0/\"min\": 3/' | kubectl apply -n kube-system -f -
  else
    kubectl patch deployment coredns -n kube-system --type='merge' -p '{"spec": {"replicas": 3}}'
  fi
}
