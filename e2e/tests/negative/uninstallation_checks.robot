*** Settings ***
Documentation    Uninstallation Checks

Test Tags    uninstall    negative

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
Resource    ../keywords/longhorn.resource
Library     ../libs/keywords/setting_keywords.py

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Uninstallation Checks
    [Documentation]    Uninstallation Checks
    ...    Prerequisites
    ...    - Have a setup of Longhorn installed on a kubernetes cluster.
    ...    - Have few volumes backups stored on S3/NFS backup store.
    ...    - Have one DR volume created (not activated)
    ...
    ...    Test steps
    ...    1. Uninstall Longhorn.
    ...    2. Check the logs of the job longhorn-uninstall, make sure there is no error(skip this step if using helm).
    ...    3. Check all the components of Longhorn from the namespace longhorn-system are uninstalled. E.g. Longhorn manager, Longhorn driver, Longhorn UI, instance manager, engine image, CSI driver etc.
    ...    4. Check all the CRDs are removed kubectl get crds | grep longhorn.
    ...    5. Check the backup stores, the backups taken should NOT be removed.
    ...    6. Create the DR volume in the other cluster and check the data.
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

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    When Create backup 0 for volume 0
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains backup 0 of volume 0

    Then Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    # Assume this is another Longhorn cluster
    Then Install Longhorn
    And Set default backupstore
    And Check backup synced from backupstore
    When Create DR volume 0 from backup 0 in another cluster
    And Wait for volume 0 restoration from backup 0 in another cluster completed
    And Activate DR volume 0
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is backup 0 created in another cluster

Uninstall Longhorn After Disabling V1 And V2 Data Engines
    [Documentation]    Test uninstalling Longhorn after disabling both v1 and v2 data engines
    ...    Related Issue:
    ...    https://github.com/longhorn/longhorn/issues/11934
    ...
    ...    Prerequisites
    ...    - Have a setup of Longhorn installed on a kubernetes cluster.
    ...
    ...    Test steps
    ...    - 1. Create volume, write data, and take backup.
    ...    - 2. Detach volume
    ...    - 3. Disable v1 data engine by setting v1-data-engine to false.
    ...    - 4. Disable v2 data engine by setting v2-data-engine to false.
    ...    - 5. Wait for all instance managers to be removed.
    ...    - 6. Set deleting-confirmation-flag to true.
    ...    - 7. Uninstall Longhorn.
    ...    - 8. Check all the components of Longhorn from the namespace longhorn-system are uninstalled.
    ...    - 9. Check all the CRDs are removed.
    ...    - 10. Reinstall Longhorn to verify the system can be installed again.
    ...
    ...    Expected behavior
    ...    - Longhorn should be uninstalled successfully without being stuck at removing backup target.
    ...    - All Longhorn components and CRDs should be removed.
    ...    - Longhorn can be reinstalled successfully after uninstallation.

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 300 MB to volume 0

    When Create backup 0 for volume 0
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains backup 0 of volume 0
    And Detach volume 0
    And Setting v1-data-engine is set to false
    And Setting v2-data-engine is set to false

    # Wait for all instance managers to be removed after disabling data engines
    When Wait for all instance managers removed

    # Set deleting confirmation flag and uninstall Longhorn
    Then Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    # Verify Longhorn can be reinstalled
    And Install Longhorn
    And Wait for Longhorn components all running
