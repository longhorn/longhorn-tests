---
title: Reusing failed replica for rebuilding
---

## Longhorn upgrade with node down and removal
1. Launch Longhorn v1.0.x
2. Create and attach a volume, then write data to the volume.
3. Directly remove a Kubernetes node, and shut down a node.
4. Wait for the related replicas failure. Then record `replica.Spec.DiskID` for the failed replicas.
5. Upgrade to Longhorn master
6. Verify the Longhorn node related to the removed node is gone.
7. Verify 
    1. `replica.Spec.DiskID` on the down node is updated and the field of the replica on the gone node is unchanged.
    2.  `replica.Spec.DataPath` for all replicas becomes empty.
8. Remove all unscheduled replicas.
9. Power on the down node. Wait for the failed replica on the down node being reused.
10. Wait for a new replica being replenished and available.

## Replica not available for reuse after disk migration
1. Deploy longhorn v1.1.0
2. Create and attach a volume, then write data to the volume.
3. Directly remove a Kubernetes node which has a replica on it.
4. Wait for the related replicas failure.
5. Verify the Longhorn node related to the removed node is gone.
6. Ssh to the node and crash the replica folder or make it readonly.
8. Add the node in the cluster again.
9. Verify a new replica being rebuilt and available.
10. Verify the data of the replica.
