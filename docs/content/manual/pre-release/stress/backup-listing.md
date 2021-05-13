---
title: "Test backup listing S3/NFS"
---

## 1. Backup listing with more than 1000 backups - S3
1. Deploy Longhorn on a kubernetes cluster.
2. Set up S3 backupStore.
3. Create a volume of 2Gi and attach it to a pod.
4. Write some data into it and compute md5sum.
5. Open browser developer tool.
6. Create one backup by clicking LH GUI (It'll call `snapshotCreate` and `snapshotBackup` APIs).
7. Copy the `snapshotBackup` API call, right click `Copy` -> `Copy as cURL`.
8. Run the curl command over 1k times in the Shell.
9. On LH GUI, click the Backup -> Volume Name to display total volume backups, you should see all the backup backups listed on the page.
10. Restore any backup and verify the data.

## 2. Backup listing with more than 1000 backups - NFS
1. Repeat the steps from test scenario `1. Backup listing with more than 1000 backups - S3` with NFS backupStore.

## 3. Backup listing of volume bigger than 200 Gi - S3
1. Deploy Longhorn on a kubernetes cluster.
2. Set up S3 backupStore.
3. Create a volume `vol-1` of 250Gi and attach it to a pod.
4. Write data of 240Gi.
5. Take a backup.
6. Go to the backup page and click on the volume `vol-1` to list the backups, you should see the backup getting listed.
7. Verify the size of data by restoring it.
8. Create another volume `vol-2` of 200Gi and attach it to a pod.
9. Write data of 150Gi.
10. Take a backup.
11. Go to the backup page, you should be able to see both the backups.
12. Click the volume `vol-2`, you should be able to see the backup.
13. Write 40Gi in the `vol-2`.
14. Take one more backup and verify the listing of the backup in the backup page.

**Note** - Use the same cluster from the test scenario-1 where 1k backups are already there to increase the stress on the system.

## 4. Backup listing of volume bigger than 200 Gi - NFS
1. Repeat steps from test scenario `3. Backup listing of volume more than 200 Gi - S3` with NFS backupStore.
