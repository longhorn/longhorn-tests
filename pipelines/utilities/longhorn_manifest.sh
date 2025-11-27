#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh
source pipelines/utilities/longhorn_namespace.sh

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

  local custom_cmd="$1"
  if [[ -n "$custom_cmd" ]]; then
    custom_cmd="${custom_cmd//longhorn.yaml/$LONGHORN_MANIFEST_PATH}"
    eval "$custom_cmd"
  fi

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

customize_longhorn_default_data_path(){
  DEFAULT_DATA_PATH="${1:-/var/lib/longhorn/}"
  sed -i "/default-setting\.yaml: |-/a\    default-data-path: ${DEFAULT_DATA_PATH}" "${LONGHORN_MANIFEST_PATH}"
}

install_longhorn(){
  get_longhorn_namespace
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" "${LONGHORN_MANIFEST_PATH}"
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
  generate_longhorn_yaml_manifest "$@"
  customize_longhorn_manifest_registry
  install_longhorn
}

uninstall_longhorn(){
  get_longhorn_namespace
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"

  wget "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/uninstall/uninstall.yaml" -O uninstall.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" uninstall.yaml
  kubectl create -f uninstall.yaml

  kubectl wait --for=condition=complete job/longhorn-uninstall -n "${LONGHORN_NAMESPACE}" --timeout=10m
  exit_code=$?
  kubectl get job/longhorn-uninstall -n "${LONGHORN_NAMESPACE}"
  kubectl logs job/longhorn-uninstall -n "${LONGHORN_NAMESPACE}" -f
  exit $exit_code
}

check_uninstall_log(){
  get_longhorn_namespace

  LATEST_POD=$(kubectl get pods -n "${LONGHORN_NAMESPACE}" -l job-name=longhorn-uninstall --sort-by=.metadata.creationTimestamp -o jsonpath="{.items[-1].metadata.name}")

  if ! kubectl logs "${LATEST_POD}" -n "${LONGHORN_NAMESPACE}" | grep "level=error\|level=fatal"; then
    return 0
  else
    return 1
  fi
}

delete_longhorn_crds(){
  get_longhorn_namespace
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"

  wget "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/deploy/longhorn.yaml" -O longhorn.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" longhorn.yaml
  kubectl delete -f longhorn.yaml
}

delete_uninstall_job(){
  get_longhorn_namespace
  UNINSTALL_VERSION="${1:-$LONGHORN_REPO_BRANCH}"

  wget "https://raw.githubusercontent.com/longhorn/longhorn/${UNINSTALL_VERSION}/uninstall/uninstall.yaml" -O uninstall.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" uninstall.yaml
  kubectl delete -f uninstall.yaml
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
