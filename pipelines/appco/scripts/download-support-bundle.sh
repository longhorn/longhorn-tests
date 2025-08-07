#!/usr/bin/env bash

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/longhorn_ui.sh

set -e

SUPPORT_BUNDLE_FILE_NAME=${1:-"lh-support-bundle.zip"}
SUPPORT_BUNDLE_ISSUE_URL=${2:-""}
SUPPORT_BUNDLE_ISSUE_DESC=${3:-"Auto-generated support bundle"}

set_kubeconfig
export_longhorn_ui_url

JSON_PAYLOAD="{\"issueURL\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\", \"description\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\"}"

CURL_CMD="curl -s -XPOST ${LONGHORN_CLIENT_URL}/v1/supportbundles -H 'Accept: application/json' -H 'Accept-Encoding: gzip, deflate' -d '${JSON_PAYLOAD}'"

run_curl_in_pod() {
  kubectl run curl-helper -n longhorn-system --rm -i --restart=Never \
    --image=alpine -- sh -c "apk add --no-cache curl jq >/dev/null && $1"
}

SUPPORT_BUNDLE_URL_RAW=$(run_curl_in_pod "${CURL_CMD}" | head -n 1)
SUPPORT_BUNDLE_URL=$(echo "$SUPPORT_BUNDLE_URL_RAW" | jq -r '.links.self + "/" + .name')

SUPPORT_BUNDLE_READY=false
while [[ ${SUPPORT_BUNDLE_READY} == false ]]; do
    PERCENT_RAW=$(run_curl_in_pod "curl -s -H 'Accept: application/json' ${SUPPORT_BUNDLE_URL}")
    PERCENT=$(echo "$PERCENT_RAW" | jq -r '.progressPercentage' || true)
    echo "${PERCENT}"

    if [[ ${PERCENT} == 100 ]]; then SUPPORT_BUNDLE_READY=true; fi
done

run_curl_in_pod "curl -L --compressed -H 'Accept-Encoding: gzip, deflate' ${SUPPORT_BUNDLE_URL}/download" > "${SUPPORT_BUNDLE_FILE_NAME}"
