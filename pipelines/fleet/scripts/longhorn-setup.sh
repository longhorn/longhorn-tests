#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/fleet.sh
source pipelines/utilities/run_longhorn_test.sh


LONGHORN_INSTALL_METHOD="fleet"


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
  setup_azurite_backup_store
  install_csi_snapshotter

  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_registry_secret
  set -x

  install_fleet

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    install_longhorn_custom
    run_longhorn_test
  fi
}

main
