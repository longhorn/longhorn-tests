#!/bin/bash
set -e

TMP_DIR="/tmp/longhorn-images-tmp"
mkdir -p "${TMP_DIR}"
rm -rf "${TMP_DIR:?}/"*
cd ${TMP_DIR}

DP_IMAGE_PATH="dp.apps.rancher.io/containers"

parse_appco_chart(){
  chart_uri="$1"
  chart_version="$2"
  file_name="$3"

  chart_ref="${chart_uri}:${chart_version}"
  target_dir=appco-${chart_version}

  # Check for dependencies
  for cmd in yq jq helm tar; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo >&2 "Error: '$cmd' is required but not installed."
      exit 1
    fi
  done

  mkdir -p "${target_dir}"
  rm -rf "${target_dir:?}/"*
  helm pull "${chart_uri}" --version "${chart_version}"
  tar -xzf "$(ls -1 *${chart_version}*.tgz | head -n 1)" --strip-components=1 -C "${target_dir}"

  # Extract 'helm.sh/images' annotation and convert to JSON
  images_json=$(
    yq eval '.annotations."helm.sh/images"' "$target_dir/Chart.yaml" | yq -o=json eval -
  )

  # Directly print image list (one per line)
  echo "${images_json}" | jq -r '.[] | .image' > "${file_name}"
}

get_test_images(){
  CUSTOM_LONGHORN_ENGINE_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-engine:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-instance-manager:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_MANAGER_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-manager:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-share-manager:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-backing-image-manager:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_UI_IMAGE="${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}/longhorn-ui:${LONGHORN_COMPONENT_TAG}"
  CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE="${DP_IMAGE_PATH}/rancher-support-bundle-kit:${SUPPORT_BUNDLE_TAG}"
  CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-external-attacher:${CSI_ATTACHER_TAG}"
  CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-external-provisioner:${CSI_PROVISIONER_TAG}"
  CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-node-driver-registrar:${CSI_REGISTRAR_TAG}"
  CUSTOM_LONGHORN_CSI_RESIZER_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-external-resizer:${CSI_RESIZER_TAG}"
  CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-external-snapshotter:${CSI_SNAPSHOTTER_TAG}"
  CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE="${DP_IMAGE_PATH}/kubernetes-csi-livenessprobe:${CSI_LIVENESSPROBE_TAG}"
}

get_stable_upgrade_images(){
  file_name="longhorn-stable-version-images.txt"

  if [[ "${LONGHORN_STABLE_VERSION_CHART_URI}" == "longhorn/longhorn" ]]; then
    wget https://raw.githubusercontent.com/longhorn/longhorn/v${LONGHORN_STABLE_VERSION#v}/deploy/longhorn-images.txt -O "./${file_name}"
  else
    target_dir=appco-${LONGHORN_STABLE_VERSION}
    parse_appco_chart "${LONGHORN_STABLE_VERSION_CHART_URI}" "${LONGHORN_STABLE_VERSION}" "${file_name}"
  fi
  STABLE_ENGINE_IMAGE=$(grep 'longhorn-engine:' "${file_name}" || true)
  STABLE_INSTANCE_MANAGER_IMAGE=$(grep 'longhorn-instance-manager:' "${file_name}" || true)
  STABLE_MANAGER_IMAGE=$(grep 'longhorn-manager:' "${file_name}" || true)
  STABLE_SHARE_MANAGER_IMAGE=$(grep 'longhorn-share-manager:' "${file_name}" || true)
  STABLE_BACKING_IMAGE_MANAGER_IMAGE=$(grep 'backing-image-manager:' "${file_name}" || true)
  STABLE_UI_IMAGE=$(grep 'longhorn-ui:' "${file_name}" || true)
  STABLE_SUPPORT_BUNDLE_IMAGE=$(grep 'support-bundle-kit:' "${file_name}" || true)
  STABLE_CSI_ATTACHER_IMAGE=$(grep 'attacher:' "${file_name}" || true)
  STABLE_CSI_PROVISIONER_IMAGE=$(grep 'provisioner:' "${file_name}" || true)
  STABLE_CSI_NODE_REGISTRAR_IMAGE=$(grep 'node-driver-registrar:' "${file_name}" || true)
  STABLE_CSI_RESIZER_IMAGE=$(grep 'resizer:' "${file_name}" || true)
  STABLE_CSI_SNAPSHOTTER_IMAGE=$(grep 'snapshotter:' "${file_name}" || true)
  STABLE_CSI_LIVENESSPROBE_IMAGE=$(grep 'livenessprobe:' "${file_name}" || true)
}

