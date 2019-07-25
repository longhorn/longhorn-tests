# Longhorn Manager tests
[![Build Status](http://drone-publish.rancher.io/api/badges/longhorn/longhorn-tests/status.svg)](http://drone-publish.rancher.io/longhorn/longhorn-tests)

## Integration test

Requirement:
1. A Kubernetes cluster with at least 3 nodes
2. Longhorn system has already been successfully deployed in the cluster.
3. No volume exists in the Longhorn system.
4. Need kubernetes 1.10 or higher.
5. Make sure MountPropagation feature gate is enabled
   5.1 For RKE before v0.1.9, you would need the extra parameter feature-gates: `MountPropagation=true` for kube-api and kubelet to enable the feature gate.

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
