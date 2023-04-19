---
title: Node disconnection test
---
https://github.com/longhorn/longhorn/issues/1545
For disconnect node : https://github.com/longhorn/longhorn/files/4864127/network_down.sh.zip

If auto-salvage is disabled, the auto-reattachment behavior after the node disconnection depends on all replicas are in ERROR state or not.

(1) If all replicas are in ERROR state, the volume would remain in detached/faulted state if auto-salvage is disabled.

(2) If there is any healthy replica, the volume would be auto-reattached even though auto-salvage is disabled.

What makes all replicas in ERROR state? When there is data writing during the disconnection:

(1) If the engine process is unable to talk with a replica (the engine process and the replica are on the different nodes), the engine process will mark the replica as ERROR. 

(2) But if the engine process is still able to talk with a replica (the engine process and the replica are on the same node), the engine process will just mark the replica as UNKNOWN state, and the replica will recover to RUNNING state after the network connection is back. Then other replicas can be rebuilt from the replica.

So we have 2 * 2 test cases for node disconnection + disabled auto-salvage:

(Case 1-1) there is no replica on the attached node + data writing during the disconnection -> all replicas become ERROR -> no auto-reattach after the disconnection

(Case 1-2) there is a replica on the attached node + data writing during the disconnection -> one replica can recover to healthy -> auto-reattach after the disconnection

(Case 2-1) there is no replica on the attached node + no data writing during the disconnection -> other replicas are still healthy -> auto-reattach after the disconnection

(Case 2-2) there is a replica on the attached node + no data writing during the disconnection -> other replicas are still healthy -> auto-reattach after the disconnection

### Case 1-1:
1. Disable auto-salvage.
2. Create a volume named test-1 with 2 replicas on the 1st and the 2nd node.
3. Attach the volume to the 3rd node.
4. Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
5. Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
6. Wait for the node back.
7. The volume should remain detached, and all replicas remain in ERROR state.

### Case 1-2:
1. Disable auto-salvage.
2. Create a volume named test-1 with 3 replicas.
3. Attach the volume to a node.
4. Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
5. Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
6. Wait for the node back.
7. The volume will be detached then reattached automatically, and replicas should still be in RUNNING state.

### Case 2-1:
1. Disable auto-salvage.
2. Create a volume named test-1 with 2 replicas on the 1st and the 2nd node.
3. Attach the volume to the 3rd node.
4. No need to write data to the volume. Directly disconnect the network of the node that the volume attached to for 100 seconds. (sudo nohup ./network_down.sh 100)
5. Wait for the node back.
6. The volume will be detached then reattached automatically, and replicas should still be in RUNNING state.

### Case 2-2:
1. Disable auto-salvage.
2. Create a volume named test-1 with 3 replicas.
3. Attach the volume to a node.
4. No need to write data to the volume. Directly disconnect the network of the node that the volume attached to for 100 seconds. (sudo nohup ./network_down.sh 100)
5. Wait for the node back.
6. The volume will be detached then reattached automatically, and replicas should still be in RUNNING state.

### Case 3:
1. Launch Longhorn.
2. Use statefulset launch a pod with the volume and write some data.
3. Run command 'sync' in pod, make sure data fulshed.
4. Disconnect the node that the volume attached to for 100 seconds.
5. Wait for the node back and the volume reattachment.
6. After the volume is reattached, the pod will be automatically deleted and recreate.
7. Verify the data and the pod still works fine.
8. Repeat step 2~6 for 3 times.
9. Create, Attach, and detach other volumes to the recovered node. All volumes should work fine.
10. Remove Longhorn and repeat step 1~9 for 3 times.