get_transient_upgrade_images(){
  file_name="longhorn-transient-version-images.txt"
  if [[ "${LONGHORN_TRANSIENT_VERSION_CHART_URI}" == "longhorn/longhorn" ]]; then
    wget https://raw.githubusercontent.com/longhorn/longhorn/v${LONGHORN_TRANSIENT_VERSION#v}/deploy/longhorn-images.txt -O "./${file_name}"
  else
   target_dir=appco-${LONGHORN_TRANSIENT_VERSION}
    parse_appco_chart "${LONGHORN_TRANSIENT_VERSION_CHART_URI}" "${LONGHORN_TRANSIENT_VERSION}" "${file_name}"
  fi
  TRANSIENT_ENGINE_IMAGE=$(grep 'longhorn-engine:' "${file_name}" || true)
  TRANSIENT_INSTANCE_MANAGER_IMAGE=$(grep 'longhorn-instance-manager:' "${file_name}" || true)
  TRANSIENT_MANAGER_IMAGE=$(grep 'longhorn-manager:' "${file_name}" || true)
  TRANSIENT_SHARE_MANAGER_IMAGE=$(grep 'longhorn-share-manager:' "${file_name}" || true)
  TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE=$(grep 'backing-image-manager:' "${file_name}" || true)
  TRANSIENT_UI_IMAGE=$(grep 'longhorn-ui:' "${file_name}" || true)
  TRANSIENT_SUPPORT_BUNDLE_IMAGE=$(grep 'support-bundle-kit:' "${file_name}" || true)
  TRANSIENT_CSI_ATTACHER_IMAGE=$(grep 'attacher:' "${file_name}" || true)
  TRANSIENT_CSI_PROVISIONER_IMAGE=$(grep 'provisioner:' "${file_name}" || true)
  TRANSIENT_CSI_NODE_REGISTRAR_IMAGE=$(grep 'node-driver-registrar:' "${file_name}" || true)
  TRANSIENT_CSI_RESIZER_IMAGE=$(grep 'resizer:' "${file_name}" || true)
  TRANSIENT_CSI_SNAPSHOTTER_IMAGE=$(grep 'snapshotter:' "${file_name}" || true)
  TRANSIENT_CSI_LIVENESSPROBE_IMAGE=$(grep 'livenessprobe:' "${file_name}" || true)
}

