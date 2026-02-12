#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/create_instance_mapping_configmap.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_rancher_chart.sh
source pipelines/utilities/longhorn_ui.sh
if [[ ${TEST_TYPE} == "robot" ]]; then
  source pipelines/utilities/run_longhorn_e2e_test.sh
else
  source pipelines/utilities/run_longhorn_test.sh
fi

LONGHORN_INSTALL_METHOD="rancher"

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
  if [[ "${TF_VAR_cis_hardening}" == true ]]; then
    install_backupstores_networkpolicy
  fi
  setup_azurite_backup_store
  install_csi_snapshotter

  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_registry_secret
  set -x
  create_instance_mapping_configmap

  install_rancher
  get_rancher_api_key

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    if [[ ${TEST_TYPE} == "pytest" ]]; then
      run_longhorn_upgrade_test
    fi
    run_longhorn_test
  else
    install_longhorn_custom
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_test
  fi
}

main
