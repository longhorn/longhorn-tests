#!/usr/bin/env bash

set -x

run_uninstall_longhorn_test(){

  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:"${LONGHORN_REPO_BRANCH}}
  
  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"
  LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/uninstall_test.yaml"
  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`  
  
  LONGHORN_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_INSTALL_VERSION}/deploy/longhorn.yaml"
  LONGHORN_UNINSTALL_MANIFEST_FILE_PATH="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_INSTALL_VERSION}/uninstall/uninstall.yaml"

  local PYTEST_COMMAND_ARGS='''"-s",
                                 "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'",
                                 "--include-uninstall-test",
                                 "-k", "test_uninstall",
                                 "--uninstall-lh-manifest-url", "'${LONGHORN_UNINSTALL_MANIFEST_FILE_PATH}'",
                                 "--deploy-lh-manifest-url", "'${LONGHORN_MANIFEST_URL}'"
                              '''

  ## generate uninstall_test pod manifest
  yq e 'select(.spec.containers[0] != null).spec.containers[0].args=['"${PYTEST_COMMAND_ARGS}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}" > ${LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).metadata.name="'${LONGHORN_UNINSTALL_TEST_POD_NAME}'"' ${LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "LONGHORN_REPO_BRANCH", "value": "'${LONGHORN_REPO_BRANCH}'"}' "${LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH}"
  
  kubectl apply -f ${LONGHORN_UNINSTALL_TESTS_MANIFEST_FILE_PATH}

  # wait uninstall test pod to start running
  while [[ -n "`kubectl get pod ${LONGHORN_UNINSTALL_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting uninstall test pod to be in running state ... rechecking in 10s"
    sleep 10s
  done

  # wait uninstall test to complete
  while [[ -n "`kubectl get pod ${LONGHORN_UNINSTALL_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep \"running\"`"  ]]; do
    kubectl logs ${LONGHORN_UNINSTALL_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  # get uninstall test junit xml report
  kubectl cp ${LONGHORN_UNINSTALL_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${TF_VAR_tf_workspace}/${LONGHORN_UNINSTALL_TEST_POD_NAME}-junit-report.xml" -c longhorn-test-report
}

set_kubeconfig_envvar(){
  ARCH=${1}
  BASEDIR=${2}

    if [[ ${ARCH} == "amd64" ]] ; then
    if [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE] ]]; then
      export KUBECONFIG="${BASEDIR}/kube_config_rke.yml"
    elif [[ ${TF_VAR_k8s_distro_name} == [rR][kK][eE]2 ]]; then
      export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/rke2.yaml"
    else
      export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/k3s.yaml"
    fi
  elif [[ ${ARCH} == "arm64"  ]]; then
    export KUBECONFIG="${BASEDIR}/terraform/aws/${DISTRO}/k3s.yaml"
  fi
}

main(){
  set_kubeconfig_envvar ${TF_VAR_arch} ${TF_VAR_tf_workspace}
  LONGHORN_UNINSTALL_TEST_POD_NAME="longhorn-test-uninstall"
  run_uninstall_longhorn_test

}

main