init_image_arrays() {
  IMAGES=(
    "${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    "${CUSTOM_LONGHORN_MANAGER_IMAGE}"
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
}

write_longhorn_env_vars(){
  # For Jenkins source and use those images
  cat <<EOF > /tmp/longhorn_env_vars.sh
export CUSTOM_LONGHORN_ENGINE_IMAGE="${CUSTOM_LONGHORN_ENGINE_IMAGE}"
export CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
export CUSTOM_LONGHORN_MANAGER_IMAGE="${CUSTOM_LONGHORN_MANAGER_IMAGE}"
export CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
export CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
export CUSTOM_LONGHORN_UI_IMAGE="${CUSTOM_LONGHORN_UI_IMAGE}"
export CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE="${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}"
export CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE="${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}"
export CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE="${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}"
export CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE="${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}"
export CUSTOM_LONGHORN_CSI_RESIZER_IMAGE="${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}"
export CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE="${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}"
export CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE="${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}"
export STABLE_MANAGER_IMAGE="${STABLE_MANAGER_IMAGE}"
export STABLE_ENGINE_IMAGE="${STABLE_ENGINE_IMAGE}"
export STABLE_INSTANCE_MANAGER_IMAGE="${STABLE_INSTANCE_MANAGER_IMAGE}"
export STABLE_SHARE_MANAGER_IMAGE="${STABLE_SHARE_MANAGER_IMAGE}"
export STABLE_BACKING_IMAGE_MANAGER_IMAGE="${STABLE_BACKING_IMAGE_MANAGER_IMAGE}"
export STABLE_UI_IMAGE="${STABLE_UI_IMAGE}"
export STABLE_SUPPORT_BUNDLE_IMAGE="${STABLE_SUPPORT_BUNDLE_IMAGE}"
export STABLE_CSI_ATTACHER_IMAGE="${STABLE_CSI_ATTACHER_IMAGE}"
export STABLE_CSI_PROVISIONER_IMAGE="${STABLE_CSI_PROVISIONER_IMAGE}"
export STABLE_CSI_NODE_REGISTRAR_IMAGE="${STABLE_CSI_NODE_REGISTRAR_IMAGE}"
export STABLE_CSI_RESIZER_IMAGE="${STABLE_CSI_RESIZER_IMAGE}"
export STABLE_CSI_SNAPSHOTTER_IMAGE="${STABLE_CSI_SNAPSHOTTER_IMAGE}"
export STABLE_CSI_LIVENESSPROBE_IMAGE="${STABLE_CSI_LIVENESSPROBE_IMAGE}"
export TRANSIENT_MANAGER_IMAGE="${TRANSIENT_MANAGER_IMAGE}"
export TRANSIENT_ENGINE_IMAGE="${TRANSIENT_ENGINE_IMAGE}"
export TRANSIENT_INSTANCE_MANAGER_IMAGE="${TRANSIENT_INSTANCE_MANAGER_IMAGE}"
export TRANSIENT_SHARE_MANAGER_IMAGE="${TRANSIENT_SHARE_MANAGER_IMAGE}"
export TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE="${TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE}"
export TRANSIENT_UI_IMAGE="${TRANSIENT_UI_IMAGE}"
export TRANSIENT_SUPPORT_BUNDLE_IMAGE="${TRANSIENT_SUPPORT_BUNDLE_IMAGE}"
export TRANSIENT_CSI_ATTACHER_IMAGE="${TRANSIENT_CSI_ATTACHER_IMAGE}"
export TRANSIENT_CSI_PROVISIONER_IMAGE="${TRANSIENT_CSI_PROVISIONER_IMAGE}"
export TRANSIENT_CSI_NODE_REGISTRAR_IMAGE="${TRANSIENT_CSI_NODE_REGISTRAR_IMAGE}"
export TRANSIENT_CSI_RESIZER_IMAGE="${TRANSIENT_CSI_RESIZER_IMAGE}"
export TRANSIENT_CSI_SNAPSHOTTER_IMAGE="${TRANSIENT_CSI_SNAPSHOTTER_IMAGE}"
export TRANSIENT_CSI_LIVENESSPROBE_IMAGE="${TRANSIENT_CSI_LIVENESSPROBE_IMAGE}"
EOF
}

helm_login_appco(){
  helm registry login dp.apps.rancher.io \
    --username "${APPCO_USERNAME}" \
    --password "${APPCO_PASSWORD}"
}

# set debugging mode off to avoid leaking appco secrets to the logs.
# DON'T REMOVE!    
set +x
helm_login_appco
set -x

get_test_images

if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
   get_stable_upgrade_images
fi

if [[ -n "${LONGHORN_TRANSIENT_VERSION}" && "${LONGHORN_UPGRADE_TEST}" == true ]]; then
  get_transient_upgrade_images
fi

init_image_arrays
write_longhorn_env_vars
