#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/install_litmus.sh
source pipelines/utilities/run_longhorn_e2e_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_INSTALL_METHOD="manifest"

create_instance_mapping_configmap(){
  kubectl create configmap instance-mapping --from-file=/tmp/instance_mapping
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
  create_cloud_secret
  set -x
  create_instance_mapping_configmap

  create_longhorn_namespace
  install_backupstores
  install_csi_snapshotter

  install_litmus
  install_experiments

  generate_longhorn_yaml_manifest
  install_longhorn_by_manifest

  setup_longhorn_ui_nodeport
  export_longhorn_ui_url

  if [[ -n "${LONGHORN_TESTS_CUSTOM_IMAGE}" ]]; then
    run_longhorn_e2e_test
  else
    run_longhorn_e2e_test_out_of_cluster
  fi
}

main
