#!/bin/bash

set -x

export LONGHORN_REPO_URI="${1}"
export LONGHORN_REPO_BRANCH="${2}"
export CUSTOM_LONGHORN_MANAGER_IMAGE="${3}"
export CUSTOM_LONGHORN_ENGINE_IMAGE="${4}"
export CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${5}"
export CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${6}"
export CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${7}"

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_helm_chart.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

get_longhorn_chart
customize_longhorn_chart
install_longhorn
