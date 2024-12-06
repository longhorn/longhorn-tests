scale_up_coredns(){
  if [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
    kubectl get configmap -n kube-system rke2-coredns-rke2-coredns-autoscaler -oyaml | sed 's/\"min\": 0/\"min\": 3/' | kubectl apply -n kube-system -f -
  else
    kubectl patch deployment coredns -n kube-system --type='merge' -p '{"spec": {"replicas": 3}}'
  fi
}
