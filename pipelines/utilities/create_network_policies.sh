#!/bin/bash

set -x

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

source "${SCRIPT_DIR}/longhorn_namespace.sh"


longhorn_internal_networkpolicies_exist(){
  kubectl get networkpolicy longhorn-manager -n "${LONGHORN_NAMESPACE}" >/dev/null 2>&1 &&
    kubectl get networkpolicy instance-manager -n "${LONGHORN_NAMESPACE}" >/dev/null 2>&1
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
