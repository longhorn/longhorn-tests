#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh

init_flux(){
  flux install
}

create_flux_helm_repo(){
  LONGHORN_NAMESPACE="longhorn-system"
  HELM_CHART_URL="${1:-https://charts.longhorn.io}"
  flux create source helm longhorn --url "${HELM_CHART_URL}" --namespace "${LONGHORN_NAMESPACE}"
}

create_flux_helm_release(){
  HELM_CHART_VERSION="${1:-${LONGHORN_INSTALL_VERSION}}"
  cat << EOF > /tmp/values.yaml
privateRegistry:
  createSecret: false
  registrySecret: docker-registry-secret
EOF
  flux create helmrelease longhorn --chart longhorn --source HelmRepository/longhorn --chart-version "${HELM_CHART_VERSION}" --namespace "${LONGHORN_NAMESPACE}" --values "/tmp/values.yaml"
  wait_longhorn_status_running
}

install_longhorn_stable(){
  create_flux_helm_repo
  create_flux_helm_release "${LONGHORN_STABLE_VERSION}"
}

install_longhorn_transient(){
  create_flux_helm_repo
  create_flux_helm_release "${LONGHORN_TRANSIENT_VERSION}"
}

install_longhorn_custom(){
  create_flux_helm_repo "${HELM_CHART_URL}"
  create_flux_helm_release
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
