# Longhorn Manager tests

## Integration test

Requirement:
1. A Kubernetes cluster with at least 3 nodes
2. Longhorn system has already been successfully deployed in the cluster.
3. No volume exists in the Longhorn system.

Run the test:
1. Deploy all backupstore servers(including `NFS` server and `Minio` as s3 server) for test purpose.
```
kubectl create -Rf integration/deploy/backupstores
```
2. Deploy the test script to the Kubernetes cluster.
```
kubectl create -f integration/deploy/test.yaml
```

Then watch the result:
```
kubectl logs -f longhorn-test
```
