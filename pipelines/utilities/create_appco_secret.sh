#!/bin/bash

create_appco_secret(){
  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  kubectl -n longhorn-system create secret docker-registry application-collection --docker-server=dp.apps.rancher.io --docker-username="${APPCO_USERNAME}" --docker-password="${APPCO_PASSWORD}"
  set -x
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
