#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/fleet.sh
source pipelines/utilities/run_longhorn_test.sh


export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_INSTALL_METHOD="fleet"


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

  install_fleet

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    create_fleet_git_repo "${FLEET_REPO_STABLE_VERSION}"
    LONGHORN_UPGRADE_TYPE="from_stable"
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-stable"
    if [[ -n "${FLEET_REPO_TRANSIENT_VERSION}" ]]; then
      UPGRADE_LH_REPO_URL="${FLEET_REPO_URI}"
      UPGRADE_LH_REPO_BRANCH="${FLEET_REPO_TRANSIENT_VERSION}"
      UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:${FLEET_REPO_TRANSIENT_VERSION}"
      run_longhorn_upgrade_test
      LONGHORN_UPGRADE_TYPE="from_transient"
      LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-transient"
    fi
    UPGRADE_LH_REPO_URL="${FLEET_REPO_URI}"
    UPGRADE_LH_REPO_BRANCH="${FLEET_REPO_VERSION}"
    UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:${FLEET_REPO_VERSION}"
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    create_fleet_git_repo
    run_longhorn_test
  fi
}

main
