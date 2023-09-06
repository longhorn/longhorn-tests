wait_longhorn_status_running(){
  local RETRY_COUNTS=10 # in minutes
  local RETRY_INTERVAL="1m"

  # csi components are installed after longhorn components.
  # it's possible that all longhorn components are running but csi components aren't created yet.
  RETRIES=0
  while [[ -z `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $1}' | grep csi-` ]] || \
    [[ -n `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $3}' | grep -v "Running\|Completed"` ]]; do
    echo "Longhorn is still installing ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}