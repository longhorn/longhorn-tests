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
}


create_argocd_app(){
  REVISION="${1:-${LONGHORN_INSTALL_VERSION}}"
  argocd app create longhorn --repo "${LONGHORN_REPO_URI}" --revision "${REVISION}" --path chart --dest-server https://kubernetes.default.svc --dest-namespace "${LONGHORN_NAMESPACE}"
}


update_argocd_app_target_revision(){
  argocd app set longhorn --revision "${1}"
}


sync_argocd_app(){
  argocd app sync longhorn
  wait_longhorn_status_running
  kubectl config set-context --current --namespace=default
}
