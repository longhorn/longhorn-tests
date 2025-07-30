#!/usr/bin/env bash

set -x

export LONGHORN_REPO_BRANCH="${LONGHORN_VERSION}"

source pipelines/utilities/kubectl_retry.sh
source pipelines/utilities/run_longhorn_test.sh
source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/coredns.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/longhornctl.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/install_csi_snapshotter.sh
if [[ "${LONGHORN_INSTALL_METHOD}" == "manifest" ]]; then
  source pipelines/appco/scripts/longhorn_manifest.sh
elif [[ "${LONGHORN_INSTALL_METHOD}" == "helm" ]]; then
  source pipelines/appco/scripts/longhorn_helm_chart.sh
fi

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

LONGHORN_NAMESPACE="longhorn-system"


apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/v${LONGHORN_REPO_BRANCH#v}/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}


enable_mtls(){
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/longhorn-grpc-tls.yml" -n ${LONGHORN_NAMESPACE}
}


wait_longhorn_status_running(){
  local RETRY_COUNTS=10 # in minutes
  local RETRY_INTERVAL="1m"

  # csi and engine image components are installed after longhorn components.
  # it's possible that all longhorn components are running but csi components aren't created yet.
  RETRIES=0
  while [[ -z `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $1}' | grep csi-` ]] || \
    [[ -z `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $1}' | grep engine-image-` ]] || \
    [[ -n `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $3}' | grep -v Running` ]]; do
    echo "Longhorn is still installing ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}


install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/nfs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
               -f ${NFS_BACKUPSTORE_URL}
}

create_appco_secret(){
  kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry application-collection --docker-server=dp.apps.rancher.io --docker-username="${APPCO_USERNAME}" --docker-password="${APPCO_PASSWORD}"
}

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
  set -x

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

  create_registry_secret

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
    run_longhorn_test
  fi
}

main
