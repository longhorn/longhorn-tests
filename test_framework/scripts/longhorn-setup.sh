#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/kubectl_retry.sh
source pipelines/utilities/install_csi_snapshotter.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/install_backupstores.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/coredns.sh
source pipelines/utilities/install_metrics_server.sh
source pipelines/utilities/run_longhorn_test.sh
source pipelines/utilities/longhornctl.sh


LONGHORN_INSTALL_METHOD="manifest"


create_admin_service_account(){
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/kubeconfig_service_account.yaml"
  TOKEN=$(kubectl -n kube-system get secret/kubeconfig-cluster-admin-token -o=go-template='{{.data.token}}' | base64 -d)
  yq -i ".users[0].user.token=\"${TOKEN}\""  "${TF_VAR_tf_workspace}/eks.yml"
}


install_iscsi(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-iscsi-installation.yaml"
}


install_cluster_autoscaler(){
  curl -o "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml" "https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml"
  CLUSTER_NAME=$(kubectl config current-context)
  sed -i "s/<YOUR CLUSTER NAME>/${CLUSTER_NAME}/g" "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].env += [{"name": "AWS_ACCESS_KEY_ID", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_ACCESS_KEY_ID"}}}]' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].env += [{"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_SECRET_ACCESS_KEY"}}}]' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].env += [{"name": "AWS_REGION", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_DEFAULT_REGION"}}}]' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].command += "--scale-down-unneeded-time=3m"' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].command += "--scale-down-delay-after-add=1m"' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
}


enable_mtls(){
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/longhorn-grpc-tls.yml" -n ${LONGHORN_NAMESPACE} 
}


install_backupstores_from_lh_repo(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/nfs-backupstore.yaml"
  CIFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/cifs-backupstore.yaml"
  AZURITE_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/azurite-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
                 -f ${NFS_BACKUPSTORE_URL} \
                 -f ${CIFS_BACKUPSTORE_URL} \
                 -f ${AZURITE_BACKUPSTORE_URL}
}


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
  set -x

  if [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
    create_admin_service_account
    install_iscsi
    install_cluster_autoscaler
  fi
  if [[ ${CUSTOM_TEST_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
      if [[ "${TF_VAR_k8s_distro_name}" == "eks" || "${TF_VAR_k8s_distro_name}" == "aks" ]]; then
          install_backupstores_from_lh_repo
      else
          install_backupstores
      fi
      setup_azurite_backup_store
  fi
  install_csi_snapshotter
  if [[ "${TF_VAR_enable_mtls}" == true ]]; then
    enable_mtls
  fi

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

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
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
