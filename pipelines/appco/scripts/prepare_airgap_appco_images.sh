#!/bin/bash
set -e

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

tag_and_push_custom_image() {
  local image="$1"
  local target_image=""

  target_image="${image/dp.apps.rancher.io/${APPCO_LONGHORN_COMPONENT_IMAGE_PATH}}"
  target_image="${REGISTRY_URL}/${target_image}"

  echo "Tagging ${image} to ${target_image}"
  docker tag "${image}" "${target_image}"

  echo "Pushing ${target_image}"
  docker push "${target_image}"
}

#tag_and_push_upgrade_image() {
tag_and_push_image() {
  local image="$1"
  local target_image=""
    
  target_image="${REGISTRY_URL}/${image}"

  echo "Tagging ${image} to ${target_image}"
  docker tag "${image}" "${target_image}"

  echo "Pushing ${target_image}"
  docker push "${target_image}"
}


mirror_longhorn_images(){
  # Login to AppCo
  echo "${APPCO_PASSWORD}" | docker login dp.apps.rancher.io --username "${APPCO_USERNAME}" --password-stdin

  # Pull images
  for image in "${IMAGES[@]}"; do
    echo "Pulling ${image}"
    docker pull --platform linux/${TF_VAR_arch} "${image}"
  done

  # Login to target registry
  echo "Logging into ${REGISTRY_URL}"
  docker login "${REGISTRY_URL}" -u "${REGISTRY_USERNAME}" -p "${REGISTRY_PASSWORD}"

  # Tag & Push images
  for image in "${IMAGES[@]}"; do
    #tag_and_push_custom_image "$image"
    tag_and_push_image "$image"
  done

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    if [[ -n "$LONGHORN_STABLE_VERSION" ]]; then
      for image in "${STABLE_VERSION_IMAGES[@]}"; do
        echo "Pulling ${image}"
        docker pull --platform linux/${TF_VAR_arch} "${image}"
      done
      for image in "${STABLE_VERSION_IMAGES[@]}"; do
        #tag_and_push_upgrade_image "$image"
        tag_and_push_image "$image"
      done
    fi
    if [[ -n "$LONGHORN_TRANSIENT_VERSION" ]]; then
      for image in "${TRANSIENT_VERSION_IMAGES[@]}"; do
        echo "Pulling ${image}"
        docker pull --platform linux/${TF_VAR_arch} "${image}"
      done
      for image in "${TRANSIENT_VERSION_IMAGES[@]}"; do
        #tag_and_push_upgrade_image "$image"
        tag_and_push_image "$image"
      done
    fi
  fi
}

mirror_longhorn_images
