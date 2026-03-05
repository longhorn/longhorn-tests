#!/bin/bash

set -x

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
  helm repo add rancher-prime "${RANCHER_PRIME_CHART_URL}"
  helm repo add rancher-alpha https://releases.rancher.com/server-charts/alpha
  helm repo update
  kubectl create namespace cattle-system
  if [[ "${RANCHER_PRIME}" == true ]]; then
    RANCHER_TYPE="prime"
  elif [[ "${RANCHER_VERSION}" == *"alpha"* ]]; then
    RANCHER_TYPE="alpha"
  else
    RANCHER_TYPE="latest"
  fi
  if [[ -z "${RANCHER_VERSION}" ]]; then
    RANCHER_VERSION=$(helm search repo "rancher-${RANCHER_TYPE}/rancher" -o yaml | yq .[0].version)
  fi
  helm install rancher "rancher-${RANCHER_TYPE}/rancher" --devel --version "${RANCHER_VERSION}" --namespace cattle-system --set bootstrapPassword="${RANCHER_BOOTSTRAP_PASSWORD}" --set hostname="${RANCHER_HOSTNAME}" --set replicas=3 --set ingress.tls.source=letsEncrypt --set letsEncrypt.email=yang.chiu@suse.com
  kubectl -n cattle-system rollout status deploy/rancher
}

get_rancher_api_key() {
  while [[ -z "${TOKEN}" ]]; do
    TOKEN=$(curl -X POST -s -k "https://${RANCHER_HOSTNAME}/v3-public/localproviders/local?action=login" -H 'Content-Type: application/json' -d "{\"username\":\"admin\", \"password\":\"${RANCHER_BOOTSTRAP_PASSWORD}\", \"responseType\": \"json\"}" | jq -r '.token' | tr -d '"')
    ARR=(${TOKEN//:/ })
    RANCHER_ACCESS_KEY=${ARR[0]}
    RANCHER_SECRET_KEY=${ARR[1]}
    sleep 3s
  done
}

install_longhorn() {
  LONGHORN_NAMESPACE="longhorn-system"
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
            -var="registry_secret=docker-registry-secret" \
            -auto-approve -no-color
  wait_longhorn_status_running
}

install_longhorn_stable() {
  install_longhorn "${LONGHORN_STABLE_VERSION}"
}

install_longhorn_custom() {
  install_longhorn
}

upgrade_longhorn() {
  TERRAFORM_UPGRADE_FOLDER="pipelines/utilities/rancher/terraform_upgrade"
  # rm terraform state files if they exist
  # otherwise when it is applied at the 2nd time during upgrading Longhorn from transient version to latest version
  # it will try to uninstall Longhorn first due to the state is overwritten
  rm -rf "${TERRAFORM_UPGRADE_FOLDER}/.terraform.lock.hcl" "${TERRAFORM_UPGRADE_FOLDER}/terraform.tfstate" "${TERRAFORM_UPGRADE_FOLDER}/.terraform"
  LONGHORN_NAMESPACE="longhorn-system"
  CHART_VERSION="${1:-${LONGHORN_INSTALL_VERSION}}"
  terraform -chdir="${TERRAFORM_UPGRADE_FOLDER}" init
  terraform -chdir="${TERRAFORM_UPGRADE_FOLDER}" apply \
            -var="api_url=https://${RANCHER_HOSTNAME}" \
            -var="access_key=${RANCHER_ACCESS_KEY}" \
            -var="secret_key=${RANCHER_SECRET_KEY}" \
            -var="rancher_chart_install_version=${CHART_VERSION}" \
            -var="longhorn_repo=${LONGHORN_REPO}" \
            -var="registry_url=${REGISTRY_URL}" \
            -var="registry_secret=docker-registry-secret" \
            -auto-approve -no-color
  wait_longhorn_status_running
}

upgrade_longhorn_transient() {
  upgrade_longhorn "${LONGHORN_TRANSIENT_VERSION}"
}

upgrade_longhorn_custom() {
  upgrade_longhorn
}

uninstall_longhorn() {
  TERRAFORM_INSTALL_FOLDER="pipelines/utilities/rancher/terraform_install"
  TERRAFORM_UPGRADE_FOLDER="pipelines/utilities/rancher/terraform_upgrade"
  if [[ -e "${TERRAFORM_UPGRADE_FOLDER}/terraform.tfstate" ]]; then
    terraform -chdir="${TERRAFORM_UPGRADE_FOLDER}" destroy \
              -var="api_url=https://${RANCHER_HOSTNAME}" \
              -var="access_key=${RANCHER_ACCESS_KEY}" \
              -var="secret_key=${RANCHER_SECRET_KEY}" \
              -var="rancher_chart_install_version=${CHART_VERSION}" \
              -var="longhorn_repo=${LONGHORN_REPO}" \
              -var="registry_url=${REGISTRY_URL}" \
              -var="registry_secret=docker-registry-secret" \
              -auto-approve -no-color
  else
    terraform -chdir="${TERRAFORM_INSTALL_FOLDER}" destroy \
              -var="api_url=https://${RANCHER_HOSTNAME}" \
              -var="access_key=${RANCHER_ACCESS_KEY}" \
              -var="secret_key=${RANCHER_SECRET_KEY}" \
              -var="rancher_chart_git_repo=${RANCHER_CHART_REPO_URI}" \
              -var="rancher_chart_git_branch=${RANCHER_CHART_REPO_BRANCH}" \
              -var="rancher_chart_install_version=${CHART_VERSION}" \
              -var="longhorn_repo=${LONGHORN_REPO}" \
              -var="registry_url=${REGISTRY_URL}" \
              -var="registry_secret=docker-registry-secret" \
              -auto-approve -no-color
  fi
}

uninstall_longhorn_crd(){
  helm uninstall --namespace=longhorn-system longhorn-crd
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
