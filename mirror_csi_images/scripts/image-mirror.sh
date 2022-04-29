#!/bin/bash

set -uo pipefail
export DOCKER_CLI_EXPERIMENTAL="enabled"

ARCH_LIST="amd64 arm64 arm s390x"

function copy_if_changed {
  SOURCE_REF="${1}"
  DEST_REF="${2}"
  ARCH="${3}"
  EXTRA_ARGS="${4:-}"

  SOURCE_MANIFEST=$(skopeo inspect docker://${SOURCE_REF} --raw 2>/dev/null)
  if [ "${#SOURCE_MANIFEST}" -gt 0 ]; then
    SOURCE_DIGEST="sha256:"$(echo -n "${SOURCE_MANIFEST}" | sha256sum | awk '{print $1}')
  else
    SOURCE_DIGEST="MISSING"
  fi

  DEST_MANIFEST=$(skopeo inspect docker://${DEST_REF} --raw 2>/dev/null)
  if [ "${#DEST_MANIFEST}" -gt 0 ]; then
    DEST_DIGEST="sha256:"$(echo -n "${DEST_MANIFEST}" | sha256sum | awk '{print $1}')
  else
    DEST_DIGEST="MISSING"
  fi

  if [ "${SOURCE_DIGEST}" == "${DEST_DIGEST}" ]; then
    echo -e "\tUnchanged: ${SOURCE_REF} == ${DEST_REF}"
    echo -e "\t           ${SOURCE_DIGEST}"
  else
    echo -e "\tCopying ${SOURCE_REF} => ${DEST_REF}"
    echo -e "\t        ${SOURCE_DIGEST} => ${DEST_DIGEST}"
    skopeo copy --override-arch=${ARCH} docker://${SOURCE_REF} docker://${DEST_REF} ${EXTRA_ARGS}
  fi
}


function set_repo_description {
  SOURCE_SPEC="${1}"
  DEST_SPEC="${2}"

  trap 'echo -e "===\nFailed to set description for ${DEST_SPEC}\n==="' ERR

  # Updates the Overview tab on Docker Hub with a description of the source and tag.
  if [ -n "${DOCKER_TOKEN:-}" ] && grep -qF 'docker.io' <<< ${DEST_SPEC}; then
    echo "Updating description for ${DEST_SPEC}"
    MESSAGE=$(sed -E 's/^\s+//g' <<< "This repository is an automated partial mirror of  \`${SOURCE_SPEC}\`.
                                             For more information see <https://github.com/rancher/image-mirror>.
                                             ")
    PAYLOAD=$(jq -n --arg MESSAGE "${MESSAGE}" '{"registry":"docker.io","full_description":$MESSAGE}')
    curl -s -o /dev/null -d @- -X PATCH \
      -H "Content-Type: application/json" \
      -H "Authorization: JWT ${DOCKER_TOKEN}" \
      "https://hub.docker.com/v2/repositories/${DEST_SPEC/docker.io\//}/" <<< ${PAYLOAD}
  fi
}

function mirror_image {
  SOURCE_SPEC="${1}"
  DEST_SPEC="${2}"
  TAG="${3}"

  trap 'echo -e "===\nFailed copying image for ${DEST_SPEC}\n==="' ERR

  # ensure that source specifies an explicit registry and repository
  IFS=/ read -a SOURCE <<< ${SOURCE_SPEC}
  if grep -vqE '[.:]|localhost' <<< ${SOURCE[0]}; then
    SOURCE=("docker.io" "${SOURCE[@]}")
  fi

  # recombine source spec
  printf -v SOURCE "/%s" "${SOURCE[@]}"; SOURCE=${SOURCE:1}

  # ensure that dest specifies an explicit registry and repository
  IFS=/ read -a DEST <<< ${DEST_SPEC}
  if grep -vqE '[.:]|localhost' <<< ${DEST[0]}; then
    DEST=("docker.io" "${DEST[@]}")
  fi

  # override destination registry if set
  if [ -n "${DEST_REGISTRY_OVERRIDE:-}" ]; then
    DEST[0]=${DEST_REGISTRY_OVERRIDE}
  fi

  # override destination org/user if set
  if [ -n "${DEST_ORG_OVERRIDE:-}" ]; then
    DEST[1]="${DEST_ORG_OVERRIDE}"
  fi

  # recombine dest spec
  printf -v DEST "/%s" "${DEST[@]}"; DEST=${DEST:1}

  # Grab raw manifest or manifest list and extract schema info
  MANIFEST=$(skopeo inspect docker://${SOURCE}:${TAG} --raw)
  SCHEMAVERSION=$(jq -r '.schemaVersion' <<< ${MANIFEST})
  MEDIATYPE=$(jq -r '.mediaType' <<< ${MANIFEST})
  SOURCES=()
  DIGESTS=()

  # Most everything should use a v2 schema, but some old images (on quay.io mostly) are still on v1
  if [ "${SCHEMAVERSION}" == "2" ]; then

    # Handle manifest lists by copying all the architectures (and their variants) out to individual suffixed tags in the destination,
    # then recombining them into a single manifest list on the bare tags.
    if [ "${MEDIATYPE}" == "application/vnd.docker.distribution.manifest.list.v2+json" ]; then
      echo "${SOURCE}:${TAG} is manifest.list.v2"
      for ARCH in ${ARCH_LIST}; do
        VARIANT_INDEX="0"
        DIGEST_VARIANT_LIST=$(jq -r --arg ARCH "${ARCH}" \
          '.manifests | map(select(.platform.architecture == $ARCH))
                      | sort_by(.platform.variant)
                      | reverse
                      | map(.digest + " " + .platform.variant)
                      | join("\n")' <<< ${MANIFEST});
        while read DIGEST VARIANT; do
          # Add skopeo flags for multi-variant architectures (arm, mostly)
          if [ -z "${VARIANT}" ] || [ "${VARIANT}" == "null" ]; then
            VARIANT=""
          fi

          # Make the first variant the default for this arch by omitting it from the tag
          if [ "${VARIANT_INDEX}" -eq 0 ]; then
            VARIANT=""
          fi

          if [ -z "${DIGEST}" ] || [ "${DIGEST}" == "null" ]; then
            echo -e "\t${ARCH} NOT FOUND"
          else
            # We have to copy the full descriptor here; if we just point buildx at another tag or hash it will lose the variant
            # info since that's not stored anywhere outside the manifest list itself.
            copy_if_changed "${SOURCE}@${DIGEST}" "${DEST}:${TAG}-${ARCH}${VARIANT}" "${ARCH}"
            DESCRIPTOR=$(jq -c -r --arg DIGEST "${DIGEST}" '.manifests | map(select(.digest == $DIGEST)) | first' <<< ${MANIFEST})
            SOURCES+=("${DESCRIPTOR}")
            DIGESTS+=("${DIGEST}")
            ((++VARIANT_INDEX))
          fi
        done <<< ${DIGEST_VARIANT_LIST}
      done

    # Standalone manifests don't include architecture info, we have to get that from the image config
    elif [ "${MEDIATYPE}" == "application/vnd.docker.distribution.manifest.v2+json" ]; then
      echo "${SOURCE}:${TAG} is manifest.v2"
      CONFIG=$(skopeo inspect docker://${SOURCE}:${TAG} --config --raw)
      ARCH=$(jq -r '.architecture' <<< ${CONFIG})
      DIGEST=$(jq -r '.config.digest' <<< ${MANIFEST})
      if grep -wqF ${ARCH} <<< ${ARCH_LIST}; then
        copy_if_changed "${SOURCE}:${TAG}" "${DEST}:${TAG}-${ARCH}" "${ARCH}"
        SOURCES+=("${DEST}:${TAG}-${ARCH}")
        DIGESTS+=("${DIGEST}")
      fi
    else
      echo "${SOURCE}:${TAG} has unknown mediaType ${MEDIATYPE}"
      return 1
    fi

  # v1 manifests contain arch but no variant, but can be treated similar to manifest.v2
  # We upconvert to v2 schema on copy, since v1 manifests cannot be added to manifest lists
  elif [ "${SCHEMAVERSION}" == "1" ]; then
    echo "${SOURCE}:${TAG} is manifest.v1"
    ARCH=$(jq -r '.architecture' <<< ${MANIFEST})
    if grep -wqF ${ARCH} <<< ${ARCH_LIST}; then
      if copy_if_changed "${SOURCE}:${TAG}" "${DEST}:${TAG}-${ARCH}" "${ARCH}" "--format=v2s2"; then
        SOURCES+=("${DEST}:${TAG}-${ARCH}")
        DIGESTS+=("${DIGEST}")
      fi
    fi
  else
    echo "${SOURCE}:${TAG} has unknown schemaVersion ${SCHEMAVERSION}"
    return 1
  fi

  NEW_DIGESTS=$(printf '%s\n' "${DIGESTS[@]}" | sort)
  CUR_MANIFEST=$(skopeo inspect docker://${DEST}:${TAG} --raw 2>/dev/null || true)
  CUR_SCHEMAVERSION=$(jq -r '.schemaVersion' <<< ${CUR_MANIFEST})
  CUR_MEDIATYPE=$(jq -r '.mediaType' <<< ${CUR_MANIFEST})

  if [ "${CUR_SCHEMAVERSION}" == "2" ] && [ "${CUR_MEDIATYPE}" == "application/vnd.docker.distribution.manifest.list.v2+json" ]; then
    CUR_DIGESTS=$(jq -r '.manifests[].digest' <<< ${CUR_MANIFEST} | sort)
  else
    CUR_DIGESTS=""
  fi

  if [ "${NEW_DIGESTS}" == "${CUR_DIGESTS}" ]; then
    echo -e "\tNo changes to manifest list for ${DEST}:${TAG}"
  else
    echo -e "\tWriting manifest list to ${DEST}:${TAG}\n${NEW_DIGESTS}"
    docker buildx imagetools create --tag ${DEST}:${TAG} "${SOURCES[@]}"
    set_repo_description ${SOURCE} ${DEST}
  fi
}

# Figure out if we should read input from a file or stdin
# If we're given a file, verify that it exists
if [ -n "${1:-}" ]; then
  INFILE="${1}"
  if [ ! -f "${INFILE}" ]; then
    echo "File ${INFILE} does not exist!"
    exit 1
  fi
else
  INFILE="/dev/stdin"
fi

echo "Reading SOURCE DESTINATION TAG from ${INFILE}"
while IFS= read -r LINE; do
  echo -e "\nLine: ${LINE}"
  if grep -P '^(?!\s*(#|//))\S+\s+\S+\s+\S+' <<< ${LINE}; then
    mirror_image ${LINE}
  fi
done < "${INFILE}"