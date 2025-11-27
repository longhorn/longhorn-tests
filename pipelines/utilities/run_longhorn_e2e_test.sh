S3_BACKUP_STORE='s3://backupbucket@us-east-1/backupstore$minio-secret'
NFS_BACKUP_STORE='nfs://longhorn-test-nfs-svc.default:/opt/backupstore'
CIFS_BACKUP_STORE='cifs://longhorn-test-cifs-svc.default/backupstore$cifs-secret'
AZURITE_BACKUP_STORE='azblob://longhorn-test-azurite@core.windows.net/$azblob-secret'

run_longhorn_test(){

  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-e2e-test:master-head"}
  LONGHORN_INSTALL_METHOD=${LONGHORN_INSTALL_METHOD:-"manifest"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="e2e/deploy/test.yaml"

  if [[ "${CUSTOM_TEST_OPTIONS}" == \"*\" ]]; then
    # Remove leading and trailing double quotes
    CUSTOM_TEST_OPTIONS="${CUSTOM_TEST_OPTIONS#\"}"
    CUSTOM_TEST_OPTIONS="${CUSTOM_TEST_OPTIONS%\"}"
  fi

  eval "ROBOT_COMMAND_ARGS=($CUSTOM_TEST_OPTIONS)"
  for OPT in "${ROBOT_COMMAND_ARGS[@]}"; do
    ROBOT_COMMAND_ARR="${ROBOT_COMMAND_ARR}\"${OPT}\", "
  done
  ROBOT_COMMAND_ARR=$(echo ${ROBOT_COMMAND_ARR} | sed 's/,$//g')

  ## generate test pod manifest
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].args=['"${ROBOT_COMMAND_ARR}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  if [[ $BACKUP_STORE_TYPE = "s3" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${S3_BACKUP_STORE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${NFS_BACKUP_STORE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${CIFS_BACKUP_STORE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${AZURITE_BACKUP_STORE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_use_hdd}" == true ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[3].value="hdd"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_k8s_distro_name}" == "eks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "aks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "gke" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[5].value="true"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="'${LONGHORN_TEST_CLOUDPROVIDER}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[7].value="'${TF_VAR_arch}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  # environment variables for upgrade test
  # install method can be manifest, helm, rancher, flux, fleet and argocd
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_METHOD", "value": "'${LONGHORN_INSTALL_METHOD}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  # the stable version of Longhorn that to be installed first
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_STABLE_VERSION", "value": "'${LONGHORN_STABLE_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  # (if provided) the transient version of Longhorn that to be install in a 2-stage upgrade test
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_TRANSIENT_VERSION", "value": "'${LONGHORN_TRANSIENT_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  # registry secret might need to be recreated during uninstallation related test cases
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "REGISTRY_URL", "value": "'${REGISTRY_URL}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "REGISTRY_USERNAME", "value": "'${REGISTRY_USERNAME}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "REGISTRY_PASSWORD", "value": "'${REGISTRY_PASSWORD}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  # add k8s distro for kubelet restart
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "K8S_DISTRO", "value": "'${TF_VAR_k8s_distro_name}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  # upgrade test parameters
  if [[ "${LONGHORN_INSTALL_METHOD}" == "manifest" ]] || [[ "${LONGHORN_INSTALL_METHOD}" == "helm" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO_URI", "value": "'${LONGHORN_REPO_URI}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO_BRANCH", "value": "'${LONGHORN_REPO_BRANCH}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_MANAGER_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "rancher" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_HOSTNAME", "value": "'${RANCHER_HOSTNAME}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_ACCESS_KEY", "value": "'${RANCHER_ACCESS_KEY}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_SECRET_KEY", "value": "'${RANCHER_SECRET_KEY}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_CHART_REPO_URI", "value": "'${RANCHER_CHART_REPO_URI}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_CHART_REPO_BRANCH", "value": "'${RANCHER_CHART_REPO_BRANCH}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    # e.g., 104.2.0+up1.7.1
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    # rancher or longhorn. use rancher/mirrored-longhornio- or longhornio/ images
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO", "value": "'${LONGHORN_REPO}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    # basically upgrading Longhorn rancher chart is done by upgrading it to LONGHORN_INSTALL_VERSION (e.g. 104.2.0+up1.7.1) without custom image version
    # but CUSTOM_LONGHORN_ENGINE_IMAGE is still needed to test engine image upgrading during the test
    # extract 1.4.2 from 102.2.1+up1.4.2
    RAW_VERSION=(${LONGHORN_INSTALL_VERSION/up/ })
    if [[ "${LONGHORN_REPO}" == "rancher" && "${RANCHER_PRIME}" == "true" ]]; then
      CUSTOM_LONGHORN_ENGINE_IMAGE="registry.rancher.com/rancher/mirrored-longhornio-longhorn-engine:v${RAW_VERSION[1]}"
    elif [[ "${LONGHORN_REPO}" == "rancher" ]]; then
      CUSTOM_LONGHORN_ENGINE_IMAGE="rancher/mirrored-longhornio-longhorn-engine:v${RAW_VERSION[1]}"
    else
      CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:v${RAW_VERSION[1]}"
    fi
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "flux" ]]; then
    # flux installs Longhorn by a "released" helm chart that can be found by command like helm search repo longhorn --versions
    # so the HELM_CHART_URL is not the Longhorn repo https://github.com/longhorn/longhorn.git
    # it should be https://charts.longhorn.io/ or your custom helm chart url
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "HELM_CHART_URL", "value": "'${HELM_CHART_URL}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "argocd" ]]; then
    # just like flux, agrocd installs Longhorn by a "released" helm chart
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "HELM_CHART_URL", "value": "'${HELM_CHART_URL}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "fleet" ]]; then
    # fleet uses a github repo contains "fleet.yaml" to install applications
    # see https://fleet.rancher.io/ref-fleet-yaml for more details
    # the fleet.yaml file defines what application you'd like to install and
    # how you'd like to configure this application
    # so it's an custom custom, not https://github.com/longhorn/longhorn.git or https://charts.longhorn.io/
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "FLEET_REPO_URI", "value": "'${FLEET_REPO_URI}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  fi

  LONGHORN_TEST_POD_NAME=`yq e 'select(.spec.containers[0] != null).metadata.name' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}`

  yq e -i 'select(.kind == "Pod" and .metadata.name == "longhorn-test").spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  kubectl apply -f ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  local RETRY_COUNTS=60
  local RETRIES=0
  # wait longhorn tests pod to start running
  while [[ -n "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' 2>/dev/null`" ]] &&
    [[ -n "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`" ]]; do
    echo "waiting longhorn test pod to be in running state ... rechecking in 10s"
    sleep 10s
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn test pod start timeout"; exit 1 ; fi
  done

  if [[ "${LONGHORN_INSTALL_METHOD}" == "rancher" ]]; then
    # share terraform state between jenkins job container and test pod
    kubectl cp /src/longhorn-tests/pipelines/utilities/rancher longhorn-test:/e2e/pipelines/utilities/
  fi

  if [[ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]]; then
    unset_kubectl_retry
  fi

  # wait longhorn tests to complete
  while [[ "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' 2>&1 | grep -v \"terminated\"`"  ]]; do
    kubectl logs ${LONGHORN_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  kubectl cp ${LONGHORN_TEST_POD_NAME}:/tmp/test-report/log.html "log.html" -c longhorn-test-report
  kubectl cp ${LONGHORN_TEST_POD_NAME}:/tmp/test-report/output.xml "output.xml" -c longhorn-test-report
  kubectl cp ${LONGHORN_TEST_POD_NAME}:/tmp/test-report/junit.xml "junit.xml" -c longhorn-test-report
  kubectl cp ${LONGHORN_TEST_POD_NAME}:/tmp/test-report/report.html "report.html" -c longhorn-test-report
}

run_longhorn_test_out_of_cluster(){

  if [[ ${BACKUP_STORE_TYPE} == "s3" ]]; then
    LONGHORN_BACKUPSTORES=${S3_BACKUP_STORE}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    LONGHORN_BACKUPSTORES=${NFS_BACKUP_STORE}
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    LONGHORN_BACKUPSTORES=${CIFS_BACKUP_STORE}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    LONGHORN_BACKUPSTORES=${AZURITE_BACKUP_STORE}
  fi
  LONGHORN_BACKUPSTORE_POLL_INTERVAL="30"

  if [[ "${CUSTOM_TEST_OPTIONS}" == \"*\" ]]; then
    # Remove leading and trailing double quotes
    CUSTOM_TEST_OPTIONS="${CUSTOM_TEST_OPTIONS#\"}"
    CUSTOM_TEST_OPTIONS="${CUSTOM_TEST_OPTIONS%\"}"
  fi

  eval "ROBOT_COMMAND_ARGS=($CUSTOM_TEST_OPTIONS)"

  cat /tmp/instance_mapping
  cp "${KUBECONFIG}" /tmp/kubeconfig
  CONTAINER_NAME="e2e-container-${IMAGE_NAME}"
  docker run --pull=always \
             --network=container:"${IMAGE_NAME}" \
             --name "${CONTAINER_NAME}" \
             -e LONGHORN_BACKUPSTORE="${LONGHORN_BACKUPSTORES}" \
             -e LONGHORN_BACKUPSTORE_POLL_INTERVAL="${LONGHORN_BACKUPSTORE_POLL_INTERVAL}" \
             -e AWS_ACCESS_KEY_ID="${TF_VAR_lh_aws_access_key}" \
             -e AWS_SECRET_ACCESS_KEY="${TF_VAR_lh_aws_secret_key}" \
             -e AWS_DEFAULT_REGION="${TF_VAR_aws_region}" \
             -e LONGHORN_CLIENT_URL="${LONGHORN_CLIENT_URL}" \
             -e KUBECONFIG="/tmp/kubeconfig" \
             -e HOST_PROVIDER="${LONGHORN_TEST_CLOUDPROVIDER}" \
             -e ARCH="${TF_VAR_arch}" \
             -e LAB_URL="${TF_VAR_lab_url}" \
             -e LAB_ACCESS_KEY="${TF_VAR_lab_access_key}" \
             -e LAB_SECRET_KEY="${TF_VAR_lab_secret_key}" \
             -e LAB_CLUSTER_ID="$(cat /tmp/cluster_id)" \
             -e LONGHORN_REPO_URI="${LONGHORN_REPO_URI}"\
             -e LONGHORN_REPO_BRANCH="${LONGHORN_REPO_BRANCH}"\
             -e CUSTOM_LONGHORN_MANAGER_IMAGE="${CUSTOM_LONGHORN_MANAGER_IMAGE}"\
             -e CUSTOM_LONGHORN_ENGINE_IMAGE="${CUSTOM_LONGHORN_ENGINE_IMAGE}"\
             -e CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE="${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"\
             -e CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE="${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"\
             -e CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE="${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"\
             -e LONGHORN_INSTALL_METHOD="${LONGHORN_INSTALL_METHOD}"\
             -e LONGHORN_STABLE_VERSION="${LONGHORN_STABLE_VERSION}"\
             -e LONGHORN_TRANSIENT_VERSION="${LONGHORN_TRANSIENT_VERSION}"\
             -e K8S_DISTRO="${TF_VAR_k8s_distro_name}"\
             --mount source="vol-${IMAGE_NAME}",target=/tmp \
             "${LONGHORN_TESTS_CUSTOM_IMAGE}" "${ROBOT_COMMAND_ARGS[@]}"
  docker stop "${CONTAINER_NAME}"
  docker rm "${CONTAINER_NAME}"

  cp /tmp/test-report/log.html "${WORKSPACE}/log.html"
  cp /tmp/test-report/output.xml "${WORKSPACE}/output.xml"
  cp /tmp/test-report/junit.xml "${WORKSPACE}/junit.xml"
  cp /tmp/test-report/report.html "${WORKSPACE}/report.html"
}
