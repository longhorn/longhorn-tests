#!/bin/bash

set -x

source pipelines/utilities/longhorn_namespace.sh

install_backupstores(){
  get_longhorn_namespace

  RUSTFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/rustfs-backupstore.yaml"
  wget "${RUSTFS_BACKUPSTORE_URL}" -O rustfs-backupstore.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" rustfs-backupstore.yaml

  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml"
  wget "${NFS_BACKUPSTORE_URL}" -O nfs-backupstore.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" nfs-backupstore.yaml

  CIFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/cifs-backupstore.yaml"
  wget "${CIFS_BACKUPSTORE_URL}" -O cifs-backupstore.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" cifs-backupstore.yaml

  AZURITE_BACKUPSTORE_URL="https://raw.githubusercontent.com/yangchiu/longhorn-tests/67ada7d3c15ed6cf3e29fa0dbb0109f0a9778647/manager/integration/deploy/backupstores/azurite-backupstore.yaml"
  wget "${AZURITE_BACKUPSTORE_URL}" -O azurite-backupstore.yaml
  sed -i "s/longhorn-system/${LONGHORN_NAMESPACE}/g" azurite-backupstore.yaml

  kubectl apply -f rustfs-backupstore.yaml \
                 -f nfs-backupstore.yaml \
                 -f cifs-backupstore.yaml \
                 -f azurite-backupstore.yaml
}

install_backupstores_from_lh_repo(){
  get_longhorn_namespace

  set +x  
  export AWS_ACCESS_KEY_ID="${MINIO_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${MINIO_SECRET_ACCESS_KEY}"
  export AWS_ENDPOINTS="${MINIO_ENDPOINTS}"
  export AWS_CERT="${MINIO_CERT}"
  export AWS_CERT_KEY="${MINIO_CERT_KEY}"
  set -x

  git clone https://github.com/longhorn/longhorn.git
  ./longhorn/scripts/generate-backupstore-credentials.sh all --no-encode
  kubectl apply -k ./longhorn/deploy/backupstores/overlays/generated-credentials/all/
}

setup_azurite_backup_store(){
  get_longhorn_namespace

  RETRY=0
  MAX_RETRY=60
  until (kubectl get pods | grep 'longhorn-test-azblob' | grep 'Running'); do
    echo 'Waiting azurite pod running'
    sleep 5
    if [ $RETRY -eq $MAX_RETRY ]; then
      break
    fi
    RETRY=$((RETRY+1))
  done

  # The azurite NodePort is consumed from inside the cluster (longhorn-manager and the az-cli pod).
  # Reaching the control plane through its public IPv4 address makes the source address the sender's
  # public IP, which the security group does not allow (connection times out), so prefer the control
  # plane node's internal IP.
  # IPv6 addresses are routed without NAT and keep using the address from /tmp/controlplane_public_ip.
  AZURITE_HOST=$(cat /tmp/controlplane_public_ip)
  if [[ "${AZURITE_HOST}" != *:* ]]; then
    CONTROL_PLANE_INTERNAL_IP=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane \
      -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' | awk '{print $1}')
    if [[ -n "${CONTROL_PLANE_INTERNAL_IP}" && "${CONTROL_PLANE_INTERNAL_IP}" != *:* ]]; then
      AZURITE_HOST="${CONTROL_PLANE_INTERNAL_IP}"
    fi
  fi

  AZBLOB_ENDPOINT=$(echo -n "http://${AZURITE_HOST}:31000/" | base64)
  kubectl -n "${LONGHORN_NAMESPACE}" patch secret azblob-secret \
    --type=json \
    -p="[{'op': 'replace', 'path': '/data/AZBLOB_ENDPOINT', 'value': \"${AZBLOB_ENDPOINT}\"}]"

  kubectl delete pod az-cli --ignore-not-found
  kubectl run az-cli \
  --image=mcr.microsoft.com/azure-cli \
  --restart=Never \
  -- az storage container create \
     -n longhorn-test-azurite \
     --connection-string \
     "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://${AZURITE_HOST}:31000/devstoreaccount1;"

  # Ready only means the container started, wait for the one-shot command to finish and verify its result
  AZ_CLI_PHASE=""
  for _ in $(seq 1 60); do
    AZ_CLI_PHASE=$(kubectl get pod az-cli -o jsonpath='{.status.phase}')
    if [[ "${AZ_CLI_PHASE}" == "Succeeded" || "${AZ_CLI_PHASE}" == "Failed" ]]; then
      break
    fi
    sleep 5
  done
  AZ_CLI_LOGS=$(kubectl logs az-cli)
  echo "${AZ_CLI_LOGS}"
  kubectl delete pod az-cli --ignore-not-found
  if [[ "${AZ_CLI_PHASE}" != "Succeeded" ]]; then
    echo "Failed to create azurite container longhorn-test-azurite via ${AZURITE_HOST}:31000 (az-cli phase: ${AZ_CLI_PHASE})" >&2
    return 1
  fi
}

install_backupstores_networkpolicy(){
  BACKUPSTORE_NETWORK_POLICY_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/backupstore-networkpolicy.yaml"
  kubectl create -f ${BACKUPSTORE_NETWORK_POLICY_URL}
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
