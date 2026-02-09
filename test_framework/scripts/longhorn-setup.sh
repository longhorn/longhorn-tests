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
  if [[ "${TF_VAR_cis_hardening}" == true ]]; then
    install_backupstores_networkpolicy
  fi
  install_csi_snapshotter
  if [[ "${TF_VAR_enable_mtls}" == true ]]; then
    enable_mtls
  fi

  patch_coredns_ipv6_name_servers
  scale_up_coredns

  if [[ "${DISTRO}" != "talos" ]]; then
    longhornctl_check
  fi

  if [[ "${DISTRO}" == "talos" ]]; then
    install_metrics_server
  fi

  get_longhorn_repo
  generate_longhorn_yaml_manifest
  create_registry_secret
  customize_longhorn_manifest_registry

  if [[ "${DISTRO}" == "talos" ]]; then
    customize_longhorn_default_data_path /var/mnt/longhorn/
  fi

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
