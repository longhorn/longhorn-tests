---
title: Node disconnection test
---
https://github.com/longhorn/longhorn/issues/1545
For disconnect node : https://github.com/longhorn/longhorn/files/4864127/network_down.sh.zip

### Case 1:
1. Disable the setting auto-salvage.
2. Create and attach a volume.
3. Keep writing data to the volume. Disconnect the node that the volume attached to for 100 seconds during the data writing.
4. Wait for the node back.
5. The volume will be detached then reattached automatically. And there are some replicas still running after the reattachment.

### Case 2:
1. Launch Longhorn.
2. Use statefulset launch a pod with the volume and write some data.
3. Disconnect the node that the volume attached to for 100 seconds.
4. Wait for the node back and the volume reattachment.
5. During volume detached/attached, pod will auto delete/create 
6. Verify the data and the pod still works fine.
7. Repeat step 2~6 for 3 times.
8. Create, Attach, and detach other volumes to the recovered node. All volumes should work fine.
9. Remove Longhorn and repeat step 1~9 for 3 times.
