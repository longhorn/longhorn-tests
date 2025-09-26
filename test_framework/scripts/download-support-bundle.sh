#!/usr/bin/env bash

source test_framework/scripts/kubeconfig.sh
source pipelines/utilities/longhorn_ui.sh

SUPPORT_BUNDLE_FILE_NAME=${1:-"lh-support-bundle.zip"}
SUPPORT_BUNDLE_ISSUE_DESC=${3:-"Auto-generated support bundle"}

set_kubeconfig
export_longhorn_ui_url

download_support_bundle(){
  set -e
  # create support bundle
  JSON_PAYLOAD="{\"issueURL\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\", \"description\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\"}"
  CURL_CMD="curl -s -XPOST ${LONGHORN_CLIENT_URL}/v1/supportbundles -H 'Accept: application/json' -H 'Accept-Encoding: gzip, deflate' -d '"${JSON_PAYLOAD}"'"
  echo ${CURL_CMD}
  CREATE_SUPPORT_BUNDLE_RESP=`kubectl exec -n longhorn-system svc/longhorn-frontend -- bash -c "${CURL_CMD}"`
  echo ${CREATE_SUPPORT_BUNDLE_RESP}
  NODE_ID=`echo ${CREATE_SUPPORT_BUNDLE_RESP} | jq -r '.id'`
  NAME=`echo ${CREATE_SUPPORT_BUNDLE_RESP} | jq -r '.name'`

  # wait for support bundle url available
  SUPPORT_BUNDLE_URL_READY=false
  CURL_CMD="curl -s -GET ${LONGHORN_CLIENT_URL}/v1/supportbundles/${NODE_ID}/${NAME} -H 'Accept: application/json' -H 'Accept-Encoding: gzip, deflate'"
  echo ${CURL_CMD}
  MAX_RETRY=100
  RETRY=0
  while [[ ${SUPPORT_BUNDLE_URL_READY} == false ]] && [[ ${RETRY} -lt ${MAX_RETRY} ]]; do
      GET_SUPPORT_BUNDLE_RESP=`kubectl exec -n longhorn-system svc/longhorn-frontend -- bash -c "${CURL_CMD}"`
      echo ${GET_SUPPORT_BUNDLE_RESP}
      SUPPORT_BUNDLE_PROGRESS=`echo ${GET_SUPPORT_BUNDLE_RESP} | jq -r '.progressPercentage'`
      if [[ ${SUPPORT_BUNDLE_PROGRESS} == 100 ]]; then SUPPORT_BUNDLE_URL_READY=true; fi
      RETRY=$((RETRY+1))
      sleep 3s
  done

  # download support bundle
  kubectl exec -n longhorn-system svc/longhorn-frontend -- curl -s -H 'Accept-Encoding: gzip, deflate' "${LONGHORN_CLIENT_URL}/v1/supportbundles/${NODE_ID}/${NAME}/download" > ${SUPPORT_BUNDLE_FILE_NAME}
  set +e
}

MAX_RETRY=3
RETRY=0
while [[ ${RETRY} -lt ${MAX_RETRY} ]]; do
  if download_support_bundle; then
    break
  else
    RETRY=$((RETRY+1))
  fi
done