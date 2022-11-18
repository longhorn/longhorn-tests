#!/usr/bin/env bash

set -x

terraform -chdir=${WORKSPACE}/test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} init
terraform -chdir=${WORKSPACE}/test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} apply -auto-approve -no-color

exit $?