---
title: BestEffort Recurring Job Cleanup
---
1. Set up a `BackupStore` anywhere (since the cleanup fails at the `Engine` level, any `BackupStore` can be used.
2. Add both of the `Engine Images` listed here:
- `quay.io/ttpcodes/longhorn-engine:no-cleanup` - `Snapshot` and `Backup` deletion are both set to return an error. If the `Snapshot` part of a `Backup` fails, that will error out first and `Backup` deletion will not be reached.
- `quay.io/ttpcodes/longhorn-engine:no-cleanup-backup` - Only `Backup` deletion is set to return an error. The `Snapshot` part of a `Backup` should succeed, and the `Backup` deletion will fail.

The next steps need to be repeated for each `Engine Image` (this is to test the code for `Snapshots` and `Backups` separately).

3. Create a `Volume` and run an `Engine Upgrade` to use one of the above images.
4. Attach the `Volume` and create a `Recurring Job` for testing. You can use a configuration that runs once every 3 minutes and only retains one `Backup`.
5. You should only see one `Snapshot` or `Backup` created per invocation.  Once enough `Backups` or `Snapshots` have been created and the `Job` attempts to delete the old ones, you will see something in the logs for the `Pod` for the `Job` similar to the following (as a result of using the provided `Engine Images` that do not have working `Snapshot` or `Backup` deletion:
```
time="2020-06-08T20:05:10Z" level=warning msg="created snapshot successfully but errored on cleanup for test: error deleting snapshot 'c-c3athc-fd3adb1e': Failed to execute: /var/lib/longhorn/engine-binaries/quay.io-ttpcodes-longhorn-engine-no-cleanup/longhorn [--url 10.42.0.188:10000 snapshot rm c-c3athc-fd3adb1e], output , stderr, time=\"2020-06-08T20:05:10Z\" level=fatal msg=\"stubbed snapshot deletion for testing\"\n, error exit status 1"
```

The `Job` should nonetheless run successfully according to `Kubernetes`. This can be verified by using `kubectl -n longhorn-system get jobs` to find the name of the `Recurring Job` and using `kubectl -n longhorn-system describe job <job-name>` to view the details, which should show that the `Jobs` ran successfully.
```
Events:
  Type    Reason            Age    From                Message
  ----    ------            ----   ----                -------
  Normal  SuccessfulCreate  4m50s  cronjob-controller  Created job test-c-yxam34-c-1591652160
  Normal  SawCompletedJob   4m10s  cronjob-controller  Saw completed job: test-c-yxam34-c-1591652160, status: Complete
  Normal  SuccessfulCreate  109s   cronjob-controller  Created job test-c-yxam34-c-1591652340
  Normal  SawCompletedJob   59s    cronjob-controller  Saw completed job: test-c-yxam34-c-1591652340, status: Complete
```

Additional invocations should not be attempted on that `Pod` that would result in multiple `Backups` or `Snapshots` being created at the same time.

Note that while the `Engine Images` being used to test this fix cause old `Backups`/`Snapshots` to not be deleted, even accounting for the extra `Backups` and `Snapshots`, you should not see multiple `Backups` being created at the same time. You should only see enough `Backups`/`Snapshots` that match the `Job` interval (since old `Backups` and `Snapshots` would not get deleted) without any extras.
