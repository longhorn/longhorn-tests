*** Settings ***
Documentation    Backup Test Cases

Test Tags    regression

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

Test Setup    Set up test environment
Test Teardown    Cleanup test resources without corrupting remote backupstore

*** Keywords ***
# Reset backup target from remote AWS S3 to local minio backup store before cleaning up resources
# to avoid deleting the existing backupa on AWS S3
Cleanup test resources without corrupting remote backupstore
    Set backupstore
    Cleanup test resources

Snapshot PV PVC could not be created on DR volume 1
    Create snapshot 0 of volume 1 will fail
    Create persistentvolume for volume 1 will fail
    Create persistentvolumeclaim for volume 1 will fail

Backup target could not be changed when DR volume exist
    Set setting backup-target to random.backup.target will fail

*** Test Cases ***
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
    [Documentation]    Test uninstall Longhorn with normal and failed backups
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    And Create backup 0 for volume 0
    And Create error backup for volume 0
    And Verify backup list contains errors for volume 0

    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    Then Install Longhorn

Test Cleanup Snapshot With The Global Setting After Backup Completed
    [Tags]    auto-cleanup-snapshot
    [Documentation]    Test cleanup snapshot with the global setting after backup completed
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
    Given Reset backupstore
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
