---
title: Multiple Backup Stores
---

## Related issues

- https://github.com/longhorn/longhorn/issues/5411

## LEP

- https://github.com/longhorn/longhorn/pull/6630

## Test Update Default Backup Target

**Given** Longhorn cluster with 3 worker nodes installed with Helm.

**Verify** The `ConfigMap` `longhorn-default-backupstore` is created.

**Then** Update the setting `defaultBackupStore.backupTarget` in the file `values.yaml`.

**Verify** The default backup target URL is updated as the value of the setting `defaultBackupStore.backupTarget`.

**Then** Update the setting `defaultBackupStore.backupTargetCredentialSecret` in the file `values.yaml`.

**Verify** The default backup target secret is updated as the value of the setting `defaultBackupStore.backupTargetCredentialSecret`.

**Then** Update the setting `defaultBackupStore.pollInterval` in the file `values.yaml`.

**Verify** The default backup target poll interval is updated as the value of the setting `defaultBackupStore.pollInterval`.

## Test Create A Volume By A Storage Class For The Parameter `backupTargetName`

**Given** Longhorn cluster with 3 worker nodes.

**And** Create a Storage Class A without the parameter `backupTargetName`.

**And** Create a Storage Class B with the parameter `backupTargetName: backupTargetB` (the backup target `backupTargetB` is created.)

**And** Create a Storage Class C with the parameter `backupTargetName: backupTargetC` (the backup target `backupTargetC` is not created.)

**Then** Create a volume A with the Storage Class A.

**Verify** The field `spec.backupTargetName` of volume A is `default`.

**Then** Create a volume B with the Storage Class B.

**Verify** The field `spec.backupTargetName` of volume B is `backupTargetB`.

**Then** Create a volume C with the Storage Class C.

**Verify** The volume C can not be created.

## Test Create And Restore A Backup With Multiple Backup Targets

**Given** Longhorn cluster with 3 worker nodes.

**And** Set up the default backup target.

**And** Create a volume and attach it.

**And** Write data to the volume.

**Then** Create an extra backup target A which has existing backups.

**Verify** Existing backups on the extra backup target A can be synchronized back to the cluster.

**Then** Create a backup D to the default backup target.

**Verify** The backup D is completed and backups of the default backup target will not be deleted.

**Then** Create a backup A to extra backup target A (by setting the `Spec.BackupTargetName` field in the volume first.)

**Verify** The backup A is completed and existing backups of backup target A will not be deleted.

**Then** Restore the backup D from the default backup target.

**Then** Restore the backup A from the extra backup target A.

**Verify** Restoring the backup D is completed and data is correct.

**Verify** Restoring the backup A is completed and data is correct.

## Test Modify The Backup Target URL

**Given** Longhorn cluster with 3 worker nodes

**And** Set up the default backup target

**Then** Set up an extra backup target A which has existing backups

**Verify** Existing backups on the extra backup target A can be synchronized back to the cluster

**Then** Modify the extra backup target A URL to another valid URL of backup target B

**Verify** Related backup volume and backup custom resources will be synchronized correctly from the remote backup target B.

**Then** Modify the extra backup target A URL to an invalid URL.

**Verify** The extra backup target A become unavailable and synchronization will be skipped.

**Verify** Related backup volume and backup custom resources of the backup target B will not be cleaned up.

**Then** Empty the extra backup target A URL

**Verify** related backup volume and backup custom resources of the backup target B will be cleaned up.

**Verify** Backup volume and backup custom resources of the default backup target will not be affected.

## Test Create And Restore A Backing Image

**Given** Longhorn cluster with 3 worker nodes.

**And** Create a backing image.

**And** Set up the default backup target

**And** Create a valid backup target A.

**Then** Create a backup D of the backing image to the default backup target.

**Verify** The backup D of the backing image is completed.

**Then** Create a backup A of the backing image to the backup target A.

**Verify** The backup A of the backing image is completed.

**Then** Restore the backup D of the backing image from the default backup target.

**Verify** The restoration succeeds and data is correct.

**Then** Restore the backup A of the backing image from the backup target A.

**Verify** The restoration succeeds and data is correct.

## Test Create A DR Volume

**Given** Longhorn cluster A with 3 worker nodes and Longhorn cluster B with 3 worker nodes.

