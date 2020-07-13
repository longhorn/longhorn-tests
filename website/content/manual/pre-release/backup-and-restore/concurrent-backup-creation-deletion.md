---
title: "[#1326](https://github.com/longhorn/longhorn/issues/1326) concurrent backup creation & deletion"
---
This one is a special case, were the volume only contains 1 backup, which the user requests to delete while the user has another backup in progress. Previously the in progress backup would only be written to disk after it's completed while the delete request would trigger the GC which then detects that there is no backups left on the volume which would trigger the volume deletion.
- create vol `dak` and attach to the same node vol `bak` is attached
- connect to node via ssh and issue `dd if=/dev/urandom of=/dev/longhorn/dak status=progress`
- wait for a bunch of data to be written (1GB)
- take a backup(1)
- wait for a bunch of data to be written (1GB)
- take a backup(2)
- immediately request deletion of backup(1)
- verify that backup(2) completes succesfully
- verify that backup(1) has been deleted
- verify that all blocks mentioned in the backup(2).cfg file are present in the blocks directory.
