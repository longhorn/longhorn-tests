---
title: Node disconnection test
---
https://github.com/longhorn/longhorn/issues/1545
For disconnect node : https://github.com/longhorn/longhorn/files/4864127/network_down.sh.zip

If auto-salvage is disabled, the auto-reattachment behavior after the node disconnection depends on all replicas are in ERROR state or not.

(1) If all replicas are in ERROR state, the volume would remain in detached/faulted state if auto-salvage is disabled.

(2) If there is any healthy replica, the volume would be auto-reattached even though auto-salvage is disabled.

What makes all replicas in ERROR state? If there is data writing during the disconnection, due to the engine process not able to talk with other replicas, the engine process will mark all other replicas as ERROR.

So we have 2 test cases for node disconnection + disabled auto-salvage:

(Case 1) data writing during the disconnection -> all replicas become ERROR -> no auto-reattach after the disconnection

(Case 2) no data writing during the disconnection -> other replicas are still healthy -> auto-reattach after the disconnection

### Case 1:
1. Disable auto-salvage.
2. Create a volume named test-1.
3. Attach the volume to a node.
4. Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
5. Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
6. Wait for the node back.
7. The volume should remain detached, and all replicas remain in ERROR state.

### Case 2:
1. Disable auto-salvage.
2. Create a volume named test-1.
3. Attach the volume to a node.
4. No need to write data to the volume. Directly disconnect the network of the node that the volume attached to for 100 seconds. (sudo nohup ./network_down.sh 100)
5. Wait for the node back.
6. The volume will be detached then reattached automatically, and replicas should still be in RUNNING state.

### Case 3:
1. Launch Longhorn.
2. Use statefulset launch a pod with the volume and write some data.
3. Disconnect the node that the volume attached to for 100 seconds.
4. Wait for the node back and the volume reattachment.
5. After the volume is reattached, the pod will be automatically deleted and recreate.
6. Verify the data and the pod still works fine.
7. Repeat step 2~6 for 3 times.
8. Create, Attach, and detach other volumes to the recovered node. All volumes should work fine.
9. Remove Longhorn and repeat step 1~9 for 3 times.
