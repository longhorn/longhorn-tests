source pipelines/utilities/longhorn_status.sh


install_fleet(){
  helm repo add fleet https://rancher.github.io/fleet-helm-charts/
  helm -n cattle-fleet-system install --create-namespace --wait fleet-crd fleet/fleet-crd
  helm -n cattle-fleet-system install --create-namespace --wait fleet fleet/fleet
}


create_fleet_git_repo(){
  REVISION="${1:-${FLEET_REPO_VERSION}}"
  cat > longhorn-gitrepo.yaml <<EOF
apiVersion: fleet.cattle.io/v1alpha1
kind: GitRepo
metadata:
  name: longhorn
  # This namespace is special and auto-wired to deploy to the local cluster
  namespace: fleet-local
spec:
  # Everything from this repo will be run in this cluster. You trust me right?
  repo: ${FLEET_REPO_URI}
  revision: ${REVISION}
  paths:
  - .
EOF
  kubectl apply -f longhorn-gitrepo.yaml
  wait_for_bundle_deployment_applied
  wait_for_bundle_deployment_ready
  wait_longhorn_status_running
}


wait_for_bundle_deployment_applied(){
  local RETRY_COUNTS=60 # in seconds
  local RETRY_INTERVAL="1s"

  RETRIES=0
  while [[ $(kubectl -n fleet-local get gitrepo longhorn -o jsonpath='{.status.summary.waitApplied}') != 1 ]]; do
    echo "Wait for fleet bundle deployment applied ... re-checking in 1s"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: apply fleet bundle deployment timeout"; exit 1 ; fi
  done
}


wait_for_bundle_deployment_ready(){
  local RETRY_COUNTS=10 # in minutes
  local RETRY_INTERVAL="1m"

  RETRIES=0
  while [[ $(kubectl -n fleet-local get gitrepo longhorn -o jsonpath='{.status.readyClusters}') != 1 ]]; do
    echo "Wait for fleet bundle deployment ready ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: fleet bundle deployment timeout"; exit 1 ; fi
  done
}
