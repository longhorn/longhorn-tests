#!/bin/bash

set -x

create_longhorn_namespace(){
  LONGHORN_NAMESPACE="longhorn-system"
  kubectl create ns "${LONGHORN_NAMESPACE}"
  if [[ "${TF_VAR_cis_hardening}" == true ]] || [[ "${DISTRO}" == "talos" ]]; then
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/enforce=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/enforce-version=latest
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/audit=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/audit-version=latest
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/warn=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/warn-version=latest
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
