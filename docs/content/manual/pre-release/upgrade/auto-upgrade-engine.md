---
title: Automatically Upgrading Longhorn Engine Test
---
<h4>Longhorn version >= 1.1.1 </h4>

[Reference ticket 2152](https://github.com/longhorn/longhorn/issues/2152)


### Test basic upgrade
1. Install old Longhorn version. E.g., <= `v1.0.2`
1. Create a volume, attach it to a pod, write some data. Create a DR volume and leave it in the detached state.
1. Upgrade to Longhorn master
1. Set setting `concurrent automatic engine upgrade per node limit` to 3
1. Verify that volumes' engines are upgraded automatically.

### Test concurrent upgrade
1. Create a StatefulSet of scale 10 using 10 Longhorn volume. Set node selector so that all pods land on the same node.
2. Upgrade Longhorn to use a newer default engine image
3. In Longhorn UI and Longhorn manager logs, Verify that Longhorn doesn't upgrade all volumes at the same time. Only 3 at a time.
4. In Longhorn UI, while the concurrent value is set to limit 1, change the value to higher number and verify if the upgrade is happening as per the new value.
5. Create stateful set pods with volume claim template, set the scale to 10 and in the configure options, select RWO and RWX. Verify the volumes created have RWX set as RWX takes precedence.
6. While the auto upgrade is set, try to manually upgrade the image engine to the latest version. The manual upgrade should work and the image should be upgraded to the default version.
7. Take backup for a volume when upgrade hasn't started.
8. Create 10 volumes and set concurrent upgrade limit to 2. When the upgrade starts, delete all the volumes. [Volumes are deleted and Longhorn UI is not corrupted.
9. Deploy a workload with rwx scale 10 with persistent volume claim template and verify the volume created can be used for all of 10 pods.
10. While upgrade is in progress, detach the volume from node and verify the detached volume is upgraded.
  
### Test degraded volume
1. Verify that Longhorn doesn't upgrade engine image for degraded volume.
2. While the upgrade is happening, make a volume degraded and verify if the upgrade still happen.

### Test DR volume
1. Verify that Longhorn doesn't upgrade engine image for DR volume.

### Test expanding volume
1. Verify that Longhorn doesn't upgrade engine image for volume which is expanding.
