install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
                 -f ${NFS_BACKUPSTORE_URL}
}