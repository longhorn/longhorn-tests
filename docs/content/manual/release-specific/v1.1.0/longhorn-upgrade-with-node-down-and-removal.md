---
title: Longhorn upgrade with node down and removal
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
