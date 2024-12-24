---
title: Delete Backup Asynchronously
---

## Related issues

- https://github.com/longhorn/longhorn/issues/8746

## LEP

- https://github.com/longhorn/longhorn/pull/9152

## Test Normal Case (use nfs)

**Given** Longhorn cluster with 3 worker nodes.

**And** Create a volume and attach it.

**And** Write large data to the volume.

**And** Create the first backup from the volume.

**And** Write small data to the volume.

**And** Create a snapshot.

**Then** Delete the first backup and create second backup from the snapshot at the same time.

**Verify** The second backup will be in `Pending` state with message including `waiting for backup to be deleted`.

**Verify** After the first backup is deleted, second backup should be in progress and complete in the end.


## Test Backup Delete Error Case (use nfs)

**Given** Longhorn cluster with 3 worker nodes.

**And** Create a volume and attach it.

**And** Write large data to the volume.

**And** Create the first backup from the volume.

**And** Write small data to the volume.

**And** Create a snapshot.

**And** Connect to the backupstore pod and make the backup.cfg file immutable by running the command `$ chattr +i backups/backup_backup-*.cfg`.

**Then** Delete the first backup and create second backup from the snapshot at the same time.

**Verify** The first backup will repeatedly enter the `Deleting` and `Error` states as it attempts to retry the deletion. When in the Error state, an error message related to permissions will be displayed.

**Verify** The second backup will be `InProgress` when the first backup is in `Error` state. The second backup should be complete after awhile.

**Verify** After make the config mutable by running the command `$ chattr -i backups/backup_backup-*.cfg`, after a while, the second backup should be in `Deleting` again and should be deleted successfully.


## Test Controller Crashes Case (use nfs)

**Given** Longhorn cluster with 3 worker nodes.

**And** Create a volume and attach it.

**And** Write large data to the volume.

**And** Create the first backup from the volume.

**And** Connect to the backupstore pod and make the backup.cfg file immutable by running the command `$ chattr +i backups/backup_backup-*.cfg`.

**Then** Delete the first backup.

**Verify** The first backup will repeatedly enter the `Deleting` and `Error` states as it attempts to retry the deletion. When in the Error state, an error message related to permissions will be displayed.

**Then** When the backup is in `Deleting` state, delete the longhorn-manager pod which is the owner of the backup. (by checking `Backup.Status.OwnerID`)

**Verify** After the longhorn manager pod is recreated, the backup should turn into `Error` state with message `No deletion in progress record, retry the deletion command`.

**Then** Make the config mutable by running the command `$ chattr -i backups/backup_backup-*.cfg`.

**Verify** The backup should be in `Deleting` again and should be deleted successfully.