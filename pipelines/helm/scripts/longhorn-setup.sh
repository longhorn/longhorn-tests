#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_helm_chart.sh
source pipelines/utilities/run_longhorn_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_REPO_DIR="${TMPDIR}/longhorn"
export LONGHORN_INSTALL_METHOD="helm"


apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}


create_registry_secret(){
  kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
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
  install_csi_snapshotter

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    get_longhorn_chart "${LONGHORN_STABLE_VERSION}"
    install_longhorn
    LONGHORN_UPGRADE_TYPE="from_stable"
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-stable"
    if [[ -n "${LONGHORN_TRANSIENT_VERSION}" ]]; then
      UPGRADE_LH_REPO_URL="${LONGHORN_REPO_URI}"
      UPGRADE_LH_REPO_BRANCH="${LONGHORN_TRANSIENT_VERSION}"
      UPGRADE_LH_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_TRANSIENT_VERSION}"
      run_longhorn_upgrade_test
      LONGHORN_UPGRADE_TYPE="from_transient"
      LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade-from-transient"
    fi
    UPGRADE_LH_REPO_URL="${LONGHORN_REPO_URI}"
    UPGRADE_LH_REPO_BRANCH="${LONGHORN_REPO_BRANCH}"
    UPGRADE_LH_MANAGER_IMAGE="${CUSTOM_LONGHORN_MANAGER_IMAGE}"
    UPGRADE_LH_ENGINE_IMAGE="${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    UPGRADE_LH_INSTANCE_MANAGER_IMAGE="${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    UPGRADE_LH_SHARE_MANAGER_IMAGE="${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
    UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE="${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    get_longhorn_chart
    install_longhorn
    run_longhorn_test
  fi

}

main
