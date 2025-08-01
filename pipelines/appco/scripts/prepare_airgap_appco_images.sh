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

mirror_longhorn_images(){
  # Login to AppCo
  echo "${APPCO_PASSWORD}" | docker login dp.apps.rancher.io --username "${APPCO_USERNAME}" --password-stdin

  # Pull images
  for image in "${IMAGES[@]}"; do
    echo "Pulling ${image}"
    docker pull --platform linux/${TF_VAR_arch} "${image}"
  done

  # Tag images
  for image in "${IMAGES[@]}"; do
    echo "Tagging ${image} to ${REGISTRY_URL}/${image}"
    docker tag "${image}" "${REGISTRY_URL}/${image}"
  done

  # Login
  echo "Logging into ${REGISTRY_URL}"
  docker login "${REGISTRY_URL}" -u "${REGISTRY_USERNAME}" -p "${REGISTRY_PASSWORD}"

  # Push images
  for image in "${IMAGES[@]}"; do
    echo "Pushing ${REGISTRY_URL}/${image}"
    docker push "${REGISTRY_URL}/${image}"
  done

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    if [[ -n "$LONGHORN_STABLE_VERSION" ]]; then
      # Pull stable version images
      for image in "${STABLE_VERSION_IMAGES[@]}"; do
        echo "Pulling ${image}"
        docker pull --platform linux/${TF_VAR_arch} "${image}"
      done

      # Tag stable version images
      for image in "${STABLE_VERSION_IMAGES[@]}"; do
        echo "Tagging ${image} to ${REGISTRY_URL}/${image}"
        docker tag "${image}" "${REGISTRY_URL}/${image}"
      done

      # Push stable version images
      for image in "${STABLE_VERSION_IMAGES[@]}"; do
        echo "Pushing ${REGISTRY_URL}/${image}"
        docker push "${REGISTRY_URL}/${image}"
      done
    fi
    if [[ -n "$LONGHORN_TRANSIENT_VERSION" ]]; then
      # Pull transient version images
      for image in "${TRANSIENT_VERSION_IMAGES[@]}"; do
        echo "Pulling ${image}"
        docker pull --platform linux/${TF_VAR_arch} "${image}"
      done

      # Tag transient version images
      for image in "${TRANSIENT_VERSION_IMAGES[@]}"; do
        echo "Tagging ${image} to ${REGISTRY_URL}/${image}"
        docker tag "${image}" "${REGISTRY_URL}/${image}"
      done

      # Push transient version images
      for image in "${TRANSIENT_VERSION_IMAGES[@]}"; do
        echo "Pushing ${REGISTRY_URL}/${image}"
        docker push "${REGISTRY_URL}/${image}"
      done
    fi
  fi
}

mirror_longhorn_images

