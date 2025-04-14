#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh

get_longhorn_repo(){
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

  LONGHORN_MANIFEST_PATH="${LONGHORN_REPO_DIR}/deploy/longhorn.yaml"
}

generate_longhorn_yaml_manifest() {
  # get longhorn default images from yaml manifest
  LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${LONGHORN_MANIFEST_PATH}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${LONGHORN_MANIFEST_PATH}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${LONGHORN_MANIFEST_PATH}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${LONGHORN_MANIFEST_PATH}"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${LONGHORN_MANIFEST_PATH}"| head -1 | sed -e 's/^"//' -e 's/"$//'`

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST_PATH}"
  else
    # use longhorn-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_MANAGER_IMAGE=${LONGHORN_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_ENGINE_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${LONGHORN_MANIFEST_PATH}"
  else
    # use longhorn-engine image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_ENGINE_IMAGE=${LONGHORN_ENGINE_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST_PATH}"
  else
    # use instance-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST_PATH}"
  else
    # use share-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${LONGHORN_MANIFEST_PATH}"
  else
    # use backing-image-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi
}

customize_longhorn_manifest_registry(){
  # (1) add secret name to imagePullSecrets.name
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-driver-deployer").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_MANIFEST_PATH}"
  yq -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_MANIFEST_PATH}"
  yq -i 'select(.kind == "DaemonSet" and .metadata.name == "pre-pull-share-manager-image").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_MANIFEST_PATH}"
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-ui").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_MANIFEST_PATH}"
  yq -i 'select(.kind == "ConfigMap" and .metadata.name == "longhorn-default-setting").data."default-setting.yaml"="registry-secret: docker-registry-secret"' "${LONGHORN_MANIFEST_PATH}"
  # (2) modify images to point to custom registry
  if [[ ! -z "${REGISTRY_URL}" ]]; then
    sed -i "s/longhornio\//${REGISTRY_URL}\/longhornio\//g" "${LONGHORN_MANIFEST_PATH}"
  fi
}

install_longhorn(){
  LONGHORN_NAMESPACE="longhorn-system"
  kubectl apply -f "${LONGHORN_MANIFEST_PATH}"
  wait_longhorn_status_running
}

install_longhorn_stable(){
  get_longhorn_repo "${LONGHORN_STABLE_VERSION}"
  customize_longhorn_manifest_registry
  install_longhorn
}

install_longhorn_transient(){
  get_longhorn_repo "${LONGHORN_TRANSIENT_VERSION}"
  customize_longhorn_manifest_registry
  install_longhorn
}

install_longhorn_custom(){
  get_longhorn_repo
  generate_longhorn_yaml_manifest
  customize_longhorn_manifest_registry
  install_longhorn
}

uninstall_longhorn(){
  LONGHORN_NAMESPACE="longhorn-system"
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"
  kubectl create -f "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/uninstall/uninstall.yaml"
  kubectl wait --for=condition=complete job/longhorn-uninstall -n "${LONGHORN_NAMESPACE}" --timeout=15m
}

delete_longhorn_crds(){
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"
  kubectl delete -f "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/deploy/longhorn.yaml"
}

delete_uninstall_job(){
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"
  kubectl delete -f "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/uninstall/uninstall.yaml"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
