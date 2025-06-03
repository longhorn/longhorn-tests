#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh

install_longhorn_custom(){
  IMAGES=(
    "${CUSTOM_LONGHORN_MANAGER_IMAGE}"
    "${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    "${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
    "${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
    "${CUSTOM_LONGHORN_UI_IMAGE}"
    "${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}"
    "${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}"
  )
  echo "${IMAGES[@]}"
  LONGHORN_NAMESPACE="longhorn-system"
  LONGHORN_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/longhorn.yaml"
  get_longhorn_manifest "${LONGHORN_MANIFEST_URL}"
  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}" "${LONGHORN_REPO_BRANCH}" "${IMAGES[@]}"
  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    customize_longhorn_manifest_for_private_registry
  fi
  install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
}

install_longhorn_stable(){
  STABLE_VERSION_IMAGES=(
    "${STABLE_MANAGER_IMAGE}"
    "${STABLE_ENGINE_IMAGE}"
    "${STABLE_INSTANCE_MANAGER_IMAGE}"
    "${STABLE_SHARE_MANAGER_IMAGE}"
    "${STABLE_BACKING_IMAGE_MANAGER_IMAGE}"
    "${STABLE_UI_IMAGE}"
    "${STABLE_SUPPORT_BUNDLE_IMAGE}"
    "${STABLE_CSI_ATTACHER_IMAGE}"
    "${STABLE_CSI_PROVISIONER_IMAGE}"
    "${STABLE_CSI_NODE_REGISTRAR_IMAGE}"
    "${STABLE_CSI_RESIZER_IMAGE}"
    "${STABLE_CSI_SNAPSHOTTER_IMAGE}"
    "${STABLE_CSI_LIVENESSPROBE_IMAGE}"
  )
  echo "${STABLE_VERSION_IMAGES[@]}"
  LONGHORN_NAMESPACE="longhorn-system"
  LONGHORN_STABLE_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_STABLE_VERSION}/deploy/longhorn.yaml"

  get_longhorn_manifest "${LONGHORN_STABLE_MANIFEST_URL}"
  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}" "${LONGHORN_STABLE_VERSION}" "${STABLE_VERSION_IMAGES[@]}"
  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    customize_longhorn_manifest_for_private_registry
  fi
  install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
}

install_longhorn_transient(){
  TRANSIENT_VERSION_IMAGES=(
    "${TRANSIENT_MANAGER_IMAGE}"
    "${TRANSIENT_ENGINE_IMAGE}"
    "${TRANSIENT_INSTANCE_MANAGER_IMAGE}"
    "${TRANSIENT_SHARE_MANAGER_IMAGE}"
    "${TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE}"
    "${TRANSIENT_UI_IMAGE}"
    "${TRANSIENT_SUPPORT_BUNDLE_IMAGE}"
    "${TRANSIENT_CSI_ATTACHER_IMAGE}"
    "${TRANSIENT_CSI_PROVISIONER_IMAGE}"
    "${TRANSIENT_CSI_NODE_REGISTRAR_IMAGE}"
    "${TRANSIENT_CSI_RESIZER_IMAGE}"
    "${TRANSIENT_CSI_SNAPSHOTTER_IMAGE}"
    "${TRANSIENT_CSI_LIVENESSPROBE_IMAGE}"
  )
  echo "${TRANSIENT_VERSION_IMAGES[@]}"
  LONGHORN_NAMESPACE="longhorn-system"
  LONGHORN_TRANSIENT_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_TRANSIENT_VERSION}/deploy/longhorn.yaml"

  get_longhorn_manifest "${LONGHORN_TRANSIENT_MANIFEST_URL}"
  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}" "${LONGHORN_TRANSIENT_VERSION}" "${TRANSIENT_VERSION_IMAGES[@]}"
  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    customize_longhorn_manifest_for_private_registry
  fi
  install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
}


install_longhorn_by_manifest(){
  LONGHORN_MANIFEST_FILE_PATH="${1}"
  kubectl apply -f "${LONGHORN_MANIFEST_FILE_PATH}"
  wait_longhorn_status_running
}

