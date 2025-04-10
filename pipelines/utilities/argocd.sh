#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh

install_argocd(){
  kubectl create namespace argocd
  kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/core-install.yaml
  wait_argocd_status_running
}

wait_argocd_status_running(){
  local RETRY_COUNTS=10
  local RETRY_INTERVAL="10s"

  RETRIES=0
  while [[ -n `kubectl get pods -n argocd --no-headers 2>&1 | awk '{print $3}' | grep -v "Running"` ]] || \
    [[ -n `kubectl get pods -n argocd --no-headers 2>&1 | awk '{print $2}' | grep -v "1/1"` ]]; do
    echo "argocd is still installing ... re-checking in 10s"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: argocd installation timeout"; exit 1 ; fi
  done
  kubectl get pods -n argocd -o wide
}

init_argocd(){
  argocd login --core
  kubectl config set-context --current --namespace=argocd
  argocd version --short
  kubectl config get-contexts
  kubectl config view
}

create_argocd_app(){
  LONGHORN_NAMESPACE="longhorn-system"
  REVISION="${1:-${LONGHORN_INSTALL_VERSION}}"
  cat > longhorn-application.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: longhorn
  namespace: argocd
spec:
  project: default
  sources:
    - chart: longhorn
      repoURL: ${HELM_CHART_URL}
      targetRevision: ${REVISION}
      helm:
        values: |
          preUpgradeChecker:
            jobEnabled: false
          privateRegistry:
            createSecret: false
            registryUrl: ${REGISTRY_URL}
            registrySecret: docker-registry-secret
  destination:
    server: https://kubernetes.default.svc
    namespace: ${LONGHORN_NAMESPACE}
EOF
  kubectl apply -f longhorn-application.yaml
}

update_argocd_app_target_revision(){
  LONGHORN_NAMESPACE="longhorn-system"
  argocd app set longhorn --revision "${1}" --source-position 1
}

sync_argocd_app(){
  argocd app sync longhorn
  wait_longhorn_status_running
  kubectl config set-context --current --namespace=default
  kubectl config get-contexts
  kubectl config view
}

# check if we're in an in-cluster environment now
is_in_cluster(){
  if [[ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]]; then
    return 0
  else
    return 1
  fi
}

# construct kubeconfig content from an in-cluster config environment (a pod)
construct_kubeconfig(){
  kubectl config set-cluster in-cluster --server="https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}" --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  kubectl config set-credentials pod-token --token="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
  kubectl config set-context default --cluster=in-cluster --user=pod-token
  kubectl config use-context default
  kubectl config get-contexts
  kubectl config view
}

upgrade_longhorn(){
  HELM_CHART_VERSION="${1:-${LONGHORN_INSTALL_VERSION}}"
  construct_kubeconfig
  init_argocd
  update_argocd_app_target_revision "${HELM_CHART_VERSION}"
  sync_argocd_app
}

upgrade_longhorn_transient(){
  upgrade_longhorn "${LONGHORN_TRANSIENT_VERSION}"
}

upgrade_longhorn_custom(){
  upgrade_longhorn
}

install_longhorn(){
  HELM_CHART_VERSION="${1:-${LONGHORN_INSTALL_VERSION}}"
  if is_in_cluster; then
    construct_kubeconfig
  fi
  init_argocd
  create_argocd_app "${HELM_CHART_VERSION}"
  sync_argocd_app
}

install_longhorn_stable(){
  install_longhorn "${LONGHORN_STABLE_VERSION}"
}

install_longhorn_custom(){
  install_longhorn
}

uninstall_longhorn_app(){
  if is_in_cluster; then
    construct_kubeconfig
  fi
  init_argocd
  argocd app delete longhorn --cascade -y
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
