#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh
source pipelines/utilities/longhorn_namespace.sh

get_longhorn_chart(){
  CHART_VERSION="${1:-$LONGHORN_REPO_BRANCH}"

  # create and clean tmpdir
  TMPDIR="/tmp/longhorn"
  mkdir -p ${TMPDIR}
  rm -rf "${TMPDIR}/"

  LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

  git clone --single-branch \
            --branch "${CHART_VERSION}" \
            "${LONGHORN_REPO_URI}" \
            "${LONGHORN_REPO_DIR}"
}

customize_longhorn_chart_registry(){
  # specify custom registry secret in chart/values.yaml
  yq -i '.privateRegistry.createSecret=false' "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i '.privateRegistry.registrySecret="docker-registry-secret"' "${LONGHORN_REPO_DIR}/chart/values.yaml"
  if [[ ! -z "${REGISTRY_URL}" ]]; then
    yq -i ".privateRegistry.registryUrl=\"${REGISTRY_URL}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
}

customize_longhorn_chart(){
  # customize longhorn components repository and tag (version) in chart/values.yaml
  OLD_IFS=$IFS
  IFS=':'
  if [[ -n "${CUSTOM_LONGHORN_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_MANAGER_IMAGE}"
    yq -i ".image.longhorn.manager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.manager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_ENGINE_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    yq -i ".image.longhorn.engine.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.engine.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_UI_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_UI_IMAGE}"
    yq -i ".image.longhorn.ui.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.ui.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.instanceManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.instanceManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.shareManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.shareManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.backingImageManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.backingImageManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  IFS=$OLD_IFS
}

install_longhorn(){
  get_longhorn_namespace
  helm upgrade --install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace "${LONGHORN_NAMESPACE}"
  wait_longhorn_status_running
}

install_longhorn_stable(){
  get_longhorn_chart "${LONGHORN_STABLE_VERSION}"
  customize_longhorn_chart_registry
  install_longhorn
}

install_longhorn_transient(){
  get_longhorn_chart "${LONGHORN_TRANSIENT_VERSION}"
  customize_longhorn_chart_registry
  install_longhorn
}

install_longhorn_custom(){
  get_longhorn_chart
  customize_longhorn_chart_registry
  customize_longhorn_chart
  install_longhorn
}

uninstall_longhorn(){
  get_longhorn_namespace
  helm uninstall longhorn --namespace "${LONGHORN_NAMESPACE}"
  kubectl delete ns "${LONGHORN_NAMESPACE}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
