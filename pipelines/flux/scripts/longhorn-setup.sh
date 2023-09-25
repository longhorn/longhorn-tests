#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/flux.sh
source pipelines/utilities/run_longhorn_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_INSTALL_METHOD="flux"
export HELM_CHART_DEFAULT_URL="https://charts.longhorn.io"


main(){
  set_kubeconfig

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi

  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  set -x

  create_longhorn_namespace
  install_backupstores
  install_csi_snapshotter

  init_flux

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    create_flux_helm_repo "${HELM_CHART_DEFAULT_URL}"
    create_flux_helm_release "${LONGHORN_STABLE_VERSION}"
    LONGHORN_UPGRADE_TYPE="from_stable"
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-stable"
    if [[ -n "${LONGHORN_TRANSIENT_VERSION}" ]]; then
      FLUX_HELM_CHART_URL="${HELM_CHART_DEFAULT_URL}"
      FLUX_HELM_CHART_VERSION="${LONGHORN_TRANSIENT_VERSION}"
      UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_TRANSIENT_VERSION}"
      run_longhorn_upgrade_test
      LONGHORN_UPGRADE_TYPE="from_transient"
      LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-transient"
    fi
    FLUX_HELM_CHART_URL="${HELM_CHART_URL}"
    FLUX_HELM_CHART_VERSION="${LONGHORN_INSTALL_VERSION}"
    UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    create_flux_helm_repo "${HELM_CHART_URL}"
    create_flux_helm_release "${LONGHORN_INSTALL_VERSION}"
    run_longhorn_test
  fi
}

main
