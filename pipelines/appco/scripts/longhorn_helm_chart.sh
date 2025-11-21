#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh
TAG_ARGS=()
SECRET_ARGS=()
LONGHORN_NAMESPACE="longhorn-system"

set_secret_args() {
  local chart_uri="$1"
  SECRET_ARGS=()

  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    if [[ "${chart_uri}" == "longhorn/longhorn" ]]; then
      FINAL_REGISTRY_URL="${REGISTRY_URL}"
    elif [[ -z "${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}" || "${chart_uri}" == *"dp.apps.rancher.io"* ]]; then
      FINAL_REGISTRY_URL="${REGISTRY_URL}/dp.apps.rancher.io"
    else
      FINAL_REGISTRY_URL="${REGISTRY_URL}/${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}"
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

set_longhorn_registry_args() {
  REGISTRY_ARGS=(
      --set image.longhorn.engine.registry=""
      --set image.longhorn.manager.registry=""
      --set image.longhorn.ui.registry=""
      --set image.longhorn.instanceManager.registry=""
      --set image.longhorn.shareManager.registry=""
      --set image.longhorn.backingImageManager.registry=""
      --set image.longhorn.supportBundleKit.registry=""
      --set image.csi.attacher.registry=""
      --set image.csi.provisioner.registry=""
      --set image.csi.nodeDriverRegistrar.registry=""
      --set image.csi.resizer.registry=""
      --set image.csi.snapshotter.registry=""
      --set image.csi.livenessProbe.registry=""
    )
}

set_longhorn_repository_args() {
  # Put the full image path into the repository field instead of splitting registry/repository.
  # This avoids issues where global.privateRegistry.registryUrl overrides image.registry
  # and produces incorrect image URLs, especially in air-gap environments.
  DP_IMAGE_PATH="dp.apps.rancher.io/containers"
  REPOSITORY_ARGS=(
      --set image.longhorn.engine.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-engine"
      --set image.longhorn.manager.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-manager"
      --set image.longhorn.ui.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-ui"
      --set image.longhorn.instanceManager.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-instance-manager"
      --set image.longhorn.shareManager.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-share-manager"
      --set image.longhorn.backingImageManager.repository="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-backing-image-manager"
      --set image.longhorn.supportBundleKit.repository="${DP_IMAGE_PATH}/rancher-support-bundle-kit"
      --set image.csi.attacher.repository="${DP_IMAGE_PATH}/kubernetes-csi-external-attacher"
      --set image.csi.provisioner.repository="${DP_IMAGE_PATH}/kubernetes-csi-external-provisioner"
      --set image.csi.nodeDriverRegistrar.repository="${DP_IMAGE_PATH}/kubernetes-csi-node-driver-registrar"
      --set image.csi.resizer.repository="${DP_IMAGE_PATH}/kubernetes-csi-external-resizer"
      --set image.csi.snapshotter.repository="${DP_IMAGE_PATH}/kubernetes-csi-external-snapshotter"
      --set image.csi.livenessProbe.repository="${DP_IMAGE_PATH}/kubernetes-csi-livenessprobe"
    )
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
      --set image.longhorn.supportBundleKit.tag="${SUPPORT_BUNDLE_TAG}"
      --set image.csi.attacher.tag="${CSI_ATTACHER_TAG}"
      --set image.csi.provisioner.tag="${CSI_PROVISIONER_TAG}"
      --set image.csi.nodeDriverRegistrar.tag="${CSI_REGISTRAR_TAG}"
      --set image.csi.resizer.tag="${CSI_RESIZER_TAG}"
      --set image.csi.snapshotter.tag="${CSI_SNAPSHOTTER_TAG}"
      --set image.csi.livenessProbe.tag="${CSI_LIVENESSPROBE_TAG}"
    )
  fi
}

install_longhorn_custom(){
  # set debugging mode off to avoid leaking appco secrets to the logs.
  # DON'T REMOVE!
  set +x
  helm_login_appco
  set -x
  set_longhorn_registry_args
  set_longhorn_repository_args
  set_longhorn_tag_args
  set_secret_args "${LONGHORN_CHART_URI}"
  
  helm repo add longhorn https://charts.longhorn.io
  helm repo update
  helm upgrade --install longhorn longhorn/longhorn \
    --namespace "${LONGHORN_NAMESPACE}" \
    --version "${LONGHORN_VERSION}" \
    "${REGISTRY_ARGS[@]}" \
    "${REPOSITORY_ARGS[@]}" \
    "${TAG_ARGS[@]}" \
    "${SECRET_ARGS[@]}"
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
