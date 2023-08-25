source pipelines/utilities/longhorn_status.sh


install_rancher() {

  RANCHER_HOSTNAME=`cat "test_framework/load_balancer_url"`
  RANCHER_BOOTSTRAP_PASSWORD='p@ssw0rd'

  kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v1.12.2/cert-manager.crds.yaml
  kubectl create namespace cert-manager
  helm repo add jetstack https://charts.jetstack.io
  helm repo update
  helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.12.2
  kubectl rollout status deployment cert-manager -n cert-manager
  kubectl get pods --namespace cert-manager

  helm repo add rancher-latest https://releases.rancher.com/server-charts/latest
  helm repo update
  kubectl create namespace cattle-system
  if [[ -z "${RANCHER_VERSION}" ]]; then
    RANCHER_VERSION=$(helm search repo rancher-latest/rancher -o yaml | yq .[0].version)
  fi
  helm install rancher rancher-latest/rancher --version "${RANCHER_VERSION}" --namespace cattle-system --set bootstrapPassword="${RANCHER_BOOTSTRAP_PASSWORD}" --set hostname="${RANCHER_HOSTNAME}" --set replicas=3 --set ingress.tls.source=letsEncrypt --set letsEncrypt.email=yang.chiu@suse.com
  kubectl -n cattle-system rollout status deploy/rancher
}


get_rancher_api_key() {
  TOKEN=$(curl -X POST -s -k "https://${RANCHER_HOSTNAME}/v3-public/localproviders/local?action=login" -H 'Content-Type: application/json' -d "{\"username\":\"admin\", \"password\":\"${RANCHER_BOOTSTRAP_PASSWORD}\", \"responseType\": \"json\"}" | jq -r '.token' | tr -d '"')
  ARR=(${TOKEN//:/ })
  RANCHER_ACCESS_KEY=${ARR[0]}
  RANCHER_SECRET_KEY=${ARR[1]}
}


install_longhorn_rancher_chart() {
  CHART_VERSION="${1:-${LONGHORN_INSTALL_VERSION}}"
  terraform -chdir="pipelines/utilities/rancher/terraform_install" init
  terraform -chdir="pipelines/utilities/rancher/terraform_install" apply \
            -var="api_url=https://${RANCHER_HOSTNAME}" \
            -var="access_key=${RANCHER_ACCESS_KEY}" \
            -var="secret_key=${RANCHER_SECRET_KEY}" \
            -var="rancher_chart_git_repo=${RANCHER_CHART_REPO_URI}" \
            -var="rancher_chart_git_branch=${RANCHER_CHART_REPO_BRANCH}" \
            -var="rancher_chart_install_version=${CHART_VERSION}" \
            -var="longhorn_repo=${LONGHORN_REPO}" \
            -var="registry_url=${REGISTRY_URL}" \
            -var="registry_user=${REGISTRY_USERNAME}" \
            -var="registry_passwd=${REGISTRY_PASSWORD}" \
            -var="registry_secret=docker-registry-secret" \
            -auto-approve -no-color
  wait_longhorn_status_running
}


upgrade_longhorn_rancher_chart() {
  terraform -chdir="pipelines/utilities/rancher/terraform_upgrade" init
  terraform -chdir="pipelines/utilities/rancher/terraform_upgrade" apply \
            -var="api_url=https://${RANCHER_HOSTNAME}" \
            -var="access_key=${RANCHER_ACCESS_KEY}" \
            -var="secret_key=${RANCHER_SECRET_KEY}" \
            -var="rancher_chart_install_version=${LONGHORN_INSTALL_VERSION}" \
            -var="longhorn_repo=${LONGHORN_REPO}" \
            -auto-approve -no-color
  wait_longhorn_status_running
}
