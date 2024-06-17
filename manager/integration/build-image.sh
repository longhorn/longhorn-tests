#!/bin/bash

REPO=${REPO:-longhornio}

version=$(./scripts/version)
image="$REPO/longhorn-manager-test:${version}"

case $(uname -m) in
        aarch64 | arm64)
                ARCH=arm64
                ;;
        x86_64)
                ARCH=amd64
                ;;
        *)
                echo "$(uname -a): unsupported architecture"
                exit 1
esac

echo "Building for ${ARCH}"
# update base image to get latest changes
BASE_IMAGE=`grep FROM package/Dockerfile  | awk '{print $2}'`
docker pull ${BASE_IMAGE}

docker build --build-arg TARGETPLATFORM="linux/${ARCH}" -t ${image} .
mkdir -p bin
echo ${image} > bin/latest_image
echo Built image ${image}
