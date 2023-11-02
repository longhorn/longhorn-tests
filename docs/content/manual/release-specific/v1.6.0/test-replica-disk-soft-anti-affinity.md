---
title: Test Replica Disk Soft Anti-Affinity
---

## Related issue

https://github.com/longhorn/longhorn/issues/3823

## Test initial behavior of global Replica Disk Soft Anti-Affinity setting

**Given** A newly created Longhorn cluster

**Then** `Replica Zone Disk Anti-Affinity` shows as `false` in the UI

*And* the `replica-soft-anti-affinity` setting shows `false` with kubectl

## Test initial behavior of global Replica Disk Soft Anti-Affinity setting after upgrade

**Given** A newly upgraded Longhorn cluster

**Then** `Replica Zone Disk Anti-Affinity` shows as `false` in the UI

*And* the `replica-soft-anti-affinity` shows `false` with kubectl

## Test behavior of volume Replica Disk Soft Anti-Affinity setting

**Given** A newly created Longhorn cluster

**When** Create a volume

**Then** The UI shows `Replica Disk Soft Anti Affinity: ignored` on the volume details page

*And* `volume.spec.replicaDiskSoftAntiAffinity` shows `ignored` with kubectl

**When** The `Update Replica Disk Soft Anti Affinity` operation is used on the UI volume details page to change `Replica
Disk Soft Anti-Affinity` to `enabled`

**Then** The UI shows `Replica Disk Soft Anti Affinity: enabled` on the volume details page

*And* `volume.spec.replicaDiskSoftAntiAffinity` shows `enabled` with kubectl

**When** The `Update Replica Disk Soft Anti Affinity` batch operation is used on the UI volumes page to change `Replica
Disk Soft Anti-Affinity` to `disabled`

**Then** The UI shows `Replica Disk Soft Anti Affinity: disabled` on the volume details page

*And* `volume.spec.replicaDiskSoftAntiAffinity` shows `disabled` with kubectl

## Test initial behavior of volume Replica Disk Soft Anti-Affinity setting after upgrade

**Given** An outdated Longhorn cluster with at least one volume

**When** The cluster is upgraded

**Then** The UI shows `Replica Disk Soft Anti Affinity: ignored` on the volume details page

*And* `volume.spec.replicaDiskSoftAntiAffinity` shows `ignored` with kubectl

## Test effect of Replica Disk Soft Anti-Affinity on replica scheduling

If an implementation of test_global_disk_soft_anti_affinity hasn't merged, follow its skeleton manually

If an implementation of test_volume_disk_soft_anti_affinity hasn't merged, follow its skeleton manually
