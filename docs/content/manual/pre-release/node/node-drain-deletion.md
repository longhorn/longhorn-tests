---
title: Node drain and deletion test
---
## Drain with force
Make sure the volumes on the drained/removed node can be detached or recovered correctly. The related issue: https://github.com/longhorn/longhorn/issues/1214
1. Deploy a cluster contains 3 worker nodes N1, N2, N3.
2. Deploy Longhorn.
3. Create a 1-replica deployment with a 3-replica Longhorn volume. The volume is attached to N1.
4. Write some data to the volume and get the md5sum.
5. Force drain and remove N2, which contains one replica only.
   ```
   kubectl drain <Node name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
   ```
6. Wait for the volume Degraded.
7. Force drain and remove N1, which is the node the volume is attached to.
   ```
   kubectl drain <Node name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
   ```
8. Verify the instance manager pods are gone and not recreated after the drain.
9. Wait for the volume detaching then being recovered. Will get attached to the workload/node.
10. Validate the volume content. The data is intact.

## Drain without force
1. Cordon the node. Longhorn will automatically disable the node scheduling when a Kubernetes node is cordoned.
2. Evict all the replicas from the node.
3. Run the following command to drain the node with ```force``` flag set to false.
    ```
    kubectl drain <Node name> --delete-emptydir-data --force=false --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
    ```
4. Observe that the workloads move to another node. The volumes should first detach and attach to workloads once they move to another node.
5. Observe the logs, one by one all the pods should get evicted.
    ```
    node/<node-name> already cordoned
    WARNING: ignoring DaemonSet-managed Pods: ingress-nginx/nginx-ingress-controller-bpf2t, kube-system/canal-hwk6v, longhorn-system/engine-image-ei-605a0f3e-8gb8l, longhorn-system/longhorn-csi-plugin-flq84, longhorn-system/longhorn-manager-tps6v
    evicting pod longhorn-system/instance-manager-r-1aebab59
    evicting pod kube-system/coredns-849545576b-v54vn
    evicting pod longhorn-system/instance-manager-e-e591dbce
    pod/instance-manager-r-1aebab59 evicted
    pod/instance-manager-e-e591dbce evicted
    pod/coredns-849545576b-v54vn evicted
    node/<node-name> evicted
    ```
6. Verify the instance manager pods are gone and not recreated after the drain.

Note: ```--ignore-daemonsets``` should be set to true to ignore some DaemonSets that exist on node such as Longhorn manager, Longhorn CSI plugin, engine image in a Longhorn deployed cluster.


## [Test kubectl drain nodes for PVC/PV/LHV is created through Longhorn UI](https://github.com/longhorn/longhorn/issues/2673)
**Given** 1 PVC/PV/LHV created through Longhorn UI
_And_ LHV is not yet attached/replicated.

**When** kubectl drain nodes.

```bash
NODE=centos-worker-0
kubectl cordon ${NODE}
kubectl drain --force --ignore-daemonsets --delete-emptydir-data --grace-period=10 ${NODE}
```

**Then** all node should successfully drain.

NOTE: We might still 1 or 2 times of the pod's disruption budget message, but will drain successfully in the end.

```log
evicting pod longhorn-system/instance-manager-r-xxxxxxxx
error when evicting pods/"instance-manager-r-xxxxxxxx" -n "longhorn-system" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption budget.
```


## Stopped replicas on deleted nodes should not be counted as healthy replicas when draining nodes

When draining a node, the node will be set as unscheduled and all pods should be evicted.

By Longhorn's default settings, the replica will only be evicted if there is another healthy replica on the running node.

#### Related Issue:
- https://github.com/longhorn/longhorn/issues/2237

**Given** Longhorn with 2 nodes cluster: Node_1, Node_2

*And* Create a 5Gi detached volume with 2 replicas.

*And* Stop Node_1 that contains one of the replicas.

*And* Uncheck the `Allow Node Drain with the Last Healthy Replica` setting and confirm getting **false** with following command:
```shell
kubectl get settings.longhorn.io/allow-node-drain-with-last-healthy-replica -n longhorn-system
```

**When** Attempts to drain Node_2 that contains remaining replica.
```shell
kubectl drain <Node_2 name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true
```

**Then** The Node_2 becomes cordoned.

*And* All pods on Node_2 are evicted except the replica instance manager pod. 
```shell
kubectl get pods --field-selector spec.nodeName=<Node_2 name> -o wide -n longhorn-system
```

*And* The message like below keeps appearing.
```
evicting pod longhorn-system/instance-manager-r-xxxxxxxx
error when evicting pods/"instance-manager-r-xxxxxxxx" -n "longhorn-system" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption budget.
```

*And* The last healthy replica exists on the Node_2.

## Setting `Allow Node Drain with the Last Healthy Replica` protects the last healthy replica with Pod Disruption Budget (PDB) 

#### Related Issue:
- https://github.com/longhorn/longhorn/issues/2237

**Given** Longhorn with 2 nodes cluster: Node_1, Node_2

*And* Create a 5Gi detached volume with 2 replicas.

*And* Stop Node_1 that contains one of the replicas.

*And* Uncheck the `Allow Node Drain with the Last Healthy Replica` setting and confirm getting **false** with following command:
```shell
kubectl get settings.longhorn.io/allow-node-drain-with-last-healthy-replica -n longhorn-system
```

*And* Drain Node_2 so that all pods on Node_2 are evicted, but the replica instance manager pod is still on Node_2 because it is protected by PDB. 
```shell
kubectl drain <Node_2 name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true
```

**When** Enable the setting `Allow Node Drain with the Last Healthy Replica` and make sure return **true** with following command:
```shell
kubectl get settings.longhorn.io/allow-node-drain-with-last-healthy-replica -n longhorn-system
```

**Then** The pod `longhorn-system/instance-manager-r-xxxxxxxx` will be evicted successfully and the following command can be used to ensure that only daemonset pods such as `engine-image`, `longhorn-csi-plugin` and `longhorn-manager` daemonset pods are running on Node_2:
```shell
kubectl get pods --field-selector spec.nodeName=<Node_2 name> -o wide -n longhorn-system
```

*And* The PDB will be deleted and can be verified with the following command:
```shell
kubectl get pdb <replica name, e.g., instance-manager-r-xxxxxxxx> -n longhorn-system
```