---
title: Test Volume Replica Zone Soft Anti-Affinity Setting
---

## Related issue
https://github.com/longhorn/longhorn/issues/5358

## Test step - Enable Volume Replica Zone Soft Anti-Affinity Setting

**Given** EKS Cluster with 3 nodes across 2 AWS zones (zone#1, zone#2)

*And* Deploy Longhorn v1.5.0

*And* Disable global replica zone anti-affinity

*And* Create a volume with 2 replicas, `replicaZoneSoftAntiAffinity=enabled` and attach it to a node.

**When** Scale volume replicas to 3

**Then** New replica should be scheduled

*And* No error messages in the longhorn manager pod logs.

*And* Volumes function correctly.


## Test step - Disable Volume Replica Zone Soft Anti-Affinity Setting

**Given** EKS Cluster with 3 nodes across 2 AWS zones (zone#1, zone#2)

*And* Deploy Longhorn v1.5.0

*And* Enable global replica zone anti-affinity

*And* Create a volume with 2 replicas, `replicaZoneSoftAntiAffinity=disabled` and attach it to a node.

**When** Scale volume replicas to 3

**Then** New replica should not be scheduled

**When** Update the Volume to `replicaZoneSoftAntiAffinity=enabled`

**Then** New replica should be scheduled

*And* No error messages in the longhorn manager pod logs.

*And* Volumes function correctly.
