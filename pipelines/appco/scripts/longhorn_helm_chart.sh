#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh
TAG_ARGS=()
SECRET_ARGS=()

set_secret_args() {
  local chart_uri="$1"
  SECRET_ARGS=()

  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    if [[ "${chart_uri}" == "longhorn/longhorn" ]]; then
      FINAL_REGISTRY_URL="${REGISTRY_URL}"
    elif [[ -z "${APPCO_LONGHORN_COMPONENT_REGISTRY}" || "${chart_uri}" == *"dp.apps.rancher.io"* ]]; then
      FINAL_REGISTRY_URL="${REGISTRY_URL}/dp.apps.rancher.io"
    else
      FINAL_REGISTRY_URL="${REGISTRY_URL}/${APPCO_LONGHORN_COMPONENT_REGISTRY}"
    fi

    SECRET_ARGS+=(
      --set privateRegistry.createSecret=false
      --set privateRegistry.registrySecret="docker-registry-secret"
      --set privateRegistry.registryUrl="${FINAL_REGISTRY_URL}"
    )
  else
    SECRET_ARGS+=(--set global.imagePullSecrets="{application-collection}")
  fi
}

helm_login_appco(){
  helm registry login dp.apps.rancher.io \
    --username "${APPCO_USERNAME}" \
    --password "${APPCO_PASSWORD}"
}

set_longhorn_tag_args() {
  if [[ -n "${LONGHORN_COMPONENT_TAG}" ]]; then
    TAG_ARGS=(
      --set image.longhorn.engine.tag="${LONGHORN_COMPONENT_TAG}"
      --set image.longhorn.manager.tag="${LONGHORN_COMPONENT_TAG}"
      --set image.longhorn.ui.tag="${LONGHORN_COMPONENT_TAG}"
      --set image.longhorn.instanceManager.tag="${LONGHORN_COMPONENT_TAG}"
      --set image.longhorn.shareManager.tag="${LONGHORN_COMPONENT_TAG}"
      --set image.longhorn.backingImageManager.tag="${LONGHORN_COMPONENT_TAG}"
    )
  fi
}

install_longhorn_custom(){
  set_secret_args "${LONGHORN_CHART_URI}"
  if [[ "${LONGHORN_CHART_URI}" == "longhorn/longhorn" ]]; then
    helm repo add longhorn https://charts.longhorn.io
    helm repo update
    helm upgrade --install longhorn longhorn/longhorn \
      --namespace "${LONGHORN_NAMESPACE}" \
      --version "${LONGHORN_VERSION}" \
      "${SECRET_ARGS[@]}"
  else
    # set debugging mode off to avoid leaking appco secrets to the logs.
    # DON'T REMOVE!    
    set +x
    helm_login_appco
    set -x
    set_longhorn_tag_args

    if [[ -z "${APPCO_LONGHORN_COMPONENT_REGISTRY}" ]]; then
      helm upgrade --install longhorn "${LONGHORN_CHART_URI}" \
        --version "${LONGHORN_VERSION}" \
        --namespace "${LONGHORN_NAMESPACE}" \
        "${SECRET_ARGS[@]}"
    else
      helm upgrade --install longhorn "${LONGHORN_CHART_URI}" \
        --version "${LONGHORN_VERSION}" \
        --namespace "${LONGHORN_NAMESPACE}" \
        --set image.longhorn.engine.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set image.longhorn.manager.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set image.longhorn.ui.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set image.longhorn.instanceManager.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set image.longhorn.shareManager.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set image.longhorn.backingImageManager.registry="${APPCO_LONGHORN_COMPONENT_REGISTRY}" \
        --set privateRegistry.registryUrl="" \
        "${TAG_ARGS[@]}" \
        "${SECRET_ARGS[@]}"
    fi
  fi
  wait_longhorn_status_running
}

install_longhorn_version() {
  local chart_uri="$1"
  local version="$2"

  set_secret_args "$chart_uri"
  helm repo add longhorn https://charts.longhorn.io
  helm repo update
  set +x
  helm_login_appco
  set -x
  helm upgrade --install longhorn "$chart_uri" \
    --version "$version" \
    --namespace "${LONGHORN_NAMESPACE}" \
    "${SECRET_ARGS[@]}"

  wait_longhorn_status_running
}

install_longhorn_stable(){
  install_longhorn_version "${LONGHORN_STABLE_VERSION_CHART_URI}" "${LONGHORN_STABLE_VERSION}"
}

install_longhorn_transient(){
  install_longhorn_version "${LONGHORN_TRANSIENT_VERSION_CHART_URI}" "${LONGHORN_TRANSIENT_VERSION}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
