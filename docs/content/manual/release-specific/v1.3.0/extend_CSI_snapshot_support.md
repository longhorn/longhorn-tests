---
title: Extended CSI snapshot support to Longhorn snapshot
---

## Related issue
https://github.com/longhorn/longhorn/issues/2534

## Test Setup

1. Deploy the CSI snapshot CRDs, Controller as instructed at https://longhorn.io/docs/1.2.3/snapshots-and-backups/csi-snapshot-support/enable-csi-snapshot-support/
2. Deploy 4 VolumeSnapshotClass:
    ```yaml
    kind: VolumeSnapshotClass
    apiVersion: snapshot.storage.k8s.io/v1beta1
    metadata:
      name: longhorn-backup-1
    driver: driver.longhorn.io
    deletionPolicy: Delete
    ```
    ```yaml
    kind: VolumeSnapshotClass
    apiVersion: snapshot.storage.k8s.io/v1beta1
    metadata:
      name: longhorn-backup-2
    driver: driver.longhorn.io
    deletionPolicy: Delete
    parameters:
      type: bak
    ```   
    ```yaml
    kind: VolumeSnapshotClass
    apiVersion: snapshot.storage.k8s.io/v1beta1
    metadata:
      name: longhorn-snapshot
    driver: driver.longhorn.io
    deletionPolicy: Delete
    parameters:
      type: snap
    ```
    ```yaml
    kind: VolumeSnapshotClass
    apiVersion: snapshot.storage.k8s.io/v1beta1
    metadata:
      name: invalid-class
    driver: driver.longhorn.io
    deletionPolicy: Delete
    parameters:
      type: invalid
    ```
3. Create Longhorn volume `test-vol` of 5GB. Create PV/PVC for the Longhorn volume.
4. Create a workload that uses the volume. Write some data to the volume.
   Make sure data persist to the volume by running `sync`
5. Set up a backup target for Longhorn

#### Scenarios 1: CreateSnapshot
  * `type` is `bak` or `""` 
    
    * Create a VolumeSnapshot with the following yaml
      ```yaml
      apiVersion: snapshot.storage.k8s.io/v1beta1
      kind: VolumeSnapshot
      metadata:
        name: test-snapshot-longhorn-backup
      spec:
        volumeSnapshotClassName: longhorn-backup-1
        source:
          persistentVolumeClaimName: test-vol
      ```
    * Verify that a backup is created.
    * Delete the `test-snapshot-longhorn-backup`
    * Verify that the backup is deleted
    * Create the `test-snapshot-longhorn-backup` VolumeSnapshot with `volumeSnapshotClassName: longhorn-backup-2`
    * Verify that a backup is created.
  * `type` is `snap`
    * volume is in detached state. 
      * Scale down the workload of `test-vol` to detach the volume.
      * Create `test-snapshot-longhorn-snapshot` VolumeSnapshot with `volumeSnapshotClassName: longhorn-snapshot`.
      * Verify the error `volume ... invalid state ... for taking snapshot` in the Longhorn CSI plugin.
    * volume is in attached state. 
      * Scale up the workload to attach `test-vol`
      * Verify that a Longhorn snapshot is created for the `test-vol`.
  * invalid type
    * Create `test-snapshot-invalid` VolumeSnapshot with `volumeSnapshotClassName: invalid-class`.
    * Verify the error `invalid snapshot type: %v. Must be %v or %v or` in the Longhorn CSI plugin.
    * Delete `test-snapshot-invalid` VolumeSnapshot.

