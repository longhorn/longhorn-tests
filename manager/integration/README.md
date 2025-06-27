# Longhorn Manager tests
[![Build Status](http://drone-publish.longhorn.io/api/badges/longhorn/longhorn-tests/status.svg)](http://drone-publish.longhorn.io/longhorn/longhorn-tests)

## Integration test

Requirement:
1. A Kubernetes cluster with at least 3 worker nodes.
   - And control node(s) with following taints:
      - `node-role.kubernetes.io/control-plane:NoSchedule` 
2. Longhorn system has already been successfully deployed in the cluster.
3. No volume exists in the Longhorn system.
4. Need kubernetes 1.10 or higher.
5. Make sure MountPropagation feature gate is enabled
   - For RKE before v0.1.9, you would need the extra parameter feature-gates: `MountPropagation=true` for kube-api and kubelet to enable the feature gate.
6. Make sure `nfs-common` or equivalent has been installed on the node to allow the NFS client to work.

Run the test:
1. Deploy all backupstore servers(including `NFS` server and `Minio` as s3 server `CIFS` and `Azurite` server) for test purposes.
   
   For Azurite, there are some manual steps need to be done after manifest deployed(https://github.com/longhorn/longhorn-tests/wiki/Setup-Azurite-Backupstore-For-Testing).
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/cifs-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/azurite-backupstore.yaml
```
2. Deploy the test script to the Kubernetes cluster.
```
kubectl create -f integration/deploy/test.yaml
```

Then watch the result:
```
kubectl logs -f longhorn-test -c longhorn-test
```
