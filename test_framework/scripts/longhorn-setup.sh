#!/usr/bin/env ash

set  -x

wget https://raw.githubusercontent.com/rancher/longhorn/master/deploy/longhorn.yaml 

LONGHORN_MANAGER_IMAGE_TAG=`grep -i "rancher\/longhorn-manager:.*$" longhorn.yaml | head -1 | awk -F ":" '{print $2}'`
LONGHORN_ENGINE_IMAGE_TAG=`grep -i "rancher\/longhorn-engine:.*$" longhorn.yaml | head -1 | awk -F ":" '{print $2}'


sed -i 's/rancher\/longhorn-manager:'${LONGHORN_MANAGER_IMAGE_TAG}'/rancher\/longhorn-manager:v0.5.0' longhorn.yaml
sed -i 's/rancher\/longhorn-engine:'${LONGHORN_ENGINE_IMAGE_TAG}'/rancher\/longhorn-engine:v0.5.0' longhorn.yaml

export KUBECONFIG="${TF_VAR_tf_workspace}/templates/kube_config_3-nodes-k8s.yml"

kubectl apply -f longhorn.yaml

while [[ -n "`kubectl get pods -n longhorn-system  | grep "longhorn-\(manager\|driver\)\|engine-image-.*" | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn is being inatalled ... rechecking in 1m"
  sleep 1m
done

kubectl create -Rf "${WORKSPACE}/manager/integration/deploy/backupstores"

sedi -i 's/#TEST_FRAMEWORK_ARGS_PLACEHOLDER/args:\ \[\ \"\-s\"\ ,\ \"\-\-junitxml=\$\{LONGHORN_JUNIT_REPORT_PATH\}" \]/' "${WORKSPACE}/manager/integration/deploy/test.yaml"

kubectl create -f "${WORKSPACE}/manager/integration/deploy/test.yaml"

echo "Waiting for test pod to be in Running state"
sleep 5m

while [[ -z "`kubectl get pods longhorn-test --no-headers=true | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn tests still running ... rechecking in 5m"
  sleep 5m
done

kubectl logs longhorn-test  > "${TF_VAR_tf_workspace}/longhorn-test-junit-report.xml"
