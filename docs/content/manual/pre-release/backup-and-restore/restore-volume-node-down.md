---
title: "[#1355](https://github.com/longhorn/longhorn/issues/1355) The node the restore volume attached to is down"
---
1. Create a backup.
2. Create a restore volume from the backup.
3. Power off the volume attached node during the restoring.
4. Wait for the Longhorn node down.
5. Wait for the restore volume being reattached and starting restoring volume with state `Degraded`.
6. Wait for the restore complete.
7. Attach the volume and verify the restored data.
8. Verify the volume works fine.
