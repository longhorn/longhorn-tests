*** Settings ***
Documentation    Backup Test Cases

Test Tags    regression    backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backup_backing_image.resource
Resource    ../keywords/system_backup.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/node.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/host.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources without corrupting remote backupstore

*** Keywords ***
# Reset backup target from remote AWS S3 to local minio backup store before cleaning up resources
# to avoid deleting the existing backup on AWS S3
Cleanup test resources without corrupting remote backupstore
    Set default backupstore
    Cleanup test resources

Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks

Backup target could not be changed when DR volume exist
    Set setting backup-target to random.backup.target will fail

*** Test Cases ***
Test Backup During Active IO
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12140
    ...    Concurrent backup/restore during active I/O
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create pod 0 using volume 0
    And Wait for pod 0 running

    # active io in the background
    And Keep writing data to pod 0
    # write another file for data integrity check
    # this file won't be overwritten by the active io
    And Write 100 MB data to file data.txt in pod 0
    And Record file data.txt checksum in pod 0 as checksum 0
    And Create backup 0 for volume 0

    When Create volume 1 from backup 0 of volume 0
    And Wait for volume 1 restoration from backup 0 of volume 0 start
    And Wait for volume 1 detached
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    And Wait for pod 1 running
    Then Check pod 1 file data.txt checksum matches checksum 0

Test Backup Volume List
    [Documentation]    Test Backup Volume List
    ...    We want to make sure that an error when listing a single backup volume
    ...    does not stop us from listing all the other backup volumes. Otherwise a
    ...    single faulty backup can block the retrieval of all known backup volumes.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1 with    dataEngine=${DATA_ENGINE}
    And Attach volume 1
    And Wait for volume 1 healthy

    When Create backup 0 for volume 0
    And Create backup 1 for volume 1
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains no error for volume 1
    And Wait for backup 0 of volume 0 to exist in backup list
    And Wait for backup 1 of volume 1 to exist in backup list

    When Place file backup_1234@failure.cfg into the backups folder of volume 0
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains no error for volume 1
    And Wait for backup 0 of volume 0 to exist in backup list
    And Wait for backup 1 of volume 1 to exist in backup list

    And Delete backup volume 0
    And Delete backup volume 1

Test Incremental Restore
    [Tags]    dr-volume
    [Documentation]    Test restore from disaster recovery volume (incremental restore)
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    When Create DR volume 1 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 0 of volume 0 completed
    And Create DR volume 2 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
    And Wait for volume 2 restoration from backup 0 of volume 0 completed
    And Create DR volume 3 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
    And Wait for volume 3 restoration from backup 0 of volume 0 completed

    Then Create snapshot 0 of volume 1 will fail
    And Backup target could not be changed when DR volume exist

    When Activate DR volume 1
    And Attach volume 1
    And Wait for volume 1 healthy
    Then Check volume 1 data is backup 0 of volume 0


    When Write data 1 to volume 0
    And Create backup 1 for volume 0
    # Wait for DR volume 2 incremental restoration completed
    Then Wait for volume 2 restoration from backup 1 of volume 0 completed
    And Activate DR volume 2
    And Attach volume 2
    And Wait for volume 2 healthy
    And Check volume 2 data is backup 1 of volume 0

    When Write data 2 to volume 0
    And Create backup 2 for volume 0
    # Wait for DR volume 3 incremental restoration completed
    Then Wait for volume 3 restoration from backup 2 of volume 0 completed
    And Activate DR volume 3
    And Attach volume 3
    And Wait for volume 3 healthy
    And Check volume 3 data is backup 2 of volume 0
    And Detach volume 3
    And Wait for volume 3 detached

    When Create persistentvolume for volume 3
    And Create persistentvolumeclaim for volume 3
    And Create pod 0 using volume 3
    Then Wait for pod 0 running
    And Delete pod 0
    And Delete persistentvolumeclaim for volume 3
    And Delete persistentvolume for volume 3

Test Uninstallation With Backups
    [Tags]    uninstall
    [Documentation]    Test uninstall Longhorn with backups
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    Then Install Longhorn

Test Cleanup Snapshot With The Global Setting After Backup Completed
    [Tags]    snapshot
    [Documentation]    Test cleanup snapshot with the global setting after backup completed
    ...    Issue: https://github.com/longhorn/longhorn/issues/9213
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy

    When Write data 0 to volume 0
    And Create backup 0 for volume 0
    And Check snapshot for backup 0 of volume 0 exists True

    When Setting auto-cleanup-snapshot-after-on-demand-backup-completed is set to true
    And Write data 1 to volume 0
    And Create backup 1 for volume 0
    And Check snapshot for backup 1 of volume 0 exists False
    And Setting auto-cleanup-snapshot-after-on-demand-backup-completed is set to false

