---
title: Test node deletion
---
### Case 1: Delete multiple kinds of nodes:
1. Deploy Longhorn.
2. Shut down the VM for one node and wait for the node `Down`. Disable another node.
3. Delete the above 2 nodes. Make sure the corresponding Kubernetes node object is deleted. --> The related Longhorn node objects will be cleaned up immediately, too.
4. Add new nodes with the same names for the cluster. --> The new nodes are available. 


### Case 2: Delete nodes when there are running volumes:
We need to update step 4.1.1 related steps after https://github.com/longhorn/longhorn/issues/5542 resolved.

1. Deploy Longhorn.
2. For each node that will be deleted later: 
    1. Create and attach 4 volumes:
        1. The 1st volume contains 1 replica only. Both the engines and the replicas are on the pre-delete node. (Attached to the pre-delete node.)
        2. The 2nd volume contains 1 replica only. The engine is on the pre-delete node and the replica is on another node. (Attached to the pre-delete node.)
        3. The 3rd volume contains 1 replica only. The replica is on the pre-delete node and the engine is on another node. (Attached to a node except for the pre-delete node.)
        4. The 4th volume contain 3 replicas. Attached to a node except for the pre-delete node.
    2. Write some data to all volumes.
3. Delete multiple nodes in the cluster simultaneously. Make sure the corresponding Kubernetes node object is deleted. --> The related Longhorn node objects will be cleaned up immediately, too.
4. For each deleted node:
    1. Verify the volume Health state  -->
        1. The 1st volume should keep `Unknown`.
        2. The 2nd volume should keep `Unknown`.
        3. The 3rd volume should become `Faulted`.
        4. The 4th and 5th volume should become `Degraded`.
    2. Detach then reattach the 1st volume. --> The volume in detached state and can not be attached to another node.
    3. Detach then reattach the 2nd volume. --> The volume works fine and the data is correct.
    4. Delete the 3rd volume. --> The volume can be deleted.
    5. Deleted the replica on the deleted node for the 4th volume. --> The replica can be deleted.
    6. Crash all replicas of the 4th volume and trigger the auto salvage. --> The auto salvage should work. The volume works fine and the data is correct after the salvage.
        * An example to crash every volume replica instance manager pods with kubectl:
            - `kubectl delete pods -l longhorn.io/instance-manager-type=replica -n longhorn-system --wait`
    7. Disabled the auto salvage setting. Then crash all replicas of the 4th volume again. --> The replica on the deleted node cannot be salvaged manually, too. The salvage feature still works fine.
