#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_rancher_chart.sh
source pipelines/utilities/run_longhorn_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_INSTALL_METHOD="rancher"


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

  install_rancher
  get_rancher_api_key


  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_rancher_chart "${LONGHORN_STABLE_VERSION}"
    LONGHORN_UPGRADE_TYPE="from_stable"
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-stable"
    if [[ -n "${LONGHORN_TRANSIENT_VERSION}" ]]; then
      RANCHER_CHART_INSTALL_VERSION="${LONGHORN_TRANSIENT_VERSION}"
      # extract 1.4.2 from 102.2.1+up1.4.2
      RAW_VERSION=(${LONGHORN_TRANSIENT_VERSION/up/ })
      if [[ "${LONGHORN_REPO}" == "rancher" ]]; then
        UPGRADE_LH_ENGINE_IMAGE="rancher/mirrored-longhornio-longhorn-engine:v${RAW_VERSION[1]}"
      else
        UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:v${RAW_VERSION[1]}"
      fi
      run_longhorn_upgrade_test
      LONGHORN_UPGRADE_TYPE="from_transient"
      LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-transient"
    fi
    RANCHER_CHART_INSTALL_VERSION="${LONGHORN_INSTALL_VERSION}"
    RAW_VERSION=(${LONGHORN_INSTALL_VERSION/up/ })
    if [[ "${LONGHORN_REPO}" == "rancher" ]]; then
        UPGRADE_LH_ENGINE_IMAGE="rancher/mirrored-longhornio-longhorn-engine:v${RAW_VERSION[1]}"
      else
        UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:v${RAW_VERSION[1]}"
      fi
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    install_longhorn_rancher_chart
    run_longhorn_test
  fi
}

main
