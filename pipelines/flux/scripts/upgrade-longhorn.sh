#!/usr/bin/env bash

set -x

export HELM_CHART_URL="${1}"
export HELM_CHART_VERSION="${2}"

source pipelines/utilities/flux.sh

export LONGHORN_NAMESPACE="longhorn-system"

create_flux_helm_repo "${HELM_CHART_URL}"
create_flux_helm_release "${HELM_CHART_VERSION}"
