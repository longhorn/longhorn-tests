#!/usr/bin/env bash

set -x

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

LONGHORN_NAMESPACE="longhorn-system"

# Longhorn version tag (e.g v1.1.0), use "master" for latest stable
# we will use this version as the base for upgrade
LONGHORN_STABLE_VERSION=${LONGHORN_STABLE_VERSION:-master}
LONGHORN_STABLE_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_STABLE_VERSION}/deploy/longhorn.yaml"

# for install Longhorn by manifest
LONGHORN_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_INSTALL_VERSION}/deploy/longhorn.yaml"

# for install Longhorn by helm chart
LONGHORN_REPO_URL="https://github.com/longhorn/longhorn"
LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

set_kubeconfig_envvar(){
  ARCH=${1}
  BASEDIR=${2}

  if [[ ${ARCH} == "amd64" ]] ; then
    if [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE] ]]; then
      export KUBECONFIG="${BASEDIR}/kube_config_rke.yml"
    elif [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE]2 ]]; then
      export KUBECONFIG="${BASEDIR}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/rke2.yaml"
    elif [[ ${TF_VAR_k8s_distro_name} == "gke" ]]; then
      gcloud container clusters get-credentials `terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${TF_VAR_k8s_distro_name} output -raw cluster_name` --zone `terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${TF_VAR_k8s_distro_name} output -raw cluster_zone` --project ${TF_VAR_gcp_project}
    elif [[ ${TF_VAR_k8s_distro_name} == "aks" ]]; then
      export KUBECONFIG="${BASEDIR}/aks.yml"
    elif [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
      export KUBECONFIG="${BASEDIR}/eks.yml"
    else
      export KUBECONFIG="${BASEDIR}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
    fi
  elif [[ ${ARCH} == "arm64"  ]]; then
    if [[ ${TF_VAR_k8s_distro_name} == "gke" ]]; then
      gcloud container clusters get-credentials `terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${TF_VAR_k8s_distro_name} output -raw cluster_name` --zone `terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${TF_VAR_k8s_distro_name} output -raw cluster_zone` --project ${TF_VAR_gcp_project}
    elif [[ ${TF_VAR_k8s_distro_name} == "aks" ]]; then
      export KUBECONFIG="${BASEDIR}/aks.yml"
    elif [[ ${TF_VAR_k8s_distro_name} == "eks" ]]; then
      export KUBECONFIG="${BASEDIR}/eks.yml"
    else
      export KUBECONFIG="${BASEDIR}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO}/k3s.yaml"
    fi
  fi
}


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
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].command += "--scale-down-unneeded-time=1m"' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  yq -i 'select(.kind == "Deployment").spec.template.spec.containers[0].command += "--scale-down-delay-after-add=1m"' "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/cluster_autoscaler.yaml"
}


install_csi_snapshotter_crds(){
    CSI_SNAPSHOTTER_REPO_URL="https://github.com/kubernetes-csi/external-snapshotter.git"
    CSI_SNAPSHOTTER_REPO_BRANCH="v5.0.1"
    CSI_SNAPSHOTTER_REPO_DIR="${TMPDIR}/k8s-csi-external-snapshotter"

    git clone --single-branch \
              --branch "${CSI_SNAPSHOTTER_REPO_BRANCH}" \
            "${CSI_SNAPSHOTTER_REPO_URL}" \
            "${CSI_SNAPSHOTTER_REPO_DIR}"

    kubectl apply -f ${CSI_SNAPSHOTTER_REPO_DIR}/client/config/crd \
                  -f ${CSI_SNAPSHOTTER_REPO_DIR}/deploy/kubernetes/snapshot-controller
}


install_rancher() {

  RANCHER_HOSTNAME=`cat "${TF_VAR_tf_workspace}/load_balancer_url"`
  RANCHER_BOOTSTRAP_PASSWORD='p@ssw0rd'

  kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v1.0.4/cert-manager.crds.yaml
  kubectl create namespace cert-manager
  helm repo add jetstack https://charts.jetstack.io
  helm repo update
  helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.4.0
  kubectl get pods --namespace cert-manager

  helm repo add rancher-latest https://releases.rancher.com/server-charts/latest
  kubectl create namespace cattle-system
  helm install rancher rancher-latest/rancher --namespace cattle-system --set bootstrapPassword="${RANCHER_BOOTSTRAP_PASSWORD}" --set hostname="${RANCHER_HOSTNAME}" --set replicas=3 --set ingress.tls.source=letsEncrypt --set letsEncrypt.email=yang.chiu@suse.com
  kubectl -n cattle-system rollout status deploy/rancher
}


get_rancher_api_key() {
  python3 "${TF_VAR_tf_workspace}/scripts/rancher/webdriver/main.py" "${RANCHER_HOSTNAME}" "${RANCHER_BOOTSTRAP_PASSWORD}"
  RANCHER_ACCESS_KEY=`cat "${PWD}/access_key"`
  RANCHER_SECRET_KEY=`cat "${PWD}/secret_key"`
}


