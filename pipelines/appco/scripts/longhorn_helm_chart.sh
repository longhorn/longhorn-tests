#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh
HELM_INSTALL_RETRY_LIMIT=10

helm_login_appco(){
  helm registry login dp.apps.rancher.io \
    --username "${APPCO_USERNAME}" \
    --password "${APPCO_PASSWORD}"
}

install_longhorn_custom(){
  if [[ "${LONGHORN_CHART_URI}" == "longhorn/longhorn" ]]; then
    helm repo add longhorn https://charts.longhorn.io
    helm repo update
    helm upgrade --install longhorn longhorn/longhorn \
      --namespace "${LONGHORN_NAMESPACE}" \
      --version "${LONGHORN_VERSION}"
  else
    # set debugging mode off to avoid leaking appco secrets to the logs.
    # DON'T REMOVE!
    set +x
    helm_login_appco
    set -x

    for ((i=1; i<=HELM_INSTALL_RETRY_LIMIT; i++)); do
      if [[ -z "${APPCO_LONGHORN_COMPOMENT_REGISTRY}" ]]; then
        helm upgrade --install longhorn "${LONGHORN_CHART_URI}" \
          --version "${LONGHORN_VERSION}" \
          --namespace "${LONGHORN_NAMESPACE}" \
          --set global.imagePullSecrets="{application-collection}"
      else
        helm upgrade --install longhorn "${LONGHORN_CHART_URI}" \
          --version "${LONGHORN_VERSION}" \
          --namespace "${LONGHORN_NAMESPACE}" \
          --set image.longhorn.engine.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set image.longhorn.manager.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set image.longhorn.ui.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set image.longhorn.instanceManager.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set image.longhorn.shareManager.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set image.longhorn.backingImageManager.registry="${APPCO_LONGHORN_COMPOMENT_REGISTRY}" \
          --set global.imagePullSecrets="{application-collection}"
      fi

      if [[ $? -eq 0 ]]; then
        echo "Helm install/upgrade succeeded on attempt $i"
        break
      else
        echo "Helm install/upgrade failed on attempt $i"
        sleep 10
      fi

      if [[ $i -eq ${HELM_INSTALL_RETRY_LIMIT} ]]; then
        echo "Helm install/upgrade failed after 3 attempts. Exiting."
        exit 1
      fi
     done
  fi
  wait_longhorn_status_running
}

install_longhorn_stable(){
  if [[ "${LONGHORN_STABLE_VERSION_CHART_URI}" == "longhorn/longhorn" ]]; then
    helm repo add longhorn https://charts.longhorn.io
    helm repo update
    helm upgrade --install longhorn longhorn/longhorn \
      --namespace "${LONGHORN_NAMESPACE}" \
      --version "${LONGHORN_STABLE_VERSION}"
  else
    # set debugging mode off to avoid leaking appco secrets to the logs.
    # DON'T REMOVE!
    set +x
    helm_login_appco
    set -x

    for ((i=1; i<=HELM_INSTALL_RETRY_LIMIT; i++)); do
      helm upgrade --install longhorn "${LONGHORN_STABLE_VERSION_CHART_URI}" \
        --version "${LONGHORN_STABLE_VERSION}" \
        --namespace "${LONGHORN_NAMESPACE}" \
        --set global.imagePullSecrets="{application-collection}"
      if [[ $? -eq 0 ]]; then
        echo "Helm install/upgrade succeeded on attempt $i"
        break
      else
        echo "Helm install/upgrade failed on attempt $i"
        sleep 10
      fi

      if [[ $i -eq ${HELM_INSTALL_RETRY_LIMIT} ]]; then
        echo "Helm install/upgrade failed after 3 attempts. Exiting."
        exit 1
      fi
    done
  fi
  wait_longhorn_status_running
}

install_longhorn_transient(){
  if [[ "${LONGHORN_TRANSIENT_VERSION_CHART_URI}" == "longhorn/longhorn" ]]; then
    helm repo add longhorn https://charts.longhorn.io
    helm repo update
    helm upgrade --install longhorn longhorn/longhorn \
      --namespace "${LONGHORN_NAMESPACE}" \
      --version "${LONGHORN_TRANSIENT_VERSION}"
  else
    # set debugging mode off to avoid leaking appco secrets to the logs.
    # DON'T REMOVE!
    set +x
    helm_login_appco
    set -x

    for ((i=1; i<=HELM_INSTALL_RETRY_LIMIT; i++)); do
      helm upgrade --install longhorn "${LONGHORN_TRANSIENT_VERSION_CHART_URI}" \
        --version "${LONGHORN_TRANSIENT_VERSION}" \
        --namespace "${LONGHORN_NAMESPACE}" \
        --set global.imagePullSecrets="{application-collection}"
      if [[ $? -eq 0 ]]; then
        echo "Helm install/upgrade succeeded on attempt $i"
        break
      else
        echo "Helm install/upgrade failed on attempt $i"
        sleep 10
      fi

      if [[ $i -eq ${HELM_INSTALL_RETRY_LIMIT} ]]; then
        echo "Helm install/upgrade failed after 3 attempts. Exiting."
        exit 1
      fi
    done
  fi
  wait_longhorn_status_running
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
