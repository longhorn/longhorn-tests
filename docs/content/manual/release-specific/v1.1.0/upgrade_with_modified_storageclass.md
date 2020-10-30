---
title: Upgrade Longhorn with modified Storage Class
---

## Intro

Longhorn can be upgraded with modified Storage Class.

## Related Issue
https://github.com/longhorn/longhorn/issues/1527

## Test steps:
### Kubectl apply -f
1. Install Longhorn v1.0.2
   ```
   kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.0.2/deploy/longhorn.yaml
   ```
1. Create a statefulset using `longhorn` storageclass for PVCs. Set the scale to 1.
1. Observe that there is a workload pod (`pod-1`) is using 1 volume (`vol-1`) with 3 replicas.
1. In Longhorn repo, on `master` branch. Modify `numberOfReplicas: "1"` in `https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml`. Upgrade Longhorn to master by running
   ```
   kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml
   ```
1. Verify that `longhorn` storage class now has the field `numberOfReplicas: 1`.
1. Scale up the deployment to 2. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.
1. Scale up the deployment to 0 then back to 2. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.

### Helm
1. Follow this instruction to install Longhorn v1.0.2 using Helm https://longhorn.io/docs/1.0.2/deploy/install/install-with-helm/#installing-longhorn
1. Create a statefulSet using `longhorn` storage class for PVCs. Set the scale to 1.
1. Observe that there is a workload pod (`pod-1`) is using 1 volume (`vol-1`) with 3 replicas.
1. Clone the longhorn chart in local system and checkout to Longhorn repo, upgrade Longhorn to the master version by running:
   ```
   helm upgrade longhorn chart/ -n longhorn-system --set persistence.defaultClassReplicaCount=1,image.longhorn.manager.tag=master
   ```
1. Verify that no error occurs.
1. Verify that `longhorn` storage class now has the field `numberOfReplicas: 1`.
1. Scale up the deployment to 2. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.
1. Scale up the deployment to 0 then back to 2. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.
1. Upgrade Longhorn again by running:
   ```
   helm upgrade longhorn chart/ -n longhorn-system --set persistence.defaultClassReplicaCount=2,image.longhorn.manager.tag=master
   ```
1. Verify that no error occurs.
1. Verify that `longhorn` storage class now has the field `numberOfReplicas: 2`.
1. Scale up the deployment to 3. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.
   * `pod-3` is using volume `vol-3` with 2 replicas.
1. See the current Longhorn release's `revision`:
   ```
   helm list -n longhorn-system
   ```
1. Rollback to the previous version by:
   ```
   helm rollback longhorn <REVISION - 1> -n longhorn-system
   ```
1. Verify that no error occurs.
1. Verify that `longhorn` storage class now has the field `numberOfReplicas: 1`.
1. Scale up the deployment to 4. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica.
   * `pod-3` is using volume `vol-3` with 2 replicas.
   * `pod-4` is using volume `vol-4` with 1 replicas.

1. Rollback to the very first version by:
   ```
   helm rollback longhorn 1 -n longhorn-system
   ```
1. See the error:
   ```
   Error: no StorageClass with the name "longhorn" found
   ```
   This is because the Longhorn master version already replaced the initial `longhorn` storage class by a different version. Users have to manually delete `longhorn` storage class before they can rollback. In the future (e.g. when upgrade/rollback between v.1.1 +) this issue will not happen because the versions after v1.1+ we don't use Helm template for `longhorn` storage class

### Rancher UI
1. Install Longhorn v1.0.2 using the rancher app catalog.  
1. Create a statefulSet using `longhorn` storage class for PVCs. Set the scale to 1.
1. Observe that there is a workload pod (`pod-1`) is using 1 volume (`vol-1`) with 3 replicas.
1. From Rancher UI, upgrade the chart to v1.1.0. In the upgrading UI, change parameter `Default Storage Class Replica Count: 1` before clicking Save
1. Verify that no error occurs.
1. Verify that `longhorn` storage class now has the field `numberOfReplicas: 1`.
1. Scale up the deployment to 2. Verify that:
   * `pod-1` is using volume `vol-1` with 3 replicas.
   * `pod-2` is using volume `vol-2` with 1 replica. 
