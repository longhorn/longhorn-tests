#!/usr/bin/env bash

set -x

export RANCHER_HOSTNAME="${1}"
export RANCHER_ACCESS_KEY="${2}"
export RANCHER_SECRET_KEY="${3}"
export LONGHORN_INSTALL_VERSION="${4}"
export LONGHORN_REPO="${5}"

source pipelines/utilities/longhorn_rancher_chart.sh

export LONGHORN_NAMESPACE="longhorn-system"

upgrade_longhorn_rancher_chart
