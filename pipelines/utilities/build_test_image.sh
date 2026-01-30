#!/bin/bash

build_test_image(){
  set -e
  ECR_URL="public.ecr.aws/${AWS_ECR_ALIAS}"
  REPO_NAME="longhornio/longhorn-e2e-test"
  # cannot use branch name as image tag
  # because it may contain invalid characters
  FULL_IMAGE_NAME="${ECR_URL}/${REPO_NAME}:${PR_NUMBER}"

  aws ecr-public get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin public.ecr.aws

  rm -rf /tmp/longhorn-tests
  git clone --single-branch --branch "${LONGHORN_TESTS_BRANCH}" --depth 1 "${LONGHORN_TESTS_REPO}" /tmp/longhorn-tests
  cd /tmp/longhorn-tests/
  docker build -t "${FULL_IMAGE_NAME}" -f e2e/Dockerfile .
  docker push "${FULL_IMAGE_NAME}"
  export LONGHORN_TESTS_CUSTOM_IMAGE="${FULL_IMAGE_NAME}"
  cd -
  echo "${PWD}"
  set +e
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
