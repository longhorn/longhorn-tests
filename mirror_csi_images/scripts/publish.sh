#!/bin/bash

INFILE="${PWD}/infile"
touch "${INFILE}"

if [[ -n "${LONGHORN_IMAGES_FILE_URL}" ]]; then

  LONGHORN_IMAGES_FILE=${PWD}/longhorn-images.txt
  if [[ "${LONGHORN_IMAGES_FILE_URL}" =~ "oci://dp.apps.rancher.io/charts/suse-storage" ]]; then
    set +x
    helm registry login dp.apps.rancher.io --username "${APPCO_USERNAME}" --password "${APPCO_PASSWORD}"
    set -x
    helm pull "${LONGHORN_IMAGES_FILE_URL}" --untar --untardir "${PWD}"
    yq '.images[].image' ./suse-storage/images-lock.yaml > "${LONGHORN_IMAGES_FILE}"
  else
    wget "${LONGHORN_IMAGES_FILE_URL}" -O "${LONGHORN_IMAGES_FILE}"
  fi

  while read -r LINE; do
    if [[ "${LINE}" =~ "registry.suse.de" ]] || [[ "${LINE}" =~ "dp.apps.rancher.io" ]]; then
      IFS=: read -ra IMAGE_TAG_PAIR <<< "${LINE}"
      echo "${IMAGE_TAG_PAIR[0]}" "${AWS_PRIVATE_ECR}/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${LINE}" =~ csi-|livenessprobe ]]; then
      CSI_IMAGE=$(echo "${LINE}" | sed -e "s/longhornio\///g")
      IFS=: read -ra IMAGE_TAG_PAIR <<< "${CSI_IMAGE}"
      echo "registry.k8s.io/sig-storage/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${LINE}" =~ "support-bundle-kit" ]]; then
      SUPPORT_BUNDLE_KIT_IMAGE=$(echo "${LINE}" | sed -e "s/longhornio\///g")
      IFS=: read -ra IMAGE_TAG_PAIR <<< "${SUPPORT_BUNDLE_KIT_IMAGE}"
      echo "rancher/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${LINE}" =~ "openshift-origin-oauth-proxy" ]]; then
      OPENSHIFT_OAUTH_PROXY=$(echo "${LINE}" | sed -e "s/longhornio\/openshift-//g")
      IFS=: read -ra IMAGE_TAG_PAIR <<< "${OPENSHIFT_OAUTH_PROXY}"
      echo "quay.io/openshift/${IMAGE_TAG_PAIR[0]}" "longhornio/openshift-${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    fi
  done < "${LONGHORN_IMAGES_FILE}"
else
  IFS=, read -ra CSI_IMAGES_ARR <<< "${CSI_IMAGES}"
  for CSI_IMAGE in "${CSI_IMAGES_ARR[@]}"; do
    IFS=: read -ra IMAGE_TAG_PAIR <<< "$CSI_IMAGE"
    if [[ "${CSI_IMAGE}" =~ "registry.suse.de" ]] || [[ "${CSI_IMAGE}" =~ "dp.apps.rancher.io" ]]; then
      echo "${IMAGE_TAG_PAIR[0]}" "${AWS_PRIVATE_ECR}/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${CSI_IMAGE}" =~ csi-|livenessprobe ]]; then
      echo "registry.k8s.io/sig-storage/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${CSI_IMAGE}" =~ "support-bundle-kit" ]]; then
      echo "rancher/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    elif [[ "${CSI_IMAGE}" =~ "openshift-origin-oauth-proxy" ]]; then
      echo "quay.io/openshift/origin-oauth-proxy" "longhornio/openshift-origin-oauth-proxy" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    fi
  done
fi

docker login -u "${DOCKER_USERNAME}" -p "${DOCKER_PASSWORD}"
echo "${APPCO_PASSWORD}" | docker login dp.apps.rancher.io --username "${APPCO_USERNAME}" --password-stdin
aws ecr get-login-password --region "${AWS_DEFAULT_REGION}" | docker login --username AWS --password-stdin "${AWS_PRIVATE_ECR}"

"${PWD}/mirror_csi_images/scripts/image-mirror.sh" "${INFILE}"
