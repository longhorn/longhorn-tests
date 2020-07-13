---
title: "[#1366](https://github.com/longhorn/longhorn/issues/1366) && [#1328](https://github.com/longhorn/longhorn/issues/1328) The node the DR volume attached to is down/rebooted"
---
#### Scenario 1
1. Create a pod with Longhorn volume.
2. Write data to the volume and get the md5sum.
3. Create the 1st backup for the volume.
4. Create a DR volume from the backup.
5. Wait for the DR volume starting the initial restore. Then power off/reboot the DR volume attached node immediately.
6. Wait for the DR volume detached then reattached.
7. Wait for the DR volume restore complete after the reattachment.
8. Activate the DR volume and check the data md5sum.
#### Scenario 2
1. Create a pod with Longhorn volume.
2. Write data to the volume and get the md5sum.
3. Create the 1st backup for the volume.
4. Create a DR volume from the backup.
5. Wait for the DR volume to complete the initial restore. 
6. Write more data to the original volume and get the md5sum.
7. Create the 2nd backup for the volume.
8. Wait for the DR volume incremental restore getting triggered. Then power off/reboot the DR volume attached node immediately.
9. Wait for the DR volume detached then reattached.
10. Wait for the DR volume restore complete after the reattachment.
11. Activate the DR volume and check the data md5sum.
