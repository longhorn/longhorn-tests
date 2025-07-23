run_longhorn_test(){

  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="manager/integration/deploy/test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='"-s", "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'"'
  if [[ -n ${CUSTOM_TEST_OPTIONS} ]]; then
    CUSTOM_TEST_OPTIONS=(${CUSTOM_TEST_OPTIONS})
    for OPT in "${CUSTOM_TEST_OPTIONS[@]}"; do
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
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $3}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $4}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_use_hdd}" == true ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[3].value="hdd"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_k8s_distro_name}" == "eks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "aks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "gke" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="true"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  RESOURCE_SUFFIX=$(terraform -chdir=test_framework/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw resource_suffix)
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[7].value="'${RESOURCE_SUFFIX}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  ## inject cloudprovider
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "CLOUDPROVIDER", "value": "'${LONGHORN_TEST_CLOUDPROVIDER}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  ## for v2 volume test
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "RUN_V2_TEST", "value": "'${RUN_V2_TEST}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  set +x
  if [[ "${TF_VAR_k8s_distro_name}" != "gke" ]] && [[ "${TF_VAR_k8s_distro_name}" != "aks" ]]; then
    ## inject aws credentials env variables from created secret
    yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_ACCESS_KEY_ID", "valueFrom": {"secretKeyRef": {"name": "host-provider-cred-secret", "key": "AWS_ACCESS_KEY_ID"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "host-provider-cred-secret", "key": "AWS_SECRET_ACCESS_KEY"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_DEFAULT_REGION", "valueFrom": {"secretKeyRef": {"name": "host-provider-cred-secret", "key": "AWS_DEFAULT_REGION"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  fi
  set -x

  LONGHORN_TEST_POD_NAME=`yq e 'select(.spec.containers[0] != null).metadata.name' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}`

  yq e -i 'select(.kind == "Pod" and .metadata.name == "longhorn-test").spec.imagePullSecrets[0].name="docker-registry-secret"' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

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

  if [[ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]]; then
    unset_kubectl_retry
  fi

  # wait longhorn tests to complete
  while [[ "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' 2>&1 | grep -v \"terminated\"`"  ]]; do
    kubectl logs ${LONGHORN_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  kubectl cp ${LONGHORN_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "longhorn-test-junit-report.xml" -c longhorn-test-report
}


run_longhorn_upgrade_test(){
  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"
  LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='''"-s",
                                 "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'",
                                 "--include-upgrade-test",
                                 "-k", "test_upgrade"
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
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $3}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $4}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  fi

  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[4].value="'${LONGHORN_UPGRADE_TYPE}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  if [[ "${TF_VAR_k8s_distro_name}" == "eks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "aks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "gke" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="true"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  fi

  ## inject cloudprovider
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "CLOUDPROVIDER", "value": "'${LONGHORN_TEST_CLOUDPROVIDER}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  ## for v2 volume test
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "RUN_V2_TEST", "value": "'${RUN_V2_TEST}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"

  ## for appco test
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "APPCO_TEST", "value": "'${APPCO_TEST}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"

  # environment variables for upgrade test
  # install method can be manifest, helm, rancher, flux, fleet and argocd
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_METHOD", "value": "'${LONGHORN_INSTALL_METHOD}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  # the stable version of Longhorn that to be installed first
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_STABLE_VERSION", "value": "'${LONGHORN_STABLE_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  # (if provided) the transient version of Longhorn that to be install in a 2-stage upgrade test
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_TRANSIENT_VERSION", "value": "'${LONGHORN_TRANSIENT_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"

  # upgrade test parameters
  if [[ "${LONGHORN_INSTALL_METHOD}" == "manifest" ]] || [[ "${LONGHORN_INSTALL_METHOD}" == "helm" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO_URI", "value": "'${LONGHORN_REPO_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO_BRANCH", "value": "'${LONGHORN_REPO_BRANCH}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE", "value": "'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    if [[ $APPCO_TEST = "true" ]]; then
      # Injecting SUSE CA cert and run pdate-ca-certificates"
      if [[ "${LONGHORN_TEST_CLOUDPROVIDER}" == "harvester" ]]; then
        yq e -i 'select(.kind == "Pod").spec.containers[0].volumeMounts += {"name": "ca-cert-volume", "mountPath": "/etc/pki/trust/anchors", "readOnly": true}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
        yq e -i 'select(.kind == "Pod").spec.volumes += {"name": "ca-cert-volume", "hostPath": {"path": "/etc/pki/trust/anchors", "type": "DirectoryOrCreate"}}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
        yq e -i '( . | select(.kind=="Pod") | .spec.containers[0].lifecycle ).postStart = {"exec":{"command":["sh","-c","update-ca-certificates"]}}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      fi
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "REGISTRY_URL", "value": "'${REGISTRY_URL}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "AIR_GAP_INSTALLATION", "value": "'${AIR_GAP_INSTALLATION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_UI_IMAGE", "value": "'${CUSTOM_LONGHORN_UI_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE", "value": "'${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_RESIZER_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE", "value": "'${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_MANAGER_IMAGE", "value": "'${TRANSIENT_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_ENGINE_IMAGE", "value": "'${TRANSIENT_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_INSTANCE_MANAGER_IMAGE", "value": "'${TRANSIENT_INSTANCE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_SHARE_MANAGER_IMAGE", "value": "'${TRANSIENT_SHARE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE", "value": "'${TRANSIENT_BACKING_IMAGE_MANAGER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_UI_IMAGE", "value": "'${TRANSIENT_UI_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_SUPPORT_BUNDLE_IMAGE", "value": "'${TRANSIENT_SUPPORT_BUNDLE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_ATTACHER_IMAGE", "value": "'${TRANSIENT_CSI_ATTACHER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_PROVISIONER_IMAGE", "value": "'${TRANSIENT_CSI_PROVISIONER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_NODE_REGISTRAR_IMAGE", "value": "'${TRANSIENT_CSI_NODE_REGISTRAR_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_RESIZER_IMAGE", "value": "'${TRANSIENT_CSI_RESIZER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_SNAPSHOTTER_IMAGE", "value": "'${TRANSIENT_CSI_SNAPSHOTTER_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "TRANSIENT_CSI_LIVENESSPROBE_IMAGE", "value": "'${TRANSIENT_CSI_LIVENESSPROBE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_TRANSIENT_VERSION_CHART_URI", "value": "'${LONGHORN_TRANSIENT_VERSION_CHART_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_STABLE_VERSION_CHART_URI", "value": "'${LONGHORN_STABLE_VERSION_CHART_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_CHART_URI", "value": "'${LONGHORN_CHART_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "APPCO_LONGHORN_COMPOMENT_REGISTRY", "value": "'${APPCO_LONGHORN_COMPOMENT_REGISTRY}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_VERSION", "value": "'${LONGHORN_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
      yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_NAMESPACE", "value": "'${LONGHORN_NAMESPACE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    fi
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "rancher" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_HOSTNAME", "value": "'${RANCHER_HOSTNAME}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_ACCESS_KEY", "value": "'${RANCHER_ACCESS_KEY}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_SECRET_KEY", "value": "'${RANCHER_SECRET_KEY}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_CHART_REPO_URI", "value": "'${RANCHER_CHART_REPO_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "RANCHER_CHART_REPO_BRANCH", "value": "'${RANCHER_CHART_REPO_BRANCH}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    # e.g., 104.2.0+up1.7.1
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    # rancher or longhorn. use rancher/mirrored-longhornio- or longhornio/ images
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_REPO", "value": "'${LONGHORN_REPO}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    # basically upgrading Longhorn rancher chart is done by upgrading it to LONGHORN_INSTALL_VERSION (e.g. 104.2.0+up1.7.1) without custom image version
    # but CUSTOM_LONGHORN_ENGINE_IMAGE is still needed to test engine image upgrading during the test
    # extract 1.4.2 from 102.2.1+up1.4.2
    RAW_VERSION=(${LONGHORN_INSTALL_VERSION/up/ })
    if [[ "${LONGHORN_REPO}" == "rancher" ]]; then
      CUSTOM_LONGHORN_ENGINE_IMAGE="rancher/mirrored-longhornio-longhorn-engine:v${RAW_VERSION[1]}"
    else
      CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:v${RAW_VERSION[1]}"
    fi
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "flux" ]]; then
    # flux installs Longhorn by a "released" helm chart that can be found by command like helm search repo longhorn --versions
    # so the HELM_CHART_URL is not the Longhorn repo https://github.com/longhorn/longhorn.git
    # it should be https://charts.longhorn.io/ or your custom helm chart url
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "HELM_CHART_URL", "value": "'${HELM_CHART_URL}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "argocd" ]]; then
    # just like flux, agrocd installs Longhorn by a "released" helm chart
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "HELM_CHART_URL", "value": "'${HELM_CHART_URL}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  elif [[ "${LONGHORN_INSTALL_METHOD}" == "fleet" ]]; then
    # fleet uses a github repo contains "fleet.yaml" to install applications
    # see https://fleet.rancher.io/ref-fleet-yaml for more details
    # the fleet.yaml file defines what application you'd like to install and
    # how you'd like to configure this application
    # so it's an custom custom, not https://github.com/longhorn/longhorn.git or https://charts.longhorn.io/
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "FLEET_REPO_URI", "value": "'${FLEET_REPO_URI}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "LONGHORN_INSTALL_VERSION", "value": "'${LONGHORN_INSTALL_VERSION}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
    CUSTOM_LONGHORN_ENGINE_IMAGE="longhornio/longhorn-engine:${LONGHORN_INSTALL_VERSION}"
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env += {"name": "CUSTOM_LONGHORN_ENGINE_IMAGE", "value": "'${CUSTOM_LONGHORN_ENGINE_IMAGE}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  fi

  yq e -i 'select(.kind == "Pod" and .metadata.name == "longhorn-test").spec.imagePullSecrets[0].name="docker-registry-secret"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  kubectl apply -f ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  # wait upgrade test pod to start running
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting upgrade test pod to be in running state ... rechecking in 10s"
    sleep 10s
  done

  if [[ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]]; then
    unset_kubectl_retry
  fi

  # wait upgrade test to complete
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep \"running\"`"  ]]; do
    kubectl logs ${LONGHORN_UPGRADE_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  # get upgrade test junit xml report
  kubectl cp ${LONGHORN_UPGRADE_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${LONGHORN_UPGRADE_TEST_POD_NAME}-junit-report.xml" -c longhorn-test-report
}