---
title: Single replica node down
---

## Related Issues
https://github.com/longhorn/longhorn/issues/2329
https://github.com/longhorn/longhorn/issues/2309
https://github.com/longhorn/longhorn/issues/3957

## Default Setting
`Automatic salvage` is enabled.

## Node restart/down scenario with `Pod Deletion Policy When Node is Down` set to default value `do-nothing`.
1. Create RWO|RWX volume with replica count = 1 & data locality = enabled|disabled|strict-local.
   - For data locality = strict-local, use RWO volume to do test.
2. Create deployment|statefulset for volume.
3. Power down node of volume/replica.
4. The workload pod will get stuck in the `terminating` state.
5. Volume will fail to attach since volume is not ready (i.e remains faulted, since single replica is on downed node).
6. Power up node or delete the workload pod so that kubernetes will recreate pod on another node.
7. Verify auto salvage finishes (i.e pod completes start).
8. Verify volume attached & accessible by pod (i.e test data is available).
   - For data locality = strict-local volume, volume wiil keep in detaching, attaching status for about 10 minutes, after volume attached to node which replica located, check volume healthy and pod status.

## Node restart/down scenario with `Pod Deletion Policy When Node is Down` set to `delete-both-statefulset-and-deployment-pod`
1. Create RWO|RWX volume with replica count = 1 & data locality = enabled|disabled|strict-local.
   - For data locality = strict-local, use RWO volume to do test.
2. Create deployment|statefulset for volume.
3. Power down node of volume/replica.
4. Volume will become faulted.
5. Wait for pod deletion & recreation on another node.
   The pod recreation will not happen immediately.
6. The replacement workload pod will get stuck in the `ContainerCreating` state.
7. Power on node of volume/replica.
8. Verify the auto salvage finishes for volumes.
9. Verify volume attached & accessible by pod (i.e test data is available).