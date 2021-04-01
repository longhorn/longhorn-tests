---
title: Backing Image on a down node
---

1. Update the settings:
   1. Disable Node Soft Anti-affinity.
   2. Set Replica Replenishment Wait Interval to a relatively long value.
2. Create a backing image:
3. Create 2 volumes with the backing image and attach them on different nodes. Verify: 
   - the disk state map of the backing image contains the disks of all replicas, and the state is running for all disks.
   - the backing image content is correct
4. Write random data to the volumes.
5. Power off 2 nodes. One node should contain one volume engine. Verify that
   - the related disk download state in the backing image will become `unknown`.
   - the volume on the running node still works fine but is state `Degraded`, and the content is correct in the volume.
   - the volume on the down node become `Unknown`.
6. Power on the 1st node. Verify
   - the failed replica of the `Degraded` volume can be reused.
   - the volume on the down node will be recovered automatically. And the data is correct.
   - the backing image will be recovered automatically.
   - the backing image file on this node will be reused when the related backing image manager pod is recovered (by check the pod log). 
7. Delete all volumes and the backing image. Verify the backing image manager can be deleted once forcing removing the related terminating pod. 

#### Available test backing image URLs:
```
https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw
https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img
https://github.com/rancher/k3os/releases/download/v0.11.0/k3os-amd64.iso 
```
