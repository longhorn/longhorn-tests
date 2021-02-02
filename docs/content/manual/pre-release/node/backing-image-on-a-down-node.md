---
title: Backing Image on a down node
---

1. Update the settings:
   1. Disable Node Soft Anti-affinity.
   2. Set Replica Replenishment Wait Interval to a relatively long value.
2. Create a backing image with one of the following URLs:
```
   https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
   https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw
```
3. Create 2 volumes with the backing image and attach them on different nodes. Verify: 
   - the disk state map of the backing image contains the disks of all replicas, and the state is running for all disks.
   - the backing image content is correct
4. Write random data to the volumes.
5. Power off a node containing one volume. Verify that
   - the related disk download state in the backing image will become `failed` once the download pod is removed by Kubernetes.
   - the volume on the running node still works fine but is state `Degraded`, and the content is correct in the volume.
   - the volume on the down node become `Unknown`.
6. Power on the node. Verify
   - the failed replica of the `Degraded` volume can be reused.
   - the volume on the down node will be recovered automatically. And the data is correct.
   - the backing image will be recovered automatically.
7. Delete all replicas expect for the reused failed replica for the volume not on the down node. Then wait for rebuilding and check the data. This verifies the reused replica data content. 