**And** Set up the default backup target with the same remote backup store D for two clusters.

**And** Set up the backup target `E` with the same remote backup store S for two clusters.

**And** Create a volume A with the default backup target in cluster A and attach it.

**And** Create a volume B with the backup target `E` in cluster B and attach it.

**And** Write data to the volume A and B.

**Then** Create a backup A-01 of the volume A in the cluster A.

**Then** Create a DR volume B-DR after the backup A is synchronized in cluster B.

**Verify** DR volume B-DR is created and stand-by to synchronize data from cluster A.

**Verify** Modifying/Deleting the backup target URL is not allowed in cluster B.

**Then** Write data to the volume A and create a new backup A-02 in the cluster A.

**Verify** The DR volume will synchronize the data from the backup A-02 in the cluster B.

**Then** Activate the volume B-DR.

**Verify** data of the volume B-DR is the same to the volume A.

**Then** Create a backup B-01 of the volume B in the cluster B.

**Then** Create a DR volume A-DR after the backup B-01 is synchronized in the cluster A.

**Then** Write data to the volume B and create a new backup B-02 in the cluster B.

**Verify** Modifying/Deleting the backup target URL is not allowed in cluster A.

**Verify** The DR volume A-DR will synchronize the data in the cluster A.

## Test Create And Restore A System Backup

**Given** Longhorn cluster with 3 worker nodes.

**And** Set up the default backup target and an extra backup target A.

**And** Create a volume A with the default backup target and attach it.

**And** Create a volume B with the backup target `A` and attach it.

**And** Write data to the volume A and B.

**Then** Create a system backup.

**Verify The system backup is completed, and the system backup and the volume A is stored on the default backup target, and the volume B is stored on the backup target A.

**Then** Delete the backup target A and volume A and B.

**Then** Restore the system backup.

**Verify** Restoration is completed, and backup target A, volume A and B is restored.

## Test Delete A Backup Target

**Given** Longhorn cluster with 3 worker nodes.

**And** Set up the default backup target and an extra backup target A which has existing backups.

**Verify** Deleting the default backup target is not allowed.

**Verify** Existing backups on the extra backup target A can be synchronized back to the cluster.

**Then** Create a backup D to the default backup target.

**Verify** The backup D is completed.

**Then** Create a backup A to extra backup target A.

**Verify** The backup A is completed.

**Then** Delete the backup target A.

**Verify** Related backup volume and backup custom resources of the backup target A will be cleaned up.

**Verify** Backup volume and backup custom resources of the default backup target will not be affected.

**Then** Add the backup target A back.

**Verify** Related backup volume and backup custom resources of the backup target A will be synchronized correctly.

## Test Uninstall

**Given** Longhorn cluster with 3 worker nodes.

**And** Set up the default backup target and a backup target A.

**And** Create a volume A with the default backup target name

**And** Create a volume B with the backup target A name.

**Then** Create backups for the volume A and B, and wait for backups completion.

**Then** Uninstall Longhorn.

**Verify** URLs of backup targets are empty first.

**Verify** Backup targets are deleted successfully.

**Verify** Uninstall successfully.

## Test Upgrade

**Given** Longhorn v1.7.x cluster with 3 worker nodes.

**And** Set up the default backup target.

**And** Create a volume and attach it, and create a backup A of the volume A, and wait for the backup completed.

**And** Create a backing image BI, and create a backup BBI of the backing image BI, and wait for the backup completed.

**Then** Upgrade Longhorn to v1.8.0

**Verify** The `default` backup target will not be deleted.

**Verify** The settings `backup-target`, `backup-target-credential-secret`, and `backupstore-poll-interval` are removed from global settings.

**Verify** The fields `Spec.BackupTargetName` of the volume A is the default backup target name `default`.

**Verify** The field `Status.BackupTarget` and labels `backup-target` of the backup A is the default backup target name `default`.

**Verify** The fields `Spec.BackupTargetName` and labels `backup-target` of the backup volume A is the default backup target name `default`, and `Spec.VolumeName` of the backup volume A is the name of the volume A.

**Verify** The fields `Spec.BackupTargetName` and labels of the backing image BI is the default backup target name `default`, and `Spec.BackingImage` of the backup BBI is the name of the backing image BI.
