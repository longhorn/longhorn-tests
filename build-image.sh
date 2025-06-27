#!/bin/bash

REPO=${REPO:-longhornio}

version=$(./version)
manager_test_image="$REPO/longhorn-manager-test:${version}"
e2e_test_image="$REPO/longhorn-e2e-test:${version}"

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
BASE_IMAGE=$(grep FROM package/Dockerfile  | awk '{print $2}')
docker pull "${BASE_IMAGE}"

mkdir -p bin

docker build --build-arg TARGETPLATFORM="linux/${ARCH}" -t "${manager_test_image}" -f manager/integration/Dockerfile .
echo "${manager_test_image}" > bin/latest_image
echo Built manager test image "${manager_test_image}"

docker build --build-arg TARGETPLATFORM="linux/${ARCH}" -t "${e2e_test_image}" -f e2e/Dockerfile .
echo "${e2e_test_image}" >> bin/latest_image
echo Built e2e test image "${e2e_test_image}"
