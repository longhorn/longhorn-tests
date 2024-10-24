*** Settings ***
Documentation    Uninstallation Checks

Test Tags    negative

Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/longhorn.resource
Library     ../libs/keywords/setting_keywords.py

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
Pull backup created by another Longhorn system
    [Documentation]    Pull backup created by another Longhorn system
    ...    1. Install test version of Longhorn.
    ...    2. Create volume, write data, and take backup.
    ...    3. Uninstall Longhorn.
    ...    4. Install test version of Longhorn.
    ...    5. Restore the backup create in step 2 and verify the data.
    ...    6. Uninstall Longhorn.
    ...    7. Install previous version of Longhorn.
    ...    8. Create volume, write data, and take backup.
    ...    9. Uninstall Longhorn.
    ...    10. Install test version of Longhorn.
    ...    11. Restore the backup create in step 8 and verify the data.        
    ...
    ...    Important
    ...    - This test case need have set environment variable manually first if not run on Jenkins
    ...       - LONGHORN_INSTALL_METHOD : helm or manifest
    ...       - LONGHORN_REPO_BRANCH (ex:master)
    ...       - CUSTOM_LONGHORN_MANAGER_IMAGE (if not using master-head)
    ...       - CUSTOM_LONGHORN_ENGINE_IMAGE (if not using master-head)
    ...       - CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE (if not using master-head)
    ...       - CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE (if not using master-head)
    ...       - CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE (if not using master-head)
    ...       - LONGHORN_STABLE_VERSION (ex:v1.6.3)
    Given Set setting deleting-confirmation-flag to true
    And Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 300 MB to volume 0
    When Create backup 0 for volume 0    
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains backup 0 of volume 0
    Then Uninstall Longhorn
    And Check Longhorn CRD removed

    # Install current version then pull backup and verify data
    Then Install Longhorn
    And Set setting deleting-confirmation-flag to true
    And set_backupstore
    And Check backup synced from backupstore
    And Create volume 1 from backup 0 in another cluster
    And Wait for volume 1 detached
    And Attach volume 1
    And Wait for volume 1 healthy
    Then Check volume 1 data is backup 0 created in another cluster
    Then Uninstall Longhorn
    And Check Longhorn CRD removed

    # Install previous version and create backup
    Then Install Longhorn stable version
    And Set setting deleting-confirmation-flag to true
    And set_backupstore
    And Create volume 2 with    dataEngine=${DATA_ENGINE}
    And Attach volume 2
    And Wait for volume 2 healthy
    And Write data 1 300 MB to volume 2
    When Create backup 1 for volume 2
    Then Verify backup list contains no error for volume 2
    And Verify backup list contains backup 1 of volume 2
    Then Uninstall Longhorn stable version
    And Check Longhorn CRD removed

     # Install current version then pull backup and verify data
    Then Install Longhorn
    And set_backupstore
    And Check backup synced from backupstore
    And Create volume 3 from backup 1 in another cluster
    And Wait for volume 3 detached
    And Attach volume 3
    And Wait for volume 3 healthy
    Then Check volume 3 data is backup 1 created in another cluster
