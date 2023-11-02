#!/usr/bin/env bash

set -x

export LONGHORN_REPO_URI="${1}"
export LONGHORN_INSTALL_VERSION="${2}"

source pipelines/utilities/argocd.sh
source pipelines/utilities/kubeconfig.sh

export LONGHORN_NAMESPACE="longhorn-system"

construct_kubeconfig

init_argocd

kubectl config get-contexts
kubectl config view

update_argocd_app_target_revision "${LONGHORN_INSTALL_VERSION}"
sync_argocd_app
