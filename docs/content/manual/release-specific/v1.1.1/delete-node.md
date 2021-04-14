---
title: Test Node Delete
---

## Related issue
https://github.com/longhorn/longhorn/issues/2186
https://github.com/longhorn/longhorn/issues/2462


## Delete Method ##
Should verify with both of the delete methods.
* Bulk Delete - This is the `Delete` on the Node page.
* Node Delete - This is the `Remove Node` for each node `Operation` drop-down list.


## Test Node Delete - should grey out when node not down

**Given** node not `Down`.

**When** Try to delete any node.

**Then** Should see button greyed out.


## Test Node Delete

**Given** pod with pvc created.
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.0/examples/pod_with_pvc.yaml
```
*And* node down:

1. Disable Node Scheduling and set Eviction Requested to true from the browser.
2. Taint node-1 with kubectl and wait for pods to re-deploy.
    ```
    kubectl taint nodes ${NODE} nodetype=storage:NoExecute
    ```

    2.1. Check longhorn pods are not scheduled to node-1.

    2.2. Node status should be Down.

**When** delete node-1 from the browser.

**Then** click `OK` in the pop-up window for delete confirmation.

*And* should see node-1 removed from the node list in the browser.

*And* should see node-1 removed from nodes.longhorn.io.
```
kubectl -n longhorn-system get nodes.longhorn.io
```


## Test Node Delete - should delete the node when the node is down, even the schedule is enabled and replicas not evicted from the node

**Given** Cluster with 4 nodes.

*And* pod with pvc created.
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.0/examples/pod_with_pvc.yaml
```

*And* node with replica is down:

1. Taint node-1 with kubectl and wait for pods to re-deploy.
    ```
    kubectl taint nodes ${NODE} nodetype=storage:NoExecute
    ```
    1.1. Check longhorn pods are not scheduled to node-1.
    1.2. Node status should be Down.

2. Longhorn replica should be stopped for the tainted node.
    ```
    ip-172-30-0-21:~ # kubectl -n longhorn-system get replica
    NAME                                                  STATE     NODE              DISK                                   INSTANCEMANAGER                IMAGE                               AGE
    pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-1c6008f2   running   ip-172-30-0-21    fad71ef9-a830-495c-974d-06538e4387fa   instance-manager-r-f694df29   longhornio/  longhorn-engine:master   50m
    pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-cab245c9   running   ip-172-30-0-190   3d435563-bd11-4566-bd9f-34815920a9e8   instance-manager-r-eb56d441   longhornio/  longhorn-engine:master   50m
    pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-e79536a5   stopped   ip-172-30-0-16    c1c8597d-f3ee-44fc-b045-ee51beb14bb6                                                                       28m
    ```

3. Volume should be degraded.
    ```
    ip-172-30-0-21:~ # kubectl -n longhorn-system get volume
    NAME                                       STATE      ROBUSTNESS   SCHEDULED    SIZE         NODE              AGE
    pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b   attached   degraded     True         2147483648   ip-172-30-0-190   64m
    ```

**When** delete node-1 from the browser.

**Then** click `OK` in the pop-up window for delete confirmation.

*And* should see node-1 removed from the node list in the browser.

*And* should see node-1 removed from nodes.longhorn.io.
```
kubectl -n longhorn-system get nodes.longhorn.io
```

*And* should see replica re-scheduled to an available node.
```
ip-172-30-0-21:~ # kubectl -n longhorn-system get replica
NAME                                                  STATE     NODE              DISK                                   INSTANCEMANAGER               IMAGE                               AGE
pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-1c6008f2   running   ip-172-30-0-21    fad71ef9-a830-495c-974d-06538e4387fa   instance-manager-r-f694df29   longhornio/longhorn-engine:master   53m
pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-cab245c9   running   ip-172-30-0-190   3d435563-bd11-4566-bd9f-34815920a9e8   instance-manager-r-eb56d441   longhornio/longhorn-engine:master   53m
pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b-r-a45afce7   running   ip-172-30-0-85    f78a06cc-56df-4269-b98c-e51504aaba10   instance-manager-r-79bd9ce1   longhornio/longhorn-engine:master   18s
```

*And* volume should eventually become healthy.
```
NAME                                       STATE      ROBUSTNESS   SCHEDULED   SIZE         NODE              AGE
pvc-cf792de8-62be-4c8d-bd6e-dc855d958e8b   attached   healthy      True        2147483648   ip-172-30-0-190   73m
```

## Test Node Delete - when the volume has only 1 replica should fail to delete the node when the node is down, the schedule is enabled and replicas not evicted from the node.

**Given** pod with pvc created.
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.0/examples/pod_with_pvc.yaml
```

*And* volume has only 1 replica.

*And* node with the 1 replica is down:

1. Taint node-1 with kubectl and wait for pods to re-deploy.
    ```
    kubectl taint nodes ${NODE} nodetype=storage:NoExecute
    ```
    1.1. Check longhorn pods are not scheduled to node-1.
    1.2. Node status should be Down.

2. Longhorn replica should be stopped.
    ```
    ip-172-30-0-21:~ # kubectl -n longhorn-system get replica
    NAME                                                  STATE         NODE             DISK                                   INSTANCEMANAGER     IMAGE   AGE
    pvc-b040fe48-5ee1-4a7b-9b3a-accc65f7e947-r-b9d1a5bd   stopped       ip-172-30-0-85      f78a06cc-56df-4269-b98c-e51504aaba10                             9m39s
    ```


**When** delete node-1 from the browser.

**Then** click `OK` in the pop-up window for delete confirmation.

*And* should see pop-up error bar.
```
unable to delete node: Could not delete node ip-172-30-0-85 with node ready condition is False, reason is ManagerPodMissing, node schedulable false, and 1 replica, 0 engine running on it
```

*And* should see node-1 still exist in the node list in the browser.

*And* should see node-1 still exist in nodes.longhorn.io.
```
ip-172-30-0-21:~ # kubectl -n longhorn-system get nodes
NAME              STATUS     ROLES                  AGE     VERSION
ip-172-30-0-16    Ready      <none>                 26h     v1.20.5+k3s1
ip-172-30-0-21    Ready      control-plane,master   26h     v1.20.5+k3s1
ip-172-30-0-85    Ready      <none>                 26h     v1.20.5+k3s1
```
