# Longhorn Manager tests

## Integration test

Requirement:
1. A Kubernetes cluster
2. Longhorn system has already been successfully deployed in the cluster.
3. No volume exists in the Longhorn system.

Run the test:
1. Deploy the [Minio](https://docs.minio.io) server for s3 test purpose, acting as the s3 backupstore.
```
kubectl create -f integration/deploy/minio-backupstore.yaml
```
If you want to test nfs backup, Deploy the nfs server.
```
kubectl create -f integration/deploy/nfs-backupstore.yaml
```
2. Deploy the test script to the Kubernetes cluster.
```
kubectl create -f integration/deploy/test.yaml
```

Then watch the result:
```
kubectl logs -f longhorn-test
```
