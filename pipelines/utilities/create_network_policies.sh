#!/bin/bash

set -x

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

source "${SCRIPT_DIR}/longhorn_namespace.sh"


longhorn_internal_networkpolicies_exist(){
  echo "Checking if Longhorn internal NetworkPolicies exist in namespace ${LONGHORN_NAMESPACE}..."

  local found_manager=false
  local found_instance=false

  if kubectl get networkpolicy longhorn-manager -n "${LONGHORN_NAMESPACE}" --request-timeout=300s >/dev/null 2>&1; then
    found_manager=true
    echo "DEBUG: NetworkPolicy 'longhorn-manager' found in ${LONGHORN_NAMESPACE}"
  else
    echo "DEBUG: NetworkPolicy 'longhorn-manager' NOT found in ${LONGHORN_NAMESPACE} (or API server unreachable)"
  fi

  if kubectl get networkpolicy instance-manager -n "${LONGHORN_NAMESPACE}" --request-timeout=300s >/dev/null 2>&1; then
    found_instance=true
    echo "DEBUG: NetworkPolicy 'instance-manager' found in ${LONGHORN_NAMESPACE}"
  else
    echo "DEBUG: NetworkPolicy 'instance-manager' NOT found in ${LONGHORN_NAMESPACE} (or API server unreachable)"
  fi

  if [[ "${found_manager}" == true && "${found_instance}" == true ]]; then
    echo "DEBUG: Both internal NetworkPolicies exist — will apply test NetworkPolicies"
    return 0
  else
    echo "DEBUG: One or both internal NetworkPolicies missing — will skip test NetworkPolicies"
    return 1
  fi
}

apply_longhorn_test_networkpolicy(){
  if ! command -v yq > /dev/null 2>&1; then
    echo "yq is required to install Longhorn test NetworkPolicies"
    exit 1
  fi

  LONGHORN_NAMESPACE="${LONGHORN_NAMESPACE}" yq e '.metadata.namespace = strenv(LONGHORN_NAMESPACE)' - <<'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-longhorn-test-to-manager
  namespace: longhorn-system
spec:
  podSelector:
    matchLabels:
      app: longhorn-manager
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: default
      podSelector:
        matchLabels:
          longhorn-test: test-job
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-longhorn-test-to-instance-manager
  namespace: longhorn-system
spec:
  podSelector:
    matchLabels:
      longhorn.io/component: instance-manager
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: default
      podSelector:
        matchLabels:
          longhorn-test: test-job
EOF
}

delete_longhorn_manager_networkpolicy(){
  kubectl delete networkpolicy allow-longhorn-test-to-manager allow-longhorn-test-to-instance-manager -n "${LONGHORN_NAMESPACE}" --ignore-not-found=true
}

setup_longhorn_manager_networkpolicy(){
  get_longhorn_namespace

  if longhorn_internal_networkpolicies_exist; then
    apply_longhorn_test_networkpolicy
  else
    delete_longhorn_manager_networkpolicy
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
