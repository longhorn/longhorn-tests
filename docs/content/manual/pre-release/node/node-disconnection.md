---
title: Node disconnection test
---
https://github.com/longhorn/longhorn/issues/1545
### Case 1:
1. Disable the setting auto-salvage.
2. Create and attach a volume.
3. Keep writing data to the volume. Disconnect the node that the volume attached to for 100 seconds during the data writing.
4. Wait for the node back.
5. The volume will be detached then reattached automatically. And there are some replicas still running after the reattachment.

### Case 2:
1. Launch Longhorn.
2. Launch a pod with the volume and write some data. (Remember to set liveness probe for the volume mount point.)
3. Disconnect the node that the volume attached to for 100 seconds.
4. Wait for the node back and the volume reattachment.
5. Verify the data and the pod still works fine.
6. Delete the pod and wait for the volume deleted/detached.
7. Repeat step 2~6 for 3 times.
8. Create, Attach, and detach other volumes to the recovered node. All volumes should work fine.
9. Remove Longhorn and repeat step 1~9 for 3 times.
