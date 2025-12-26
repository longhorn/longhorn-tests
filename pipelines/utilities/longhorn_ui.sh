#!/bin/bash

set -x

source pipelines/utilities/longhorn_namespace.sh

setup_longhorn_ui_nodeport(){
  get_longhorn_namespace
  kubectl get service longhorn-ui-nodeport -n "${LONGHORN_NAMESPACE}" > /dev/null 2>&1
  if [[ $? -eq 0 ]]; then
    echo "NodePort longhorn-ui-nodeport already exists. Skipping creation."
  else
    kubectl expose --type=NodePort deployment longhorn-ui -n "${LONGHORN_NAMESPACE}" --port 8000 --name longhorn-ui-nodeport --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":8000,"protocol":"TCP","targetPort":8000,"nodePort":30000}]}}'
  fi
}

export_longhorn_ui_url(){
  export LONGHORN_CLIENT_URL="http://$(cat /tmp/controlplane_public_ip):30000"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
