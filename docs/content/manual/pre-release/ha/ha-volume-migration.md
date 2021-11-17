---
title: HA Volume Migration
---

1. Create a migratable volume:
    1. Deploy a migratable StorageClass. e.g., https://github.com/longhorn/longhorn/blob/master/examples/rwx/storageclass-migratable.yaml
    2. Create a PVC with access mode `ReadWriteMany` via this StorageClass.
2. Attach a volume to a node and wait for volume running. Then write some data into the volume. Here I would recommend directly restoring a volume (set `fromBackup` in the StorageClass) and attach it instead.
3. Start the migration by request attaching to another node for the volume.
4. Trigger the following scenarios then confirm or rollback the migration:

   --------------------------
   | **#** | **Scenario**          | **Migration Confirmation** | **Migration Rollback** |
   | ----- | --------------------- | -------------------------- | ---------------------- |
   | 1     | New engine crash      | If the request is successfully sent before the migration engine & replicas being removed, the volume should be auto reattached after migration. <br> Otherwise, the request will be rejected until the volume is reattached and restarts the migration components | Should succeed |
   | 2     | All new replica crash | If the request is successfully sent before the migration engine & replicas being removed, the volume should keep running (then may start rebuilding) after migration. <br> Otherwise, the request will be rejected until the volume is reattached and restarts the migration components | Should succeed |
   | 3     | Old engine crash      | If the request is successfully sent before the volume becoming Faulted, the volume should keep running after migration. <br> Otherwise, the request will be rejected until the volume is reattached and restarts the migration components | Should succeed |
   | 4     | All old replica crash | If the request is successfully sent before the volume becoming Faulted, the volume should keep running (then may start rebuilding) after migration. <br> Otherwise, the request will be rejected until the volume is reattached and restarts the migration components | Should succeed |
   | 5     | Degraded volume       | Should succeed | Should succeed |
   | 6     | One replica node down | Should succeed | Should succeed |
   | 7     | New engine node down  | The request should be rejected | Should succeed |
   | 8     | Old engine node down  | The request should be rejected | The request should be accepted. But the volume should keep state Unknown after the rollback since it's on a down node. |
   
   Note:
    1. Scenario 1-5 can be handled by integration test. But we need to manually test them before the the implementation.
    2. For Scenario 1-4, Longhorn may behave differently based on when the request is sent to the backend. To verify if there are race conditions, I would recommend repeating those cases multiple times. Please be aware that the timing of sending requests is important. You can choose different timing when you repeatedly test those cases. 
       For migration confirmation, as I mentioned above, the migration should succeed once the request is received before Longhorn updating the volume to an unavailable status. Otherwise, the request will be rejected until the auto recovery is done.
       For migration rollback, it's better to verify the rollback always works and won't affect the volume auto recovery no matter when the request is received. e.g., the request can be accepted while the volume is in detaching or attaching (both are parts of the auto reattachment flow).
    3. Migration confirmation/rollback success does not mean the volume should keep running. Instead, it means the volume won't be stuck in a buggy state and can be automatically recovered in the end. As for the exact expect behaviors, please follow the above table. 
5. Check if the volume works fine on the desired node after migration confirmation/rollback. And there is no extra process in instance manager pods.
   You can enter into the instance manager pods, list all engine/replicas processes, and verify if there is a corresponding engine/replica CR for each process. 
