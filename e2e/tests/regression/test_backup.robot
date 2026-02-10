*** Settings ***
Documentation    Backup Test Cases

Test Tags    regression    backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
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

Snapshot PV PVC could not be created on DR volume 1
    Create snapshot 0 of volume 1 will fail
    Create persistentvolume for volume 1 will fail
    Create persistentvolumeclaim for volume 1 will fail

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
    And Verify backup list contains backup 0 of volume 0
    And Verify backup list contains backup 1 of volume 1

    When Place file backup_1234@failure.cfg into the backups folder of volume 0
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains no error for volume 1
    And Verify backup list contains backup 0 of volume 0
    And Verify backup list contains backup 1 of volume 1

    And Delete backup volume 0
    And Delete backup volume 1

Test Incremental Restore
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

    Then Snapshot PV PVC could not be created on DR volume 1
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
    [Tags]    auto-cleanup-snapshot
    [Documentation]    Test cleanup snapshot with the global setting after backup completed
    IF    '${DATA_ENGINE}' == 'v2'
        # https://github.com/longhorn/longhorn/issues/12082
        Skip    Test case need to refine for v2 data engine
    END

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
    [Tags]    backup
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
