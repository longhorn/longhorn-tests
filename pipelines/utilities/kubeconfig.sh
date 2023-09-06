set_kubeconfig(){
  # rke2, rke and k3s all support amd64
  # but only k3s supports arm64
  if [[ "${TF_VAR_arch}" == "amd64" ]] ; then
    if [[ "${TF_VAR_k8s_distro_name}" == "rke" ]]; then
        export KUBECONFIG="test_framework/kube_config_rke.yml"
    elif [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
        export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/rke2.yaml"
    else
        export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
    fi
  elif [[ "${TF_VAR_arch}" == "arm64"  ]]; then
    export KUBECONFIG="test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
  fi
}