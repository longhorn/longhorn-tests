install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml"
  CIFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/cifs-backupstore.yaml"
  AZURITE_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/azurite-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
                 -f ${NFS_BACKUPSTORE_URL} \
                 -f ${CIFS_BACKUPSTORE_URL} \
                 -f ${AZURITE_BACKUPSTORE_URL}
  setup_azuitize_backup_store
}

setup_azuitize_backup_store(){
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

  AZBLOB_ENDPOINT=$(echo -n "http://$(kubectl get svc azblob-service -o jsonpath='{.spec.clusterIP}'):10000/" | base64)
  kubectl -n longhorn-system patch secret azblob-secret \
    --type=json \
    -p="[{'op': 'replace', 'path': '/data/AZBLOB_ENDPOINT', 'value': \"${AZBLOB_ENDPOINT}\"}]"

  CONTROL_PLANE_PUBLIC_IP=$(cat /tmp/controlplane_public_ip)
  # port forward and az container create need to be run on control node
  ssh ec2-user@${CONTROL_PLANE_PUBLIC_IP} "nohup kubectl port-forward --address 0.0.0.0 service/azblob-service 20001:10000 > /dev/null 2>&1 &"
  ssh ec2-user@${CONTROL_PLANE_PUBLIC_IP} "az storage container create -n longhorn-test-azurite --connection-string 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://0.0.0.0:20001/devstoreaccount1;'"
}