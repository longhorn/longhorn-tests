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

<<<<<<< HEAD

install_csi_snapshotter_crds(){
    CSI_SNAPSHOTTER_REPO_URL="https://github.com/kubernetes-csi/external-snapshotter.git"
    CSI_SNAPSHOTTER_REPO_BRANCH="v6.2.1"
    CSI_SNAPSHOTTER_REPO_DIR="${TMPDIR}/k8s-csi-external-snapshotter"

    git clone --single-branch \
              --branch "${CSI_SNAPSHOTTER_REPO_BRANCH}" \
            "${CSI_SNAPSHOTTER_REPO_URL}" \
            "${CSI_SNAPSHOTTER_REPO_DIR}"

    kubectl apply -f ${CSI_SNAPSHOTTER_REPO_DIR}/client/config/crd \
                  -f ${CSI_SNAPSHOTTER_REPO_DIR}/deploy/kubernetes/snapshot-controller
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


install_longhorn_stable(){
  install_longhorn_by_manifest "${LONGHORN_STABLE_MANIFEST_URL}"
}


create_longhorn_namespace(){
  kubectl create ns ${LONGHORN_NAMESPACE}
}


install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/nfs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
               -f ${NFS_BACKUPSTORE_URL}
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

  # set MANAGED_K8S_CLUSTER to true
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="true"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  ## inject cloudprovider
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "CLOUDPROVIDER", "value": "gke"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

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


=======
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

>>>>>>> a7efe95 (ci: provide docker credentials when pulling Longhorn components images)
main(){
  set_kubeconfig_envvar

  create_longhorn_namespace

  if [[ "${TF_VAR_distro}" == "COS_CONTAINERD" ]]; then
    kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-gke-cos-node-agent.yaml
  fi

  if [[ ${PYTEST_CUSTOM_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
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