customize_longhorn_manifest_for_private_registry(){
  # (1) add secret name to imagePullSecrets.name
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-driver-deployer").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-ui").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "ConfigMap" and .metadata.name == "longhorn-default-setting").data."default-setting.yaml"="registry-secret: docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
}

get_longhorn_manifest(){
  manifest_url="$1"
  wget ${manifest_url} -P ${TF_VAR_tf_workspace}
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${TF_VAR_tf_workspace}/longhorn.yaml"
}

generate_longhorn_yaml_manifest() {
  MANIFEST_BASEDIR="${1}"
  BRANCH="${2}"
  shift 2
  CUSTOM_IMAGES=("$@")

  # create and clean tmpdir
  TMPDIR="/tmp/longhorn"
  mkdir -p ${TMPDIR}
  rm -rf "${TMPDIR}/"

  LONGHORN_REPO_URI=${LONGHORN_REPO_URI:-"https://github.com/longhorn/longhorn.git"}
  LONGHORN_REPO_DIR="${TMPDIR}/longhorn"
  local LONGHORN_REPO_BRANCH=${BRANCH:-"master"}

  local CUSTOM_LONGHORN_MANAGER_IMAGE="${CUSTOM_IMAGES[0]}"
  local CUSTOM_LONGHORN_ENGINE_IMAGE="${CUSTOM_IMAGES[1]}"
  local CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${CUSTOM_IMAGES[2]}"
  local CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${CUSTOM_IMAGES[3]}"
  local CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${CUSTOM_IMAGES[4]}"
  local CUSTOM_LONGHORN_UI_IMAGE="${CUSTOM_IMAGES[5]}"
  local CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE="${CUSTOM_IMAGES[6]}"
  local CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE="${CUSTOM_IMAGES[7]}"
  local CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE="${CUSTOM_IMAGES[8]}"
  local CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE="${CUSTOM_IMAGES[9]}"
  local CUSTOM_LONGHORN_CSI_RESIZER_IMAGE="${CUSTOM_IMAGES[10]}"
  local CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE="${CUSTOM_IMAGES[11]}"
  local CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE="${CUSTOM_IMAGES[12]}"

  git clone --single-branch \
            --branch ${LONGHORN_REPO_BRANCH} \
            ${LONGHORN_REPO_URI} \
            ${LONGHORN_REPO_DIR}

  cat "${LONGHORN_REPO_DIR}/deploy/longhorn.yaml" > "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # get longhorn default images from yaml manifest
  LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_UI_IMAGE=`grep -io "longhornio\/longhorn-ui:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SUPPORT_BUNDLE_IMAGE=`grep -io "longhornio\/support-bundle-kit:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_ATTACHER_IMAGE=`grep -io "longhornio\/csi-attacher:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_PROVISIONER_IMAGE=`grep -io "longhornio\/csi-provisioner:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=`grep -io "longhornio\/csi-node-driver-registrar:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_RESIZER_IMAGE=`grep -io "longhornio\/csi-resizer:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_SNAPSHOTTER_IMAGE=`grep -io "longhornio\/csi-snapshotter:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_LIVENESSPROBE_IMAGE=`grep -io "longhornio\/livenessprobe:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`

  # replace longhorn images with custom images
  if [[ -z "${REGISTRY_URL}" ]]; then
    sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  fi

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_UI_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_UI_IMAGE}'#'${CUSTOM_LONGHORN_UI_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_UI_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_UI_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_UI_IMAGE=${LONGHORN_UI_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_SUPPORT_BUNDLE_IMAGE}'#'${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_SUPPORT_BUNDLE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE=${LONGHORN_SUPPORT_BUNDLE_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_ATTACHER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_ATTACHER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE=${LONGHORN_CSI_ATTACHER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_PROVISIONER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_PROVISIONER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE=${LONGHORN_CSI_PROVISIONER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#'${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_RESIZER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_RESIZER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_RESIZER_IMAGE=${LONGHORN_CSI_RESIZER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE=${LONGHORN_CSI_SNAPSHOTTER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#'${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE=${LONGHORN_CSI_LIVENESSPROBE_IMAGE}
  fi

}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
