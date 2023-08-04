set_kubeconfig(){
  # rke2, rke and k3s all support amd64
  # but only k3s supports arm64
  if [[ "${TF_VAR_arch}" == "amd64" ]] ; then
    if [[ "${TF_VAR_k8s_distro_name}" == "rke" ]]; then
        export KUBECONFIG="${PWD}/test_framework/kube_config_rke.yml"
    elif [[ "${TF_VAR_k8s_distro_name}" == "rke2" ]]; then
        export KUBECONFIG="${PWD}/test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/rke2.yaml"
    else
        export KUBECONFIG="${PWD}/test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
    fi
  elif [[ "${TF_VAR_arch}" == "arm64"  ]]; then
    export KUBECONFIG="${PWD}/test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
  fi
}


# construct kubeconfig content from an in-cluster config environment (a pod)
construct_kubeconfig(){
  kubectl config set-cluster in-cluster --server="https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}" --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  kubectl config set-credentials pod-token --token="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
  kubectl config set-context default --cluster=in-cluster --user=pod-token
  kubectl config use-context default
}