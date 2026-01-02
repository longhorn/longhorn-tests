---
title: Test migration when there is engine or replica unavailable
---

## Related issue
https://github.com/longhorn/longhorn/issues/11397

## Test

**Given** Create a v1 Longhorn volume
```yaml
apiVersion: longhorn.io/v1beta2
kind: Volume
metadata:
  labels:
    backup-target: default
    longhornvolume: vol
    recurring-job-group.longhorn.io/default: enabled
    setting.longhorn.io/remove-snapshots-during-filesystem-trim: ignored
    setting.longhorn.io/replica-auto-balance: ignored
    setting.longhorn.io/snapshot-data-integrity: ignored
  name: vol
  namespace: longhorn-system
spec:
  accessMode: rwx
  backingImage: ""
  backupCompressionMethod: lz4
  backupTargetName: default
  dataEngine: v1
  dataLocality: disabled
  dataSource: ""
  disableFrontend: false
  diskSelector: []
  encrypted: false
  freezeFilesystemForSnapshot: ignored
  fromBackup: ""
  frontend: blockdev
  image: longhornio/longhorn-engine:master-head
  lastAttachedBy: ""
  migratable: true
  migrationNodeID: ""
  nodeID: ""
  nodeSelector: []
  numberOfReplicas: 3
  replicaAutoBalance: ignored
  replicaDiskSoftAntiAffinity: ignored
  replicaSoftAntiAffinity: ignored
  replicaZoneSoftAntiAffinity: ignored
  restoreVolumeRecurringJob: ignored
  revisionCounterDisabled: false
  size: "5368709120"
  snapshotDataIntegrity: ignored
  snapshotMaxCount: 250
  snapshotMaxSize: "0"
  staleReplicaTimeout: 2880
  unmapMarkSnapChainRemoved: ignored
```

**And** Attach the volume to a node with `<Original Node ID>`
```yaml
apiVersion: longhorn.io/v1beta2
kind: VolumeAttachment
metadata:
  labels:
    longhornvolume: vol
  name: vol
  namespace: longhorn-system
spec:
  attachmentTickets:
    longhorn-before-migration:
      generation: 0
      id: longhorn-before-migration
      nodeID: <Original Node ID>
      parameters:
        disableFrontend: "false"
        lastAttachedBy: ""
      type: csi-attacher
  volume: vol
```

**And** Start migration to `<New Node ID>`
```yaml
apiVersion: longhorn.io/v1beta2
kind: VolumeAttachment
metadata:
  labels:
    longhornvolume: vol
  name: vol
  namespace: longhorn-system
spec:
  attachmentTickets:
    longhorn-before-migration:
      generation: 0
      id: longhorn-before-migration
      nodeID: <Original Node ID>
      parameters:
        disableFrontend: "false"
        lastAttachedBy: ""
      type: csi-attacher
    longhorn-after-migration:
      generation: 0
      id: longhorn-after-migration
      nodeID: <Migration Node ID>
      parameters:
        disableFrontend: "false"
        lastAttachedBy: ""
      type: csi-attacher
  volume: vol
```

**And** Cordon the migration destination node `<New Node ID>`
```bash
kubectl cordon <New Node ID>
```

**And** Invalidate the engine image binary inside the instance manager pod on the migration node `<New Node ID>` for a while 
```bash
rm -rf /host/var/lib/longhorn/engine-binaries/*
touch /host/var/lib/longhorn/engine-binaries/longhornio-longhorn-engine-master-head
```

**And** Crash the replica process and the engine process in the instance manager pod and wait a while

**When** Remove the invalid file that occupies the engine image binary path, and uncordon the node
```bash
rm /host/var/lib/longhorn/engine-binaries/longhornio-longhorn-engine-master-head
kubectl uncordon <New Node ID>
```

**Then** Verify that the below message cannot be found in log of the longhorn-manager pod that owns the volume engine. And no new replica is created or started.
```
level=warning msg="The current available migration replicas do not match the record in the migration engine status, will restart the migration engine then update the replica map"
```

**When** Create an extra migration replica manually by copying an existing migration replica YAML and changing its name with a random string. 

**Then** Verify that the migration engine will be restarted and the extra replica will be removed.

**When** Confirm the migration by deleting ticket `longhorn-before-migration` in the longhorn volume attachment

**Then** Verify the migrated volume is healthy and works fine on the new node `<New Node ID>`