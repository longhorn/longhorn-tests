---
title: Test node deletion
---
### Case 1: Delete multiple kinds of nodes:
1. Deploy Longhorn.
2. Shut down the VM for one node and wait for the node `Down`. Disable another node.
3. Delete the above 2 nodes. Make sure the corresponding Kubernetes node object is deleted. --> The related Longhorn node objects will be cleaned up immediately, too.
4. Add new nodes with the same names for the cluster. --> The new nodes are available. 


### Case 2: Delete nodes when there are running volumes:
1. Deploy Longhorn.
2. For each node that will be deleted later: 
    1. create and attach 4 volumes:
        1. The 1st volume contains 1 replica only. Both the engines and the replicas are on the pre-delete node. (Attached to the pre-delete node.)
        2. The 2nd volume contains 1 replica only. The engine is on the pre-delete node and the replica is on another node. (Attached to the pre-delete node.)
        3. The 3rd and the 4th volume contain 3 replicas. Both volumes are attached to a node except for the pre-delete node.
    2. Write some data to all volumes.
3. Delete multiple nodes in the cluster simultaneously. Make sure the corresponding Kubernetes node object is deleted. --> The related Longhorn node objects will be cleaned up immediately, too.
4. For each deleted node:
    1.Verify the volume Health state  -->
        1. The 1st volume should become `Faulted`.
        2. The 2nd volume should keep `Unknown`.
        3. The 3rd and the 4th volume should become `Degraded`.
    2. Delete the 1st volume. --> The volume can be deleted.
    3. Detach then reattach the 2nd volume. --> The volume works fine and the data is correct.
    4. Crash all replicas of the 3rd volume and trigger the auto salvage. --> The auto salvage should work. The volume works fine and the data is correct after the salvage.
    5. Disabled the auto salvage setting. Then crash all replicas of the 3rd volume again. --> The replica on the deleted node cannot be salvaged manually, too. The salvage feature still works fine.
    6. Deleted the replica on the deleted node for the 4th volume. --> The replica can be deleted.
