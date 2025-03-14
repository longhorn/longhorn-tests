create_registry_secret(){
  if [[ -z "${REGISTRY_URL}" ]]; then
    kubectl -n default create secret docker-registry docker-registry-secret --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
    kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry docker-registry-secret --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
  else
    kubectl -n default create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
    kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
  fi
  kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"docker-registry-secret"}]}' -n default
  kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"docker-registry-secret"}]}' -n longhorn-system
}
