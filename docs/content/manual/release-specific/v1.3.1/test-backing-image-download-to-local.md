---
title: Test transient error in engine status during eviction
---

### Test step
1. Create and attach a multi-replica volume.
2. Prepare one extra disk for a node that contains at least one volume replica.
3. Keep monitoring the engine YAML. e.g., `watch -n  "kubectl -n longhorn-system get lhe <engine name>"`.
4. Evicting the old disk for node. => Verify that there is no transient error in engine Status during eviction. A counter example is like:
```
apiVersion: longhorn.io/v1beta2
kind: Engine
metadata:
  creationTimestamp: "2022-07-27T04:46:03Z"
  finalizers:
  - longhorn.io
  generation: 4
  labels:
    longhornnode: shuo-k8s-worker-1
    longhornvolume: vol1
  name: vol1-e-998b62c7
  namespace: longhorn-system
  ownerReferences:
  - apiVersion: longhorn.io/v1beta2
    kind: Volume
    name: vol1
    uid: fe656464-78af-4abf-8068-0742ba247fef
  resourceVersion: "34220387"
  uid: f6a339e2-d606-479f-910f-c787f9efa906
spec:
  active: true
  backupVolume: ""
  desireState: running
  disableFrontend: false
  engineImage: longhornio/longhorn-engine:master-head
  frontend: blockdev
  logRequested: false
  nodeID: shuo-k8s-worker-1
  replicaAddressMap:
    vol1-r-769e039f: 10.42.4.30:10000
    vol1-r-56144d78: 10.42.2.81:10000
    vol1-r-8724804e: 10.42.1.59:10000
  requestedBackupRestore: ""
  requestedDataSource: ""
  revisionCounterDisabled: false
  salvageRequested: false
  upgradedReplicaAddressMap: {}
  volumeName: vol1
  volumeSize: "1073741824"
status:
  backupStatus: null
  cloneStatus:
    tcp://10.42.1.59:10000:
      error: ""
      fromReplicaAddress: ""
      isCloning: false
      progress: 0
      snapshotName: ""
      state: ""
    tcp://10.42.2.81:10000:
      error: ""
      fromReplicaAddress: ""
      isCloning: false
      progress: 0
      snapshotName: ""
      state: ""
    tcp://10.42.4.30:10000:
      error: ""
      fromReplicaAddress: ""
      isCloning: false
      progress: 0
      snapshotName: ""
      state: ""
    tcp://10.42.4.30:10015:
      error: 'failed to get snapshot clone status of tcp://10.42.4.30:10015: failed
        to get snapshot clone status: rpc error: code = Unavailable desc = all SubConns
        are in TransientFailure, latest connection error: connection error: desc =
        "transport: Error while dialing dial tcp 10.42.4.30:10017: connect: connection
        refused"'
      fromReplicaAddress: ""
      isCloning: false
      progress: 0
      snapshotName: ""
      state: ""
  currentImage: longhornio/longhorn-engine:master-head
  currentReplicaAddressMap:
    vol1-r-769e039f: 10.42.4.30:10000
    vol1-r-56144d78: 10.42.2.81:10000
    vol1-r-8724804e: 10.42.1.59:10000
  currentSize: "1073741824"
  currentState: running
  endpoint: /dev/longhorn/vol1
  instanceManagerName: instance-manager-e-3bdc3f00
  ip: 10.42.4.31
  isExpanding: false
  lastExpansionError: ""
  lastExpansionFailedAt: ""
  lastRestoredBackup: ""
  logFetched: false
  ownerID: shuo-k8s-worker-1
  port: 10001
  purgeStatus:
    tcp://10.42.1.59:10000:
      error: ""
      isPurging: false
      progress: 0
      state: ""
    tcp://10.42.2.81:10000:
      error: ""
      isPurging: false
      progress: 0
      state: ""
    tcp://10.42.4.30:10000:
      error: ""
      isPurging: false
      progress: 0
      state: ""
    tcp://10.42.4.30:10015:
      error: ""
      isPurging: false
      progress: 0
      state: ""
  rebuildStatus: {}
  replicaModeMap:
    vol1-r-769e039f: RW
    vol1-r-47418d68: RW
    vol1-r-56144d78: RW
    vol1-r-8724804e: RW
  restoreStatus:
    tcp://10.42.1.59:10000:
      backupURL: ""
      currentRestoringBackup: ""
      isRestoring: false
      lastRestored: ""
      state: ""
    tcp://10.42.2.81:10000:
      backupURL: ""
      currentRestoringBackup: ""
      isRestoring: false
      lastRestored: ""
      state: ""
    tcp://10.42.4.30:10000:
      backupURL: ""
      currentRestoringBackup: ""
      isRestoring: false
      lastRestored: ""
      state: ""
    tcp://10.42.4.30:10015:
      backupURL: ""
      currentRestoringBackup: ""
      error: 'Failed to get restoring status on tcp://10.42.4.30:10015: failed to
        get restore status: rpc error: code = Unavailable desc = all SubConns are
        in TransientFailure, latest connection error: connection error: desc = "transport:
        Error while dialing dial tcp 10.42.4.30:10017: connect: connection refused"'
      isRestoring: false
      lastRestored: ""
      state: ""
  salvageExecuted: false
  snapshots:
    35491870-d26d-4083-abf5-8fe36453eaec:
      children:
        volume-head: true
      created: "2022-07-27T04:50:53Z"
      labels: {}
      name: 35491870-d26d-4083-abf5-8fe36453eaec
      parent: ""
      removed: false
      size: "0"
      usercreated: false
    volume-head:
      children: {}
      created: "2022-07-27T04:50:53Z"
      labels: {}
      name: volume-head
      parent: 35491870-d26d-4083-abf5-8fe36453eaec
      removed: false
      size: "0"
      usercreated: false
  snapshotsError: ""
  started: true
  storageIP: 10.42.4.31
```


---
GitHub Issue: https://github.com/longhorn/longhorn/issues/4294