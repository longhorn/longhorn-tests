#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/create_instance_mapping_configmap.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_helm_chart.sh
source pipelines/utilities/longhorn_ui.sh
if [[ ${TEST_TYPE} == "robot" ]]; then
  source pipelines/utilities/run_longhorn_e2e_test.sh
else
  source pipelines/utilities/run_longhorn_test.sh
fi


LONGHORN_INSTALL_METHOD="helm"


apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}


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

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    get_longhorn_chart "${LONGHORN_STABLE_VERSION}"
    customize_longhorn_chart_registry
    install_longhorn
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    if [[ ${TEST_TYPE} == "pytest" ]]; then
      run_longhorn_upgrade_test
    fi
    run_longhorn_test
  else
    get_longhorn_chart
    customize_longhorn_chart_registry
    customize_longhorn_chart
    install_longhorn
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_test
  fi

}

main
