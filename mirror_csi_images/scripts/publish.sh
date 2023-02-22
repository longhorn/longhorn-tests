#!/bin/bash

INFILE="${PWD}/infile"
touch $INFILE

IFS=, read -ra CSI_IMAGES_ARR <<< "${CSI_IMAGES}"
for CSI_IMAGE in "${CSI_IMAGES_ARR[@]}"; do
  IFS=: read -ra IMAGE_TAG_PAIR <<< "$CSI_IMAGE"
  echo "registry.k8s.io/sig-storage/${IMAGE_TAG_PAIR[0]}" "longhornio/${IMAGE_TAG_PAIR[0]}" "${IMAGE_TAG_PAIR[1]}" >> $INFILE
done

docker login -u "${DOCKER_USERNAME}" -p "${DOCKER_PASSWORD}"

"${PWD}/mirror_csi_images/scripts/image-mirror.sh" $INFILE
