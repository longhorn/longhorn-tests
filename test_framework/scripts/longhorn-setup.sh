#!/usr/bin/env ash

set  -x

LONGHORN_MANAGER_IMAGE_VERSION="v0.5.0"
LONGHORN_ENGINE_IMAGE_VERSION="v0.5.0"

sed -i 's/LONGHORN_MANAGER_TAG/'${LONGHORN_MANAGER_IMAGE_VERSION}'/' "${TF_VAR_tf_workspace}/templates/longhorn.yaml"

sed -i 's/LONGHORN_ENGINE_TAG/'${LONGHORN_ENGINE_IMAGE_VERSION}'/'   "${TF_VAR_tf_workspace}/templates/longhorn.yaml"

export KUBECONFIG="${TF_VAR_tf_workspace}/templates/kube_config_3-nodes-k8s.yml"

kubectl apply -f "${TF_VAR_tf_workspace}/templates/longhorn.yaml"

while [[ -n "`kubectl get pods -n longhorn-system  | grep "longhorn-\(manager\|driver\)\|engine-image-.*" | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn is installing ... rechecking in 1m"
  sleep 1m
done

kubectl create -Rf manager/integration/deploy/backupstores

kubectl create -f manager/integration/deploy/test.yaml

echo "Waiting for test pod to be in Running state"
sleep 5m

while [[ -z "`kubectl get pods longhorn-test --no-headers=true | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn tests still running ... rechecking in 5m"
  sleep 5m
done

kubectl logs longhorn-test  > "${TF_VAR_tf_workspace}/longhorn-test-junit-report.xml"
