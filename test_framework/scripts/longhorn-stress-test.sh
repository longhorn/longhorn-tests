#!/usr/bin/env ash

set  -x

echo "Running stress test ..."

cp "${WORKSPACE}/manager/integration/deploy/test.yaml.orig" "${WORKSPACE}/manager/integration/deploy/test_stress.yaml"

sed -i 's/#TEST_FRAMEWORK_ARGS_PLACEHOLDER/args:\ \[\ test_stress \]/' "${WORKSPACE}/manager/integration/deploy/test_stress.yaml"

sed  -i 's/longhornio\/longhorn-manager-test:.*$/longhornio\/longhorn-manager-test:staging/' "${WORKSPACE}/manager/integration/deploy/test_stress.yaml"

kubectl create -f "${WORKSPACE}/manager/integration/deploy/test_stress.yaml"

echo "Waiting for test pod to be in Running state"
sleep 5m

while [[ -z "`kubectl get pods longhorn-test --no-headers=true | awk '{print $3}' | grep -v Running`"  ]]; do
  echo "Longhorn tests still running ... rechecking in 5m"
  sleep 5m
done

kubectl logs longhorn-test
