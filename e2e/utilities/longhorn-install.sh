#!/usr/bin/env bash

set -x

source ../pipelines/utilities/longhorn_ui.sh
source ../pipelines/utilities/create_longhorn_namespace.sh
source ../pipelines/utilities/install_backupstores.sh
source ../pipelines/utilities/longhorn_status.sh
source ../pipelines/utilities/longhorn_helm_chart.sh
source ../pipelines/utilities/create_aws_secret.sh
source ../pipelines/utilities/longhorn_manifest.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
LONGHORN_NAMESPACE="longhorn-system"
LONGHORN_REPO_DIR="${TMPDIR}/longhorn"
LONGHORN_REPO_URI=${LONGHORN_REPO_URI:-"https://github.com/longhorn/longhorn.git"}
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

install_longhorn_by_chart(){
  get_longhorn_chart
  customize_longhorn_chart
  helm upgrade --install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace "${LONGHORN_NAMESPACE}"
  wait_longhorn_status_running
}

install_longhorn_stable_by_chart(){
  git clone --single-branch \
            --branch "${LONGHORN_STABLE_VERSION}" \
            "${LONGHORN_REPO_URI}" \
            "${LONGHORN_REPO_DIR}"
    helm upgrade --install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace "${LONGHORN_NAMESPACE}"
    wait_longhorn_status_running
}

install_longhorn_stable_by_manifest(){
  LONGHORN_STABLE_VERSION=${LONGHORN_STABLE_VERSION}
  LONGHORN_STABLE_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_STABLE_VERSION}/deploy/longhorn.yaml"  
  install_longhorn_by_manifest "${LONGHORN_STABLE_MANIFEST_URL}"
}

install_longhorn(){
  create_longhorn_namespace
  install_backupstores
  if [[ "${LONGHORN_INSTALL_METHOD}" == "helm" ]]; then
    install_longhorn_by_chart
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "manifest" ]]; then
    generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
    install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
  fi
  setup_longhorn_ui_nodeport
}

install_longhorn_stable_version(){
  create_longhorn_namespace
  install_backupstores
  if [[ "${LONGHORN_INSTALL_METHOD}" == "helm" ]]; then
    install_longhorn_stable_by_chart
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "manifest" ]]; then
    install_longhorn_stable_by_manifest
  fi
  setup_longhorn_ui_nodeport
}

if [[ $# -gt 0 ]]; then
    $1  # Run the function passed as the first argument
else
    install_longhorn
fi
