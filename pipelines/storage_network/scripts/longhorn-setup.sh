#!/usr/bin/env bash

set -x

source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/storage_network.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/run_longhorn_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_INSTALL_METHOD="manifest"

set_kubeconfig_envvar(){
    export KUBECONFIG="${PWD}/pipelines/storage_network/terraform/k3s.yaml"
}

main(){
  set_kubeconfig_envvar

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi

  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  set -x

  if [[ "${TF_VAR_thick_plugin}" == true ]]; then
    deploy_multus_thick_plugin_daemonset
  else
    deploy_multus_thin_plugin_daemonset
  fi
  deploy_network_attachment_definition

  create_longhorn_namespace
  install_backupstores
  install_csi_snapshotter

  generate_longhorn_yaml_manifest
  install_longhorn_by_manifest

  update_storage_network_setting

  run_longhorn_test
}

main