Test Backupstore With Existing Backups
    [Documentation]    https://github.com/longhorn/longhorn/issues/11337
    Given Reset default backupstore
    When Set backupstore url to s3://longhorn-test-backupstore@us-east-1/
    And Set backupstore secret to host-provider-cred-secret
    And Set backupstore poll interval to 30 seconds
    Then Wait for backupstore ready
    # the existing backup in the backup store is called test-backup
    And Wait for backup test-backup ready
    # backup backing image name will change every time it's synced by the remote backup store
    # it's impossible to validate it by a given name
    # https://github.com/longhorn/longhorn/issues/11355
    And Wait for backing image backup for backing image bi ready
    # the existing system backup in the backup store is called system-backup
    And Wait for system backup system-backup ready

Backup Older Snapshot When Newer Snapshot Backup Exists
    [Documentation]
    ...    This test verifies that a volume can successfully create a backup from
    ...    an older snapshot even after a newer snapshot had already been backed
    ...    up.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/11461
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Create snapshot 0 of volume 0
    And Write data to volume 0
    And Create snapshot 1 of volume 0
    And Validate snapshot 0 is parent of snapshot 1 in volume 0 snapshot list
    And Create backup 0 for volume 0    snapshot_id=1
    And Verify backup list contains no error for volume 0

    When Create backup 1 for volume 0    snapshot_id=0
    Then Verify backup list contains no error for volume 0

Test DR Volume Backup Block Size
    [Tags]    dr-volume
    [Documentation]
    ...    Verify the DR volume's backup block size should be always set from the latest backup.
    ...
    ...    https://github.com/longhorn/longhorn/issues/11580
    Given Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}    backupBlockSize=16Mi
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create backup 0 for volume 0

    When Create DR volume 1 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
    And DR volume 1 setting backupBlockSize should be 16Mi

SnapshotBack Proxy Request Should Be Sent To Correct Instance-Manager Pod
    [Documentation]
    ...    Verify snapshot backup goes to the correct instance-manager pod.
    ...
    ...    https://github.com/longhorn/longhorn/issues/12475
    # Limit the test scope to a single node
    [Setup]    Set up v2 test environment
    Given Set node 1 with    allowScheduling=false    evictionRequested=true
    And Set node 2 with    allowScheduling=false    evictionRequested=true
    And Delete node 1
    And Delete node 2

    And Create volume 0 with    dataEngine=v1   numberOfReplicas=1
    And Attach volume 0 to node 0
    And Write data 0 to volume 0
    And Create volume 1 with    dataEngine=v2   numberOfReplicas=1
    And Attach volume 1 to node 0
    And Write data 1 to volume 0

    When Get test start time
    And Create backup 0 for volume 0
    And Verify v1 instance manager log on node 0 contain backup after test start
    And Verify v2 instance manager log on node 0 not contain backup after test start
    Then Get test start time
    And Create backup 1 for volume 1
    And Verify v2 instance manager log on node 0 contain backup after test start
    And Verify v1 instance manager log on node 0 not contain backup after test start
    And Reboot node 1
    And Reboot node 2
    And Wait for longhorn ready