#### Scenarios 2: Create new volume from CSI snapshot
  * From `longhorn-backup` type
    * Create a new PVC with the flowing yaml:
      ```yaml
      apiVersion: v1
      kind: PersistentVolumeClaim
      metadata:
        name: test-restore-pvc
      spec:
        storageClassName: longhorn
        dataSource:
          name: test-snapshot-longhorn-backup
          kind: VolumeSnapshot
          apiGroup: snapshot.storage.k8s.io
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 5Gi
      ```
    * Attach the PVC `test-restore-pvc` and verify the data 
    * Delete the PVC
  * From `longhorn-snapshot` type
    * Source volume is attached && Longhorn snapshot exist
        * Create a PVC with the following yaml:
          ```yaml
          apiVersion: v1
          kind: PersistentVolumeClaim
          metadata:
            name: test-restore-pvc
          spec:
            storageClassName: longhorn
            dataSource:
              name: test-snapshot-longhorn-snapshot
              kind: VolumeSnapshot
              apiGroup: snapshot.storage.k8s.io
            accessModes:
              - ReadWriteOnce
            resources:
              requests:
                storage: 5Gi
          ```
        * Attach the PVC `test-restore-pvc` and verify the data 
        * Delete the PVC
    * Source volume is detached
      * Scale down the workload to detach the `test-vol`
      * Create the same PVC `test-restore-pvc` as in the `Source volume is attached && Longhorn snapshot exist` section
      * Verify that PVC provisioning failed because the source volume is detached so Longhorn cannot verify the existence of the Longhorn snapshot in the source volume.
      * Scale up the workload to attache `test-vol`  
      * Wait for PVC to finish provisioning and be bounded
      * Attach the PVC `test-restore-pvc` and verify the data
      * Delete the PVC
    * Source volume is attached && Longhorn snapshot doesn’t  exist
      * Find the VolumeSnapshotContent of the VolumeSnapshot `test-snapshot-longhorn-snapshot`.
        Find the Longhorn snapshot name inside the field `VolumeSnapshotContent.snapshotHandle`.
        Go to Longhorn UI. Delete the Longhorn snapshot. Make sure that the snapshot is gone (the snapshot might still be there if it is the child of volume head. In this case you need to create a new snapshot before you can delete the target sanapshot )
      * Repeat steps in the section `Longhorn snapshot exist` above.
        PVC should be stuck in provisioning because Longhorn snapshot of the source volume doesn't exist.
      * Delete the PVC `test-restore-pvc` PVC
  
#### Scenarios 3: Delete CSI snapshot
  * `bak` type
    * Done in the above step
  * `snap` type
    * volume is attached && snapshot doesn’t exist
      * Delete the VolumeSnapshot `test-snapshot-longhorn-snapshot` and verify that the VolumeSnapshot is deleted.
    * volume is attached && snapshot exist
      * Recreate the VolumeSnapshot `test-snapshot-longhorn-snapshot`
      * Verify the creation of Longhorn snapshot with the name in the field `VolumeSnapshotContent.snapshotHandle`
      * Delete the VolumeSnapshot `test-snapshot-longhorn-snapshot` 
      * Verify that Longhorn snapshot is removed or marked as removed
      * Verify that the VolumeSnapshot `test-snapshot-longhorn-snapshot` is deleted.
    * volume is detached
      * Recreate the VolumeSnapshot `test-snapshot-longhorn-snapshot`
      * Scale down the workload to detach `test-vol`
      * Delete the VolumeSnapshot `test-snapshot-longhorn-snapshot`
      * Verify that VolumeSnapshot `test-snapshot-longhorn-snapshot` is stuck in deleting

#### Scenarios 4: Concurrent backup creation & deletion
  * From https://longhorn.github.io/longhorn-tests/manual/pre-release/backup-and-restore/concurrent-backup-creation-deletion/
  * `` and `bak` type
    * Use volume test-vol previous created
    * Connect to node via ssh and issue dd if=/dev/urandom of=/dev/longhorn/dak status=progress
    * Wait for a bunch of data to be written (1GB)
    * take a backup(1) by 
    ```yaml
      apiVersion: snapshot.storage.k8s.io/v1beta1
      kind: VolumeSnapshot
      metadata:
        name: test-snapshot-longhorn-backup1
      spec:
        volumeSnapshotClassName: longhorn-backup-1
        source:
          persistentVolumeClaimName: test-vol
      ```
    * wait for a bunch of data to be written (1GB)
    * take a backup(2) by 
    ```yaml
      apiVersion: snapshot.storage.k8s.io/v1beta1
      kind: VolumeSnapshot
      metadata:
        name: test-snapshot-longhorn-backup2
      spec:
        volumeSnapshotClassName: longhorn-backup-1
        source:
          persistentVolumeClaimName: test-vol
      ```
    * immediately request deletion of backup(1)
    * verify that backup(2) completes successfully.
    * verify that backup(1) has not been deleted.
    * verify that all blocks mentioned in the backup(2).cfg file are present in the blocks directory.
    * delete backup(1)
    * verify that backup(1) has been deleted.
    * Repeat previous use 'volumeSnapshotClassName: longhorn-backup-2' (bak)