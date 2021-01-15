---
title: Test Snapshot Purge Error Handling
---

## Related issue
https://github.com/longhorn/longhorn/issues/1895

Longhorn v1.1.1 handles the error during snapshot purge better and reports to Longhorn-manager.

## Scenario-1
1. Create a volume with 3 replicas and attach to a pod.
2. Write some data into the volume and take a snapshot.
3. Delete a replica that will result in creating a system generated snapshot.
4. Wait for replica to finish and take another snapshot.
5. ssh into a node and resize the latest snapshot. (e.g `dd if=/dev/urandom count=50 bs=1M of=<SNAPSHOT-NAME>.img`)
6. Trigger snapshot purge by delete the oldest snapshot.
7. Verify the replica (on the node from step 5) shows error `file sizes are not equal and the parent file is larger than the child file` and starts to rebuild.

## Scenario-2
1. Create a volume with 3 replicas and attach to a pod.
2. Write some data into the volume and take two snapshots.
3. Delete a replica that will result in creating a system generated snapshot.
4. While the rebuilding is in progress, delete a snapshot to trigger SnapshotPurge.
5. Verify that Longhorn manager reports error like `Failed to purge snapshots: REPLICA_ADDRESS: cannot purge snapshots because REPLICA_ADDRESS is rebuilding`
