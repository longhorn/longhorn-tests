create_longhorn_namespace(){
  kubectl create ns "${LONGHORN_NAMESPACE}"
  if [[ "${TF_VAR_cis_hardening}" == true ]]; then
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/enforce=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/enforce-version=latest
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/audit=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/audit-version=latest
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/warn=privileged
    kubectl label ns default "${LONGHORN_NAMESPACE}" pod-security.kubernetes.io/warn-version=latest
  fi
}