set_kubeconfig(){
  if [[ "${DISTRO}" == "talos" ]]; then
    export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/kubeconfig"
    until [ $(kubectl get node -o jsonpath='{.items[*].status.conditions}' | jq '.[] | select(.type  == "Ready").status' | grep -ci true) -eq 4 ]; do
      echo "waiting for talos cluster nodes to be running";
      sleep 30;
    done
  elif [[ "${LONGHORN_TEST_CLOUDPROVIDER}" == "harvester" ]]; then
    export KUBECONFIG="test_framework/kube_config.yaml"
  elif [[ "${TF_VAR_k8s_distro_name}" == "rke" ]]; then
    export KUBECONFIG="test_framework/kube_config_rke.yml"
  elif [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
    export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/rke2.yaml"
  elif [[ "${TF_VAR_k8s_distro_name}" == "k3s" ]]; then
    export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
  elif [[ ${TF_VAR_k8s_distro_name} == "aks" ]]; then
    export KUBECONFIG="test_framework/aks.yml"
  elif [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
    export KUBECONFIG="test_framework/eks.yml"
  fi
}