install_longhorn_by_rancher() {
  terraform -chdir="${TF_VAR_tf_workspace}/scripts/rancher/terraform" init
  terraform -chdir="${TF_VAR_tf_workspace}/scripts/rancher/terraform" apply \
            -var="api_url=https://${RANCHER_HOSTNAME}" \
            -var="access_key=${RANCHER_ACCESS_KEY}" \
            -var="secret_key=${RANCHER_SECRET_KEY}" \
            -var="rancher_chart_git_repo=${RANCHER_CHART_GIT_REPO}" \
            -var="rancher_chart_git_branch=${RANCHER_CHART_GIT_BRANCH}" \
            -var="rancher_chart_install_version=${RANCHER_CHART_INSTALL_VERSION}" \
            -var="registry_url=${REGISTRY_URL}" \
            -var="registry_user=${REGISTRY_USERNAME}" \
            -var="registry_passwd=${REGISTRY_PASSWORD}" \
            -var="registry_secret=docker-registry-secret" \
            -auto-approve -no-color
}


wait_longhorn_status_running(){
  local RETRY_COUNTS=10 # in minutes
  local RETRY_INTERVAL="1m"

  RETRIES=0
  while [[ -n `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $3}' | grep -v Running` ]]; do
    echo "Longhorn is still installing ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}


get_longhorn_manifest(){
  wget ${LONGHORN_MANIFEST_URL} -P ${TF_VAR_tf_workspace}
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${TF_VAR_tf_workspace}/longhorn.yaml"
}


get_longhorn_chart(){
  git clone --single-branch \
            --branch "${LONGHORN_INSTALL_VERSION}" \
            "${LONGHORN_REPO_URL}" \
            "${LONGHORN_REPO_DIR}"
}


create_registry_secret(){
  kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
}


customize_longhorn_manifest_for_airgap(){
  # (1) add secret name to imagePullSecrets.name
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-driver-deployer").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-ui").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "ConfigMap" and .metadata.name == "longhorn-default-setting").data."default-setting.yaml"="registry-secret: docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  # (2) modify images to point to private registry
  sed -i "s/longhornio\//${REGISTRY_URL}\/longhornio\//g" "${TF_VAR_tf_workspace}/longhorn.yaml"
}


customize_longhorn_chart_for_airgap(){
  # specify private registry secret in chart/values.yaml
  yq -i '.privateRegistry.createSecret=true' "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryUrl=\"${REGISTRY_URL}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryUser=\"${REGISTRY_USERNAME}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryPasswd=\"${REGISTRY_PASSWORD}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i '.privateRegistry.registrySecret="docker-registry-secret"' "${LONGHORN_REPO_DIR}/chart/values.yaml"
}


