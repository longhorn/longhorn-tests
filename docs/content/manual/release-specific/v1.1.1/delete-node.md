---
title: Test Node Delete
---

## Related issue
https://github.com/longhorn/longhorn/issues/2186

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

**When** node-1 deleted from the browser.

**Then** should see node-1 removed from the node list in the browser.

*And* should see node-1 removed from nodes.longhorn.io.
```
kubectl -n longhorn-system get nodes.longhorn.io
```


## Test Node Delete - should fail when volume replica not evicted on node

**Given** pod with pvc created.
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.0/examples/pod_with_pvc.yaml
```

*And* node down:

1. Taint node-1 with kubectl and wait for pods to re-deploy.
    ```
    kubectl taint nodes ${NODE} nodetype=storage:NoExecute
    ```
    1.1. Check longhorn pods are not scheduled to node-1.

    1.2. Node status should be Down.

    1.3. Check longhorn replicas are running on node-1.
    ```
    kubectl -n longhorn-system get replicas
    ```

**When** node-1 deleted from the browser.

**Then** should see error in the browser.
```
unable to delete node: Could not delete node ip-172-30-0-16 with node ready condition is False, reason is ManagerPodMissing, node schedulable false, and 1 replica, 1 engine running on it
```