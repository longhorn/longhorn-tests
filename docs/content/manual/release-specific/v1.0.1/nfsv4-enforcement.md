---
title: NFSv4 Enforcement (No NFSv3 Fallback)
---
Since the client falling back to `NFSv3` usually results in a failure to mount the `NFS` share, the way we can check for `NFSv3` fallback is to check the error message returned and see if it mentions `rpc.statd`, since dependencies on `rpc.statd` and other services are no longer needed for `NFSv4`, but are needed for `NFSv3`. The `NFS` mount **should not** fall back to `NFSv3` and instead only give the user a warning that the server may be `NFSv3`:
1. Modify `nfs-backupstore.yaml` from `deploy/backupstores/` in the `longhorn` repository such that it includes the following environment variable (this will force the server to only support `NFSv3`):
```yaml
name: PROTOCOLS
value: "3"
```
2. Create the `Backup Store` using `nfs-backupstore.yaml`.
3. Set the `Backup Target` in the `longhorn-ui` to `nfs://longhorn-test-nfs-svc.default:/opt/backupstore`.
4. Attempt to list the `Backup Volumes` in the `longhorn-ui`. You should get an error that resembles the following:
```
error listing backups: error listing backup volumes: Failed to execute: /var/lib/longhorn/engine-binaries/quay.io-ttpcodes-longhorn-engine-nfs4/longhorn [backup ls --volume-only nfs://longhorn-test-nfs-svc.default:/opt/backupstore], output Cannot mount nfs longhorn-test-nfs-svc.default:/opt/backupstore: nfsv4 mount failed but nfsv3 mount succeeded, may be due to server only supporting nfsv3: Failed to execute: mount [-t nfs4 -o nfsvers=4.2 longhorn-test-nfs-svc.default:/opt/backupstore /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/backupstore], output mount.nfs4: mounting longhorn-test-nfs-svc.default:/opt/backupstore failed, reason given by server: No such file or directory , error exit status 32 , stderr, time="2020-07-09T20:05:44Z" level=error msg="Cannot mount nfs longhorn-test-nfs-svc.default:/opt/backupstore: nfsv4 mount failed but nfsv3 mount succeeded, may be due to server only supporting nfsv3: Failed to execute: mount [-t nfs4 -o nfsvers=4.2 longhorn-test-nfs-svc.default:/opt/backupstore /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/backupstore], output mount.nfs4: mounting longhorn-test-nfs-svc.default:/opt/backupstore failed, reason given by server: No such file or directory\n, error exit status 32" , error exit status 1
```
This indicates that the mount failed on `NFSv4` and did not attempt to fall back to `NFSv3` since there's no mention of `rpc.statd`. However, the server **did** detect that the problem may have been the result of `NFSv3` as mentioned in this error log.

If the `NFS` mount attempted to fall back to `NFSv3`, you should see an error similar to the following:
```
error listing backups: error listing backup volumes: Failed to execute: /var/lib/longhorn/engine-binaries/longhornio-longhorn-engine-master/longhorn [backup ls --volume-only nfs://longhorn-test-nfs-svc.default:/opt/backupstore], output Cannot mount nfs longhorn-test-nfs-svc.default:/opt/backupstore: Failed to execute: mount [-t nfs4 longhorn-test-nfs-svc.default:/opt/backupstore /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/backupstore], output /usr/sbin/start-statd: 23: /usr/sbin/start-statd: systemctl: not found mount.nfs4: rpc.statd is not running but is required for remote locking. mount.nfs4: Either use '-o nolock' to keep locks local, or start statd. , error exit status 32 , stderr, time="2020-07-02T23:13:33Z" level=error msg="Cannot mount nfs longhorn-test-nfs-svc.default:/opt/backupstore: Failed to execute: mount [-t nfs4 longhorn-test-nfs-svc.default:/opt/backupstore /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/backupstore], output /usr/sbin/start-statd: 23: /usr/sbin/start-statd: systemctl: not found\nmount.nfs4: rpc.statd is not running but is required for remote locking.\nmount.nfs4: Either use '-o nolock' to keep locks local, or start statd.\n, error exit status 32" , error exit status 1
```
This error mentions `rpc.statd` and indicates a fallback to `NFSv3`.

Additionally, we need to test and make sure that the `NFSv3` warning only occurs when `NFSv3` may have been involved:
1. Set up the `NFS Backup Store` normally using `nfs-backupstore.yaml`. Do **not** make the changes to `nfs-backupstore.yaml` that I described above. This will create an `NFS` server that only supports `NFSv4`.
2. Set the `Backup Target` in the `longhorn-ui` to a non-exported `NFS` share, such as `nfs://longhorn-test-nfs-svc.default:/opt/test` (I set it to `test` because the correct directory is supposed to be `backupstore`).
3. Attempt to list the Backup Volumes in the longhorn-ui. You should get an `error` that resembles the following:
```
error listing backups: error listing backup volumes: Failed to execute: /var/lib/longhorn/engine-binaries/quay.io-ttpcodes-longhorn-engine-nfs4/longhorn [backup ls --volume-only nfs://longhorn-test-nfs-svc.default:/opt/test], output Cannot mount nfs longhorn-test-nfs-svc.default:/opt/test: Failed to execute: mount [-t nfs4 -o nfsvers=4.2 longhorn-test-nfs-svc.default:/opt/test /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/test], output mount.nfs4: mounting longhorn-test-nfs-svc.default:/opt/test failed, reason given by server: No such file or directory , error exit status 32 , stderr, time="2020-07-09T20:09:21Z" level=error msg="Cannot mount nfs longhorn-test-nfs-svc.default:/opt/test: Failed to execute: mount [-t nfs4 -o nfsvers=4.2 longhorn-test-nfs-svc.default:/opt/test /var/lib/longhorn-backupstore-mounts/longhorn-test-nfs-svc_default/opt/test], output mount.nfs4: mounting longhorn-test-nfs-svc.default:/opt/test failed, reason given by server: No such file or directory\n, error exit status 32" , error exit status 1
```
You should **not** see any mention of `NFSv3` in this case.
