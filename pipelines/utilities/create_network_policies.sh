#!/bin/bash

set -x

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

source "${SCRIPT_DIR}/longhorn_namespace.sh"

install_longhorn_manager_networkpolicy(){
  get_longhorn_namespace

  if ! command -v yq > /dev/null 2>&1; then
    echo "yq is required to install Longhorn test NetworkPolicies"
    exit 1
  fi

  local policy_path="${SCRIPT_DIR}/../../manager/integration/deploy/network-policies/longhorn-manager-networkpolicy.yaml"
  if [[ ! -f "${policy_path}" ]]; then
    policy_path="${SCRIPT_DIR}/../../../manager/integration/deploy/network-policies/longhorn-manager-networkpolicy.yaml"
  fi

  if [[ ! -f "${policy_path}" ]]; then
    echo "Longhorn manager test NetworkPolicy manifest not found"
    exit 1
  fi

  LONGHORN_NAMESPACE="${LONGHORN_NAMESPACE}" yq e '.metadata.namespace = strenv(LONGHORN_NAMESPACE)' "${policy_path}" | kubectl apply -f -
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