Test Corrupting Source Replica While Backup Creation
    [Documentation]    Verify that corrupting the source replica while a backup is in progress causes
    ...    a backup error, and that the volume recovers, and a subsequent backup
    ...    can be successfully restored with data integrity.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/6138#issuecomment-1708355748
    ...
    ...    Steps:
    ...    1. Create and attach a volume
    ...    2. Write some data to the volume
    ...    3. Create a backup for the volume without waiting for completion
    ...    4. Wait for the backup creation to be started (backup state == InProgress)
    ...    5. While backing creation is still in progress,
    ...       corrupt the backup's source replica to make the backup to be marked as Error
    ...       Since the source replica is randomly selected when creating backup,
    ...       e.g., backup.status.replicaAddress: tcp://10.42.2.16:20001,
    ...       the instance manager with IP 10.42.2.16 will be the source replica for this backup.
    ...       We can delete all the instance manager to simulate the source replica corruption.
    ...       This will cause the backup to be marked as Error.
    ...    6. The backup should be marked as Error
    ...    7. Wait for the volume to be re-attached and become healthy
    ...    8. Delete the Error backup and verify the volume is still healthy
    ...       (Issue: https://github.com/longhorn/longhorn/issues/7575)
    ...    9. Create one more backup for the volume
    ...    10. Restore a volume from the backup
    ...    11. Attach the restored volume and verify the data checksum matches
    Given Create volume 0 with    size=3Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write 2 GB data to volume 0

    When Create backup 0 for volume 0    wait=False
    And Wait for volume 0 backup to be in progress
    And Delete ${DATA_ENGINE} instance manager on node 0
    And Delete ${DATA_ENGINE} instance manager on node 1
    And Delete ${DATA_ENGINE} instance manager on node 2
    Then Verify backup list contains errors for volume 0
    And Wait for volume 0 attached
    And Wait for volume 0 healthy

    When Delete all backups
    Then Check volume 0 kept in healthy

    When Create backup 1 for volume 0
    And Create volume 1 from backup 1 of volume 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 1 of volume 0 completed
    And Attach volume 1
    And Wait for volume 1 healthy
    Then Check volume 1 data is backup 1 of volume 0

Test Concurrent Backup Creation
    [Documentation]
    ...    Verify that multiple backups created concurrently from different snapshots
    ...    and volumes produce correct and independent restore results.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/6138#issuecomment-1879309192
    ...
    ...    Steps:
    ...    1. Create 2 deployments
    ...    2. Write 1Gi data to file data.bin in both deployment pods, record checksums as checksum 0 and 1
    ...    3. Take snapshot 0 for deployment 0 volume, snapshot 1 for deployment 1 volume
    ...    4. Overwrite data.bin in both deployment pods with new 1Gi data, record as checksum 2 and 3
    ...    5. Take snapshot 2 for deployment 0 volume, snapshot 3 for deployment 1 volume
    ...    6. Create backup 0 from snapshot 0 (deployment 0), backup 1 from snapshot 1 (deployment 1),
    ...       backup 2 from snapshot 2 (deployment 0), backup 3 from snapshot 3 (deployment 1),
    ...       backup 4 directly from deployment 0, backup 5 directly from deployment 1 — all without waiting
    ...    7-12. Restore each backup to a new volume with a pod and verify data integrity

    # Step 1: Create deployments
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 attached and healthy
    And Wait for volume of deployment 1 attached and healthy

    # Step 2: Write initial 1Gi data and record checksums
    And Write 1024 MB data to file data.bin in deployment 0
    And Record file data.bin checksum in deployment 0 as checksum 0
    And Write 1024 MB data to file data.bin in deployment 1
    And Record file data.bin checksum in deployment 1 as checksum 1

    # Step 3: Take first snapshots
    And Create snapshot 0 for deployment 0 volume
    And Create snapshot 1 for deployment 1 volume

    # Step 4: Overwrite data and record new checksums
    And Write 1024 MB data to file data.bin in deployment 0
    And Record file data.bin checksum in deployment 0 as checksum 2
    And Write 1024 MB data to file data.bin in deployment 1
    And Record file data.bin checksum in deployment 1 as checksum 3

    # Step 5: Take second snapshots
    And Create snapshot 2 for deployment 0 volume
    And Create snapshot 3 for deployment 1 volume

    # Step 6: Create all backups concurrently without waiting
    And Create backup 0 for deployment 0 volume    wait=False    snapshot_id=0
    And Create backup 1 for deployment 1 volume    wait=False    snapshot_id=1
    And Create backup 2 for deployment 0 volume    wait=False    snapshot_id=2
    And Create backup 3 for deployment 1 volume    wait=False    snapshot_id=3
    And Create backup 4 for deployment 0 volume    wait=False
    And Create backup 5 for deployment 1 volume    wait=False

    # Wait for all backups to complete
    And Wait for backup 0 of deployment 0 volume to exist in backup list
    And Wait for backup 1 of deployment 1 volume to exist in backup list
    And Wait for backup 2 of deployment 0 volume to exist in backup list
    And Wait for backup 3 of deployment 1 volume to exist in backup list
    And Wait for backup 4 of deployment 0 volume to exist in backup list
    And Wait for backup 5 of deployment 1 volume to exist in backup list

    # Step 7: Restore volume 0 from backup 0 (snapshot 0 of deployment 0) → checksum 0
    When Create volume 0 from deployment 0 volume backup 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 0 restoration from backup 0 of deployment 0 volume completed
    And Wait for volume 0 detached
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create pod 0 using volume 0
    And Wait for pod 0 running
    Then Check pod 0 file data.bin checksum matches checksum 0

    # Step 8: Restore volume 1 from backup 1 (snapshot 1 of deployment 1) → checksum 1
    When Create volume 1 from deployment 1 volume backup 1    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 1 of deployment 1 volume completed
    And Wait for volume 1 detached
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    And Wait for pod 1 running
    Then Check pod 1 file data.bin checksum matches checksum 1

    # Step 9: Restore volume 2 from backup 2 (snapshot 2 of deployment 0) → checksum 2
    When Create volume 2 from deployment 0 volume backup 2    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 restoration from backup 2 of deployment 0 volume completed
    And Wait for volume 2 detached
    And Create persistentvolume for volume 2
    And Create persistentvolumeclaim for volume 2
    And Create pod 2 using volume 2
    And Wait for pod 2 running
    Then Check pod 2 file data.bin checksum matches checksum 2

    # Step 10: Restore volume 3 from backup 3 (snapshot 3 of deployment 1) → checksum 3
    When Create volume 3 from deployment 1 volume backup 3    dataEngine=${DATA_ENGINE}
    And Wait for volume 3 restoration from backup 3 of deployment 1 volume completed
    And Wait for volume 3 detached
    And Create persistentvolume for volume 3
    And Create persistentvolumeclaim for volume 3
    And Create pod 3 using volume 3
    And Wait for pod 3 running
    Then Check pod 3 file data.bin checksum matches checksum 3

    # Step 11: Restore volume 4 from backup 4 (direct backup of deployment 0) → checksum 2
    When Create volume 4 from deployment 0 volume backup 4    dataEngine=${DATA_ENGINE}
    And Wait for volume 4 restoration from backup 4 of deployment 0 volume completed
    And Wait for volume 4 detached
    And Create persistentvolume for volume 4
    And Create persistentvolumeclaim for volume 4
    And Create pod 4 using volume 4
    And Wait for pod 4 running
    Then Check pod 4 file data.bin checksum matches checksum 2

    # Step 12: Restore volume 5 from backup 5 (direct backup of deployment 1) → checksum 3
    When Create volume 5 from deployment 1 volume backup 5    dataEngine=${DATA_ENGINE}
    And Wait for volume 5 restoration from backup 5 of deployment 1 volume completed
    And Wait for volume 5 detached
    And Create persistentvolume for volume 5
    And Create persistentvolumeclaim for volume 5
    And Create pod 5 using volume 5
    And Wait for pod 5 running
    Then Check pod 5 file data.bin checksum matches checksum 3

Test Backup Creation And Deletion At The Same Time
    [Documentation]
    ...    Verify that deleting a completed backup while another backup of the
    ...    same volume is still in progress does not interfere with the in-progress
    ...    backup. The in-progress backup should complete successfully and the
    ...    restored data should be intact.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/6138#issuecomment-1879309192
    ...
    ...    Steps:
    ...    1. Create a deployment to use a Longhorn volume.
    ...    2. Write file1.bin to the deployment and record the checksum.
    ...    3. Create backup 0 and wait for completion.
    ...    4. Write file2.bin to the deployment and record the checksum.
    ...    5. Create backup 1 without waiting for completion.
    ...    6. Delete backup 0 while backup 1 is still in progress.
    ...    7. Wait for backup 1 to complete.
    ...    8. Restore a volume from backup 1.
    ...    9. Check the data integrity of both file1.bin and file2.bin.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy

    # Write file1.bin and take a complete backup
    When Write 512 MB data to file file1.bin in deployment 0
    And Record file file1.bin checksum in deployment 0 as checksum 0
    And Create backup 0 for deployment 0 volume
    And Wait for backup 0 of deployment 0 volume to exist in backup list

    # Write file2.bin, start backup 1 without waiting, then immediately delete backup 0
    And Write 512 MB data to file file2.bin in deployment 0
    And Record file file2.bin checksum in deployment 0 as checksum 1
    And Create backup 1 for deployment 0 volume    wait=False
    And Delete backup 0 of deployment 0 volume

    # Wait for backup 1 to finish, then restore and verify both files
    And Wait for backup 1 of deployment 0 volume to exist in backup list
    When Create volume 0 from deployment 0 volume backup 1    dataEngine=${DATA_ENGINE}
    And Wait for volume 0 restoration from backup 1 of deployment 0 volume completed
    And Wait for volume 0 detached
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create pod 0 using volume 0
    And Wait for pod 0 running
    Then Check pod 0 file file1.bin checksum matches checksum 0
    And Check pod 0 file file2.bin checksum matches checksum 1
