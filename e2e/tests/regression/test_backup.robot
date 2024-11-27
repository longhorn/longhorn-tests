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
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backupstore.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Keywords ***
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

    When Create DR volume 1 from backup 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 0 completed
    And Create DR volume 2 from backup 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 restoration from backup 0 completed
    And Create DR volume 3 from backup 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 3 restoration from backup 0 completed

    Then Snapshot PV PVC could not be created on DR volume 1
    And Backup target could not be changed when DR volume exist

    When Activate DR volume 1
    And Attach volume 1
    And Wait for volume 1 healthy
    Then Check volume 1 data is backup 0


    When Write data 1 to volume 0
    And Create backup 1 for volume 0
    # Wait for DR volume 2 incremental restoration completed
    Then Wait for volume 2 restoration from backup 1 completed
    And Activate DR volume 2
    And Attach volume 2
    And Wait for volume 2 healthy
    And Check volume 2 data is backup 1

    When Write data 2 to volume 0
    And Create backup 2 for volume 0
    # Wait for DR volume 3 incremental restoration completed
    Then Wait for volume 3 restoration from backup 2 completed
    And Activate DR volume 3
    And Attach volume 3
    And Wait for volume 3 healthy
    And Check volume 3 data is backup 2
    And Detach volume 3
    And Wait for volume 3 detached

    When Create persistentvolume for volume 3
    And Create persistentvolumeclaim for volume 3
    And Create pod 0 using volume 3
    Then Wait for pod 0 running
    And Delete pod 0
    And Delete persistentvolumeclaim for volume 3
    And Delete persistentvolume for volume 3
