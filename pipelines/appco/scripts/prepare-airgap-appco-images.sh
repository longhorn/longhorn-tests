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

# Delete images if exist
for image in "${IMAGES[@]}"; do
  echo "Deleting ${image} if exists"
  docker rmi -f "${image}" || true
done

# Delete tagged images if exist
PRIVATE_REGISTERY_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep '^lh-registry-') || true

for image in ${PRIVATE_REGISTERY_IMAGES}; do
  echo "Deleting ${image} if exists"
  docker rmi -f "${image}" || true
done

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
