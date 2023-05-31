#!/usr/bin/env bash

set -e

SUPPORT_BUNDLE_FILE_NAME=${1:-"lh-support-bundle.zip"}
SUPPORT_BUNDLE_ISSUE_URL=${2:-""}
SUPPORT_BUNDLE_ISSUE_DESC=${3:-"Auto-generated support buundle"}

set_kubeconfig_envvar(){
    gcloud container clusters get-credentials `terraform -chdir=${TF_VAR_tf_workspace}/terraform output -raw cluster_name` --zone `terraform -chdir=${TF_VAR_tf_workspace}/terraform output -raw cluster_zone` --project ${TF_VAR_gcp_project}
}

set_kubeconfig_envvar

LH_FRONTEND_ADDR=`kubectl get svc -n longhorn-system longhorn-frontend -o json | jq -r '.spec.clusterIP + ":" + (.spec.ports[0].port|tostring)'`

JSON_PAYLOAD="{\"issueURL\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\", \"description\": \"${SUPPORT_BUNDLE_ISSUE_DESC}\"}"

CURL_CMD="curl -XPOST http://${LH_FRONTEND_ADDR}/v1/supportbundles -H 'Accept: application/json' -H 'Accept-Encoding: gzip, deflate' -d '"${JSON_PAYLOAD}"'"

SUPPORT_BUNDLE_URL=`kubectl exec -n longhorn-system svc/longhorn-frontend -- bash -c "${CURL_CMD}"  | jq -r '.links.self + "/" + .name'`

SUPPORT_BUNDLE_READY=false
while [[ ${SUPPORT_BUNDLE_READY} == false ]]; do
    PERCENT=`kubectl exec -n longhorn-system svc/longhorn-frontend -- curl -H 'Accept: application/json' ${SUPPORT_BUNDLE_URL} | jq -r '.progressPercentage' || true`
    echo ${PERCENT}
    
    if [[ ${PERCENT} == 100 ]]; then SUPPORT_BUNDLE_READY=true; fi
done

kubectl exec -n longhorn-system svc/longhorn-frontend -- curl -H 'Accept-Encoding: gzip, deflate' ${SUPPORT_BUNDLE_URL}/download > ${SUPPORT_BUNDLE_FILE_NAME}
