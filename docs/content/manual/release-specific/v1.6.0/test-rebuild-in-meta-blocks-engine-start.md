---
title: Test `Rebuild` in volume.meta blocks engine start
---

## Related issue
https://github.com/longhorn/longhorn/issues/6626

## Test with patched image

**Given** a patched longhorn-engine image with the following code change.
```diff
diff --git a/pkg/sync/sync.go b/pkg/sync/sync.go
index b48ddd46..c4523f11 100644
--- a/pkg/sync/sync.go
+++ b/pkg/sync/sync.go
@@ -534,9 +534,9 @@ func (t *Task) reloadAndVerify(address, instanceName string, repClient *replicaC
                return err
        }

-       if err := repClient.SetRebuilding(false); err != nil {
-               return err
-       }
+       // if err := repClient.SetRebuilding(false); err != nil {
+       //      return err
+       // }
        return nil
 }
```
**And** a patched longhorn-instance-manager image with the longhorn-engine vendor updated.  
**And** Longhorn is installed with the patched images.  
**And** the `data-locality` setting is set to `disabled`.  
**And** the `auto-salvage` setting is set to `true`.  
**And** a new StorageClass is created with `NumberOfReplica` set to `1`.  
**And** a StatefulSet is created with `Replica` set to `1`.  
**And** the node of the StatefulSet Pod and the node of its volume Replica are different. This is necessary to trigger the rebuilding in reponse to the data locality setting update later.  
**And** Volume have 1 running Replica.  
**And** data exists in the volume.  

**When** the `data-locality` setting is set to `best-effort`.  
**And** the replica rebuilding is completed.  
**And** the `Rebuilding` in the replicas's `volume.meta` file is `true`.  
**And** Delete the instance manager Pod of the Replica.  

**Then** the Replica should be running.  
**And** the StatefulSet Pod should restart.  
**And** the `Rebuilding` in replicas's `volume.meta` file should be `false`.  
**And** the data should remain intact.
