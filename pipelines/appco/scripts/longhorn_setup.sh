#!/usr/bin/env bash

set -x

export LONGHORN_REPO_BRANCH="${LONGHORN_VERSION}"

source pipelines/utilities/kubectl_retry.sh
if [[ ${TEST_TYPE} == "robot" ]]; then
  source pipelines/utilities/run_longhorn_e2e_test.sh
else
  source pipelines/utilities/run_longhorn_test.sh
fi
source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/selinux_workaround.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/coredns.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/longhornctl.sh
source pipelines/utilities/longhorn_status.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_instance_mapping_configmap.sh
source pipelines/utilities/create_harvester_secret.sh
source pipelines/utilities/create_appco_secret.sh
source pipelines/appco/scripts/longhorn_helm_chart.sh


# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

LONGHORN_NAMESPACE="longhorn-system"


main(){
  set_kubeconfig

  if [[ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]]; then
    apply_kubectl_retry
  fi

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi
  
  create_longhorn_namespace
  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  create_appco_secret
  create_harvester_secret
  create_registry_secret
  set -x
  create_instance_mapping_configmap

  if [[ ${CUSTOM_TEST_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
  fi
  install_csi_snapshotter
  if [[ "${TF_VAR_enable_mtls}" == true ]]; then
    enable_mtls
  fi

  scale_up_coredns

  # msg="failed to get package manager" error="operating systems (amzn, sl-micro) are not supported"
  if [[ "${TF_VAR_k8s_distro_name}" != "eks" ]] && \
    [[ "${DISTRO}" != "sle-micro" ]]; then
    longhornctl_check
  fi

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    install_longhorn_custom
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    if [[ "${TEST_TYPE}" == "robot" ]]; then
      if [[ "${OUT_OF_CLUSTER}" == true ]]; then
        run_longhorn_test_out_of_cluster
      else
        run_longhorn_test
      fi
    fi
    run_longhorn_test
  fi
}

main
