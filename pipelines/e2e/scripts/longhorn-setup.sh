#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/kubectl_retry.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/storage_network.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_harvester_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/create_instance_mapping_configmap.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/install_metrics_server.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/run_longhorn_e2e_test.sh
source pipelines/utilities/coredns.sh
source pipelines/utilities/longhornctl.sh

LONGHORN_INSTALL_METHOD="manifest"

main(){
  set_kubeconfig

  if [[ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]]; then
    apply_kubectl_retry
  fi

  create_longhorn_namespace

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi

  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  create_harvester_secret
  set -x
  create_instance_mapping_configmap

  install_backupstores
  setup_azurite_backup_store
  install_csi_snapshotter
  create_nad_without_storage_network

  patch_coredns_ipv6_name_servers
  scale_up_coredns

  # msg="failed to get package manager" error="operating systems amzn are not supported"
  if [[ "${TF_VAR_k8s_distro_name}" != "eks" ]] && \
    [[ "${DISTRO}" != "talos" ]]; then
    longhornctl_check
  fi

  if [[ "${DISTRO}" == "talos" ]]; then
    install_metrics_server
  fi

  get_longhorn_repo
  generate_longhorn_yaml_manifest
  create_registry_secret
  customize_longhorn_manifest_registry
  install_longhorn

  setup_longhorn_ui_nodeport
  export_longhorn_ui_url

  if [[ "${OUT_OF_CLUSTER}" == true ]]; then
    run_longhorn_test_out_of_cluster
  else
    run_longhorn_test
  fi
}

main
