#!/usr/bin/env ash

set  -x

RETRY_COUNTS=10

LONGHORN_MANAGER_REPO_URI="https://github.com/longhorn/longhorn-manager.git"
LONGHORN_MANAGER_BRANCH="master"
LONGHORN_MANAGER_TMPDIR="/tmp/longhorn-manager"
LONGHORN_STABLE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml"


check_longhorn_status() {
  export KUBECONFIG="${TF_VAR_tf_workspace}/templates/kube_config_3-nodes-k8s.yml"

  RETRIES=0
  while [[ -n "`kubectl get pods -n longhorn-system  | grep "instance-manager-.*\|longhorn-\(manager\|driver\|csi\)\|engine-image-.*" | awk '{print $3}' | grep -v Running`"  ]]; do
    echo "Longhorn is being installed ... rechecking in 1m"
    sleep 1m
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}

mkdir -p ${LONGHORN_MANAGER_TMPDIR}

git clone --single-branch --branch ${LONGHORN_MANAGER_BRANCH} ${LONGHORN_MANAGER_REPO_URI} ${LONGHORN_MANAGER_TMPDIR}

for FILE in `find "${LONGHORN_MANAGER_TMPDIR}/deploy/install" -type f -name "*\.yaml" | sort`; do 
  cat ${FILE} >> longhorn.yaml
  echo "---"  >> longhorn.yaml
done


LONGHORN_MANAGER_IMAGE_TAG=`grep -io "longhornio\/longhorn-manager:.*$" longhorn.yaml | head -1 | awk -F ":" '{print $2}'`
LONGHORN_ENGINE_IMAGE_TAG=`grep -io "longhornio\/longhorn-engine:.*$" longhorn.yaml | head -1 | awk -F ":" '{print $2}'`


sed -i 's/longhornio\/longhorn-manager:'${LONGHORN_MANAGER_IMAGE_TAG}'/longhornio\/longhorn-manager:master/' longhorn.yaml
sed -i 's/longhornio\/longhorn-engine:'${LONGHORN_ENGINE_IMAGE_TAG}'/longhornio\/longhorn-engine:master/' longhorn.yaml


export KUBECONFIG="${TF_VAR_tf_workspace}/templates/kube_config_3-nodes-k8s.yml"

# scale coredns min pods to 3 for node offline tests
kubectl get configmaps -n kube-system coredns-autoscaler -o yaml | sed  's/\"min\":1/\"min\":3/' | kubectl apply -n kube-system -f -


if [[ ${LONGHORN_UPGRADE_TEST} ]]; then
  ## install Longhorn stable version, before running test_upgrade.
  kubectl apply -f "${LONGHORN_STABLE_URL}"

  check_longhorn_status

  kubectl create -Rf "${WORKSPACE}/manager/integration/deploy/backupstores"

  ## generate upgrade_test pod manifest
  sed 's/#TEST_FRAMEWORK_ARGS_PLACEHOLDER/args:\ \[\ \"\-s\"\ ,\ \"\-\-junitxml=\$\{LONGHORN_JUNIT_REPORT_PATH\}",\ \"\-\-include\-upgrade\-test\ \-k test_upgrade\" \]/; s/name: longhorn-test$/name: longhorn-test-upgrade/' "${WORKSPACE}/manager/integration/deploy/test.yaml" >> "${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  sed  -i 's/longhornio\/longhorn-manager-test:.*$/longhornio\/longhorn-manager-test:master/' "${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  ## run upgrade test
  kubectl apply -f "${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  echo "Wait for upgrade test pod to be in Running state"
  sleep 2m

  while [[ -z "`kubectl get pods longhorn-test-upgrade --no-headers=true | awk '{print $3}' | grep -v Running`"  ]]; do
    echo "upgrade test still running ... rechecking in 1m"
    sleep 1m
  done

  ## get upgrade test junit report
  kubectl logs longhorn-test-upgrade  >> "${TF_VAR_tf_workspace}/longhorn-test-upgrade-junit-report.xml"

else
  ## install longhorn latest
  kubectl apply -f longhorn.yaml
  check_longhorn_status
  kubectl create -Rf "${WORKSPACE}/manager/integration/deploy/backupstores"
fi


# generate test pod manifest
sed -i 's/#TEST_FRAMEWORK_ARGS_PLACEHOLDER/args:\ \[\ \"\-s\"\ ,\ \"\-\-junitxml=\$\{LONGHORN_JUNIT_REPORT_PATH\}" \]/' "${WORKSPACE}/manager/integration/deploy/test.yaml"

sed  -i 's/longhornio\/longhorn-manager-test:.*$/longhornio\/longhorn-manager-test:master/' "${WORKSPACE}/manager/integration/deploy/test.yaml"

# run manager integration tests
kubectl apply -f "${WORKSPACE}/manager/integration/deploy/test.yaml"

echo "Waiting for test pod to be in Running state"
sleep 5m

while [[ -z "`kubectl get pods longhorn-test --no-headers=true | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn tests still running ... rechecking in 5m"
  sleep 5m
done

# get integration test junit report
kubectl logs longhorn-test  >> "${TF_VAR_tf_workspace}/longhorn-test-junit-report.xml"
