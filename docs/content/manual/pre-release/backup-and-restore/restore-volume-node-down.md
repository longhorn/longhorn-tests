---
title: "[#1355](https://github.com/longhorn/longhorn/issues/1355) The node the restore volume attached to is down"
---

### Case 1:
1. Create a backup.
2. Restore the above backup.
3. Power off the volume attached node during the restoring.
4. Wait for the Longhorn node down.
5. Wait for the restore volume being reattached and starting restoring volume with state `Degraded`.
6. Wait for the restore complete.
7. Attach the volume and verify the restored data.
8. Verify the volume works fine.

### Case 2:
1. Repeat the steps from case 1 with an encrypted volume.