generate_longhorn_yaml_manifest() {
  MANIFEST_BASEDIR="${1}"

  LONGHORN_REPO_URI=${LONGHORN_REPO_URI:-"https://github.com/longhorn/longhorn.git"}
  LONGHORN_REPO_BRANCH=${LONGHORN_REPO_BRANCH:-"master"}
  LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

  CUSTOM_LONGHORN_MANAGER_IMAGE=${CUSTOM_LONGHORN_MANAGER_IMAGE:-"longhornio/longhorn-manager:master-head"}
  CUSTOM_LONGHORN_ENGINE_IMAGE=${CUSTOM_LONGHORN_ENGINE_IMAGE:-"longhornio/longhorn-engine:master-head"}

  CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE:-""}

  git clone --single-branch \
            --branch ${LONGHORN_REPO_BRANCH} \
            ${LONGHORN_REPO_URI} \
            ${LONGHORN_REPO_DIR}

  cat "${LONGHORN_REPO_DIR}/deploy/longhorn.yaml" > "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # get longhorn default images from yaml manifest
  LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`

  # replace longhorn images with custom images
  sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use instance-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use share-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use backing-image-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi
}


install_longhorn_by_manifest(){
  LONGHORN_MANIFEST_FILE_PATH="${1}"
  kubectl apply -f "${LONGHORN_MANIFEST_FILE_PATH}"
  wait_longhorn_status_running
}


install_longhorn_by_chart(){
  helm install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace longhorn-system
  wait_longhorn_status_running
}


install_longhorn_stable(){
  install_longhorn_by_manifest "${LONGHORN_STABLE_MANIFEST_URL}"
}


create_longhorn_namespace(){
  kubectl create ns ${LONGHORN_NAMESPACE}
}


install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
               -f ${NFS_BACKUPSTORE_URL}
}


create_aws_secret(){
  AWS_ACCESS_KEY_ID_BASE64=`echo -n "${TF_VAR_lh_aws_access_key}" | base64`
  AWS_SECRET_ACCESS_KEY_BASE64=`echo -n "${TF_VAR_lh_aws_secret_key}" | base64`
  AWS_DEFAULT_REGION_BASE64=`echo -n "${TF_VAR_aws_region}" | base64`

  yq e -i '.data.AWS_ACCESS_KEY_ID |= "'${AWS_ACCESS_KEY_ID_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_SECRET_ACCESS_KEY |= "'${AWS_SECRET_ACCESS_KEY_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_DEFAULT_REGION |= "'${AWS_DEFAULT_REGION_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"

  kubectl apply -f "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml" -n kube-system
}


run_longhorn_upgrade_test(){
  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"
  LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='''"-s",
                                 "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'",
                                 "--include-upgrade-test",
                                 "-k", "test_upgrade",
                                 "--upgrade-lh-repo-url", "'${UPGRADE_LH_REPO_URL}'",
                                 "--upgrade-lh-repo-branch", "'${UPGRADE_LH_REPO_BRANCH}'",
                                 "--upgrade-lh-manager-image", "'${UPGRADE_LH_MANAGER_IMAGE}'",
                                 "--upgrade-lh-engine-image", "'${UPGRADE_LH_ENGINE_IMAGE}'",
                                 "--upgrade-lh-instance-manager-image", "'${UPGRADE_LH_INSTANCE_MANAGER_IMAGE}'",
                                 "--upgrade-lh-share-manager-image", "'${UPGRADE_LH_SHARE_MANAGER_IMAGE}'",
                                 "--upgrade-lh-backing-image-manager-image", "'${UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE}'"
                              '''

  ## generate upgrade_test pod manifest
  yq e 'select(.spec.containers[0] != null).spec.containers[0].args=['"${PYTEST_COMMAND_ARGS}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}" > ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).metadata.name="'${LONGHORN_UPGRADE_TEST_POD_NAME}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  if [[ $BACKUP_STORE_TYPE = "s3" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $1}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $2}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  fi

  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[4].value="'${LONGHORN_UPGRADE_TYPE}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  kubectl apply -f ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  # wait upgrade test pod to start running
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting upgrade test pod to be in running state ... rechecking in 10s"
    sleep 10s
  done

    # wait upgrade test to complete
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep \"running\"`"  ]]; do
    kubectl logs ${LONGHORN_UPGRADE_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  # get upgrade test junit xml report
  kubectl cp ${LONGHORN_UPGRADE_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${TF_VAR_tf_workspace}/${LONGHORN_UPGRADE_TEST_POD_NAME}-junit-report.xml" -c longhorn-test-report
}


run_longhorn_tests(){

  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='"-s", "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'"'
  if [[ -n ${PYTEST_CUSTOM_OPTIONS} ]]; then
    PYTEST_CUSTOM_OPTIONS=(${PYTEST_CUSTOM_OPTIONS})
    for OPT in "${PYTEST_CUSTOM_OPTIONS[@]}"; do
      PYTEST_COMMAND_ARGS=${PYTEST_COMMAND_ARGS}', "'${OPT}'"'
    done
  fi

  ## generate test pod manifest
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].args=['"${PYTEST_COMMAND_ARGS}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  if [[ $BACKUP_STORE_TYPE = "s3" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $1}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $2}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_use_hdd}" == true ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[3].value="hdd"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_k8s_distro_name}" == "eks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "gke" ]] || [[ "${TF_VAR_k8s_distro_name}" == "aks" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="true"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  set +x
  ## inject aws cloudprovider and credentials env variables from created secret
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "CLOUDPROVIDER", "value": "aws"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_ACCESS_KEY_ID", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_ACCESS_KEY_ID"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_SECRET_ACCESS_KEY"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_DEFAULT_REGION", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_DEFAULT_REGION"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  set -x

  LONGHORN_TEST_POD_NAME=`yq e 'select(.spec.containers[0] != null).metadata.name' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}`

  kubectl apply -f ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  local RETRY_COUNTS=60
  local RETRIES=0
  # wait longhorn tests pod to start running
  while [[ -n "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting longhorn test pod to be in running state ... rechecking in 10s"
    sleep 10s
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn test pod start timeout"; exit 1 ; fi
  done

  # wait longhorn tests to complete
  while [[ "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' 2>&1 | grep -v \"terminated\"`"  ]]; do
    kubectl logs ${LONGHORN_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  kubectl cp ${LONGHORN_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${TF_VAR_tf_workspace}/longhorn-test-junit-report.xml" -c longhorn-test-report
}


main(){
  set_kubeconfig_envvar ${TF_VAR_arch} ${TF_VAR_tf_workspace}

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
  create_longhorn_namespace
  if [[ ${PYTEST_CUSTOM_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
  fi
  install_csi_snapshotter_crds

  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    if [[ "${LONGHORN_INSTALL_METHOD}" == "manifest-file" ]]; then
      create_registry_secret
      get_longhorn_manifest
      customize_longhorn_manifest_for_airgap
      install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
    elif [[ "${LONGHORN_INSTALL_METHOD}" == "helm-chart" ]]; then
      get_longhorn_chart
      customize_longhorn_chart_for_airgap
      install_longhorn_by_chart
    elif [[ "${LONGHORN_INSTALL_METHOD}" == "rancher" ]]; then
      install_rancher
      get_rancher_api_key
      install_longhorn_by_rancher
    fi
    run_longhorn_tests
  elif [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
    install_longhorn_stable
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
    run_longhorn_tests
  else
    generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
    install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
    run_longhorn_tests
  fi
}

main
