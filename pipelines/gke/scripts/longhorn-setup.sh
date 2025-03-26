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

  if [[ ${CUSTOM_TEST_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
    setup_azurite_backup_store
  fi
  install_csi_snapshotter

  get_longhorn_repo
  generate_longhorn_yaml_manifest
  create_registry_secret
  customize_longhorn_manifest_registry

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    run_longhorn_upgrade_test
    run_longhorn_test
  else
    install_longhorn
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_test
  fi
}

main
