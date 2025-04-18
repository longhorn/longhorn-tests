---
title: Checksum enabled large volume with multiple rebuilding
---

##### Related Issue:
- https://github.com/longhorn/longhorn/issues/4210

## Verify Large Volume Data Integrity During Replica Rebuilding with Recurring Jobs
   
1. Enable the setting `Snapshot Data Integrity` and `Immediate Snapshot Data Integrity Check After Creating a Snapshot`
1. Create a 50 Gi volume. write around 30 Gi data into it.
2. Create a recurring job of snapshot & backup.
3. Delete a replica and wait for the replica rebuilding.
4. Check volume data is intact

## Compare Large Volume Rebuild Performance Before and After Enabling Snapshot Integrity

1. Create a 50 Gi volume. write around 30 Gi data into it.
1. Fail one of the replica (node down or network partition) and wait for the replica becomes failed.
1. Power on node (or recover network)
1. Rebuilding (record rebuild time)
1. Enable `Snapshot Data Integrity` and `Immediate Snapshot Data Integrity Check After Creating a Snapshot`
1. Create a 50 Gi volume. write around 30 Gi data into it.
1. Take a snapshot
1. Wait for N minutes. Or check if the snapshot checksum file is generated
1. Fail one of the replica (node down or network partition) and wait for the replica becomes failed.
1. Power on node (or recover network)
1. Rebuilding (expect faster than without the two settings enabled)