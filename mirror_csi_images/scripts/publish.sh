#!/bin/bash

INFILE="${PWD}/infile"
touch "${INFILE}"

if [[ -n "${LONGHORN_IMAGES_FILE_URL}" ]]; then

  LONGHORN_IMAGES_FILE=${PWD}/longhorn-images.txt
  wget "${LONGHORN_IMAGES_FILE_URL}" -O "${LONGHORN_IMAGES_FILE}"

  while read -r LINE; do
    if [[ "${LINE}" =~ "csi-" ]]; then
      CSI_IMAGE=$(echo "${LINE}" | sed -e "s/longhornio\///g")
      IFS=: read -ra IMAGE_TAG_PAIR <<< "${CSI_IMAGE}"
      echo "k8s.gcr.io/sig-storage/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
    fi
  done < "${LONGHORN_IMAGES_FILE}"
else
  IFS=, read -ra CSI_IMAGES_ARR <<< "${CSI_IMAGES}"
  for CSI_IMAGE in "${CSI_IMAGES_ARR[@]}"; do
    IFS=: read -ra IMAGE_TAG_PAIR <<< "$CSI_IMAGE"
    echo "k8s.gcr.io/sig-storage/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> "${INFILE}"
  done
fi

docker login -u "${DOCKER_USERNAME}" -p "${DOCKER_PASSWORD}"

"${PWD}/mirror_csi_images/scripts/image-mirror.sh" "${INFILE}"
