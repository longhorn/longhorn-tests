#!/usr/bin/env bash

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/longhorn_ui.sh

set -e

SUPPORT_BUNDLE_FILE_NAME=${1:-"lh-support-bundle.zip"}
SUPPORT_BUNDLE_ISSUE_URL=${2:-""}
SUPPORT_BUNDLE_ISSUE_DESC=${3:-"Auto-generated support bundle"}

NAMESPACE="longhorn-system"
POD_NAME="curl-helper"

set_kubeconfig
export_longhorn_ui_url

JSON_PAYLOAD="{\"issueURL\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\", \"description\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\"}"

CURL_CMD="curl -s -XPOST ${LONGHORN_CLIENT_URL}/v1/supportbundles -H 'Accept: application/json' -H 'Accept-Encoding: gzip, deflate' -d '${JSON_PAYLOAD}'"

run_curl_in_pod() {
  local IMAGE="alpine:3.21"
  local CMD="$1"

  if ! kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    kubectl run "${POD_NAME}" -n "${NAMESPACE}" --image="${IMAGE}" --restart=Never --command -- sleep 3600 >/dev/null
    kubectl wait --for=condition=Ready pod/"${POD_NAME}" -n "${NAMESPACE}" --timeout=30s >/dev/null
  fi
  OUTPUT=$(kubectl exec -n "${NAMESPACE}" "${POD_NAME}" -- sh -c "apk add --no-cache curl jq >/dev/null && ${CMD}")
  echo "${OUTPUT}"
}

SUPPORT_BUNDLE_URL_RAW=$(run_curl_in_pod "${CURL_CMD}")
SUPPORT_BUNDLE_URL=$(echo "$SUPPORT_BUNDLE_URL_RAW" | jq -r '.links.self + "/" + .name')

SUPPORT_BUNDLE_READY=false
MAX_RETRY=100
RETRY=0
while [[ ${SUPPORT_BUNDLE_READY} == false ]] && [[ ${RETRY} -lt ${MAX_RETRY} ]]; do
    PERCENT_RAW=$(run_curl_in_pod "curl -s -H 'Accept: application/json' ${SUPPORT_BUNDLE_URL}")
    PERCENT=$(echo "$PERCENT_RAW" | jq -r '.progressPercentage' || true)
    echo "${PERCENT}"

    if [[ ${PERCENT} == 100 ]]; then SUPPORT_BUNDLE_READY=true; fi

    RETRY=$((RETRY+1))
    sleep 3s
done

run_curl_in_pod "curl -sSLf ${SUPPORT_BUNDLE_URL}/download -o /tmp/support-bundle.zip"
kubectl cp longhorn-system/curl-helper:/tmp/support-bundle.zip "${SUPPORT_BUNDLE_FILE_NAME}"
kubectl delete pod "${POD_NAME}" -n "${NAMESPACE}" --wait >/dev/null 2>&1
