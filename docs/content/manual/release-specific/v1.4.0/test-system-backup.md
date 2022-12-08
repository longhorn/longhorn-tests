---
title: Test Longhorn system backup should sync from the remote backup target
---

## Steps

**Given** Custom resource SystemBackup (foo) exist in AWS S3,

*And* System backup (foo) downloaded from AWS S3. 

*And* Custom resource SystemBackup (foo) deleted.

**When** Upload the system backup (foo) to AWS S3.

*And* Create a new custom resource SystemBackup(foo).
> This needs to be done before the system backup gets synced to the cluster.

**Then** Should see the synced messages in the custom resource SystemBackup(foo).
```
Events:
  Type    Reason   Age    From                               Message
  ----    ------   ----   ----                               -------
  Normal  Syncing  9m29s  longhorn-system-backup-controller  Syncing system backup from backup target
  Normal  Synced   9m28s  longhorn-system-backup-controller  Synced system backup from backup target
```
