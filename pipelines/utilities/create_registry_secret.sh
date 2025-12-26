#!/bin/bash

set -x

source pipelines/utilities/longhorn_namespace.sh

create_registry_secret(){
  get_longhorn_namespace
  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  if [[ -z "${REGISTRY_URL}" ]]; then
    # use --dry-run=client -o yaml | kubectl apply -f - to avoid errors when the secret already exists
    kubectl -n default create secret docker-registry docker-registry-secret --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD} --dry-run=client -o yaml | kubectl apply -f -
    kubectl -n "${LONGHORN_NAMESPACE}" create secret docker-registry docker-registry-secret --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD} --dry-run=client -o yaml | kubectl apply -f -
  else
    kubectl -n default create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD} --dry-run=client -o yaml | kubectl apply -f -
    kubectl -n "${LONGHORN_NAMESPACE}" create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD} --dry-run=client -o yaml | kubectl apply -f -
  fi
  set -x
  kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"docker-registry-secret"}]}' -n default
  kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"docker-registry-secret"}]}' -n "${LONGHORN_NAMESPACE}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
