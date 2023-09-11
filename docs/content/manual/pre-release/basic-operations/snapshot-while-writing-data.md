---
title: Snapshot while writing data in the volume
---
## Related issue:
https://github.com/longhorn/longhorn/issues/2187

## Scenario
1. Create a kubernetes pod + pvc that mounts a Longhorn volume.
2. Write 5 Gib into the pod using `dd if=/dev/urandom of=/mnt/<volume> count=5000 bs=1M conv=fsync status=progress`
3. While running the above command initiate a snapshot.
4. Verify the logs of the instance-manager using `kubetail instance-manager -n longhorn-system`. There should some logs related to freezing and unfreezing the filesystem. Like `Froze filesystem of volume mounted ...`
5. Verify snapshot succeeded and `dd` operation will complete.
6. Create another snapshot/backup and verify the data.

Note: The above issue is still open and the scenario will not work.
