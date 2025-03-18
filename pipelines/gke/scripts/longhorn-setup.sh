#!/usr/bin/env bash

set -x

source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/run_longhorn_test.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

export LONGHORN_NAMESPACE="longhorn-system"
export LONGHORN_REPO_DIR="${TMPDIR}/longhorn"
export LONGHORN_INSTALL_METHOD="manifest"

set_kubeconfig_envvar(){
    gcloud container clusters get-credentials `terraform -chdir=${PWD}/pipelines/gke/terraform output -raw cluster_name` --zone `terraform -chdir=${PWD}/pipelines/gke/terraform output -raw cluster_zone` --project ${TF_VAR_gcp_project}
}

print_out_cluster_info(){
  gcloud container clusters describe `terraform -chdir=${PWD}/pipelines/gke/terraform output -raw cluster_name` --zone `terraform -chdir=${PWD}/pipelines/gke/terraform output -raw cluster_zone` --format="value(currentNodeVersion)"
  kubectl create -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: print-os-release
spec:
  containers:
  - name: print-os-release
    image: alpine
    args: ["/bin/sh", "-c", "while true;do date;sleep 5; done"]
    volumeMounts:
    - name: host
      mountPath: /mnt/host
  volumes:
  - name: host
    hostPath:
      path: /
      type: Directory
EOF
  kubectl wait --for=condition=Ready pod/print-os-release --timeout=60s
  kubectl exec -it print-os-release -- cat /mnt/host/etc/os-release
  kubectl delete pod/print-os-release
}

main(){
  set_kubeconfig_envvar
  print_out_cluster_info

  create_longhorn_namespace

  if [[ "${TF_VAR_distro}" == "COS_CONTAINERD" ]]; then
    kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-gke-cos-node-agent.yaml
  fi

  if [[ ${PYTEST_CUSTOM_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
    setup_azurite_backup_store
  fi
  install_csi_snapshotter

  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_registry_secret
  set -x

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    generate_longhorn_yaml_manifest
    customize_longhorn_chart_registry
    install_longhorn_stable
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    UPGRADE_LH_TRANSIENT_VERSION="${LONGHORN_TRANSIENT_VERSION}"
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
    generate_longhorn_yaml_manifest
    customize_longhorn_chart_registry
    install_longhorn_by_manifest
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_test
  fi
}

main
