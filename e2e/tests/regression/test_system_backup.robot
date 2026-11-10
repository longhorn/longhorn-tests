*** Settings ***
Documentation    System Backup Test Cases

Test Tags    regression    system_backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/system_backup.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/secret.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test System Backup And Restore
    [Tags]    coretest
    [Documentation]    Test system backup and restore
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create system backup 0
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0
    And Wait for volume 0 deleted

    When Restore system backup 0

    Then Wait for volume 0 to be created
    And Wait for volume 0 restoration to complete
    And Attach volume 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Uninstallation With System Backup
    [Tags]    uninstall
    [Documentation]    Test uninstall Longhorn with system backup
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    And Create system backup 0

    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    Then Install Longhorn

Test Create System Backup With DR Volume
    [Tags]    dr-volume
    [Documentation]    Test create system backup with DR volume
    ...                Issue: https://github.com/longhorn/longhorn/issues/10239
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create backup 0 for volume 0
    And Check snapshot for backup 0 of volume 0 exists

    When Create DR volume 1 from backup 0    dataEngine=${DATA_ENGINE}
    And Create system backup 0
    And Assert volume 1 remains attached for at least 60 seconds

Test System Backup With Snapshot Of Empty Creation Time
    [Tags]    system-backup    snapshot
    [Documentation]    Test system backup with volumeBackupPolicy if-not-present
    ...                succeeds when a restored volume has a snapshot with an empty creationTime.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/13942
    ...
    ...                Conditions required to reproduce:
    ...                - A snapshot with status.readyToUse=true, status.creationTime="" and
    ...                  status.size != 0 (snapshots with size 0 are skipped and do not trigger it)
    ...                - The volume has a non-empty status.lastBackup
    ...                - SystemBackup uses volumeBackupPolicy: if-not-present (the default)
    ...
    ...                Reproduce steps:
    ...                1. Create a volume, attach it, write some data, and create
    ...                   a backup.
    ...                2. Restore to a new volume and wait for the restore to complete.
    ...                3. Check the snapshots of the new volume:
    ...                   kubectl -n longhorn-system get snapshots.longhorn.io
    ...                   The first restored snapshot has an empty CREATIONTIME and
    ...                   READYTOUSE=true. Its SIZE must be non-zero to hit the bug.
    ...                4. Attach the new volume, and create another backup so that
    ...                   `kubectl -n longhorn-system get volume vol-restore -o jsonpath='{.status.lastBackup}'`
    ...                   is non-empty.
    ...                6. Create a SystemBackup with spec.volumeBackupPolicy: if-not-present.
    ...                7. Check the SystemBackup state becomes Ready without errors like:
    ...                   parsing time "" as "2006-01-02T15:04:05Z07:00": cannot parse "" as "2006"
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create backup 0 for volume 0
    And Wait for backup 0 of volume 0 to exist in backup list

    When Create volume 1 from backup 0 of volume 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration to complete
    And Attach volume 1
    And Wait for volume 1 healthy
    And Create backup 1 for volume 1
    And Wait for backup 1 of volume 1 to exist in backup list
    And Create system backup 0

    ${system_backup_name} =    generate_name_with_suffix    system-backup    0
    Then Wait for system backup ${system_backup_name} ready

Test System Restore Job Uses Registry Secret
    [Documentation]    Test SystemRestore propagates the registry-secret setting to the rollout Job's imagePullSecrets.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/13968
    ...
    ...                Use the existing Longhorn installation and dummy registry credentials.
    ...                A private registry and actual registry authentication are not required.
    ...
    ...                1. Save the original registry-secret setting.
    ...                2. Create a temporary Docker registry Secret in longhorn-system with dummy credentials.
    ...                3. Set registry-secret to the temporary Secret name and create a SystemBackup.
    ...                4. Start a SystemRestore without waiting for completion.
    ...                5. Verify the corresponding longhorn-system-rollout Job's imagePullSecrets contains the Secret name.
    ...                6. Wait for the same SystemRestore to complete.
    ...                7. Restore the original registry-secret setting and clean up test resources, including the Secret.
    [Teardown]    Cleanup registry secret test resources
    Given Save original registry secret setting
    ${secret_name} =    Create dummy registry secret 0

    When Setting registry-secret is set to ${secret_name}
    And Create system backup 0
    ${restore_name} =    Restore system backup 0    wait=${FALSE}
    Then System restore ${restore_name} rollout job should use registry secret ${secret_name}
    And Wait for system restore ${restore_name} completed

*** Keywords ***
Cleanup registry secret test resources
    ${original} =    Get Variable Value    \${original_registry_secret}    ${NONE}
    IF    $original is not None
        Setting registry-secret is set to ${original}
    END
    Cleanup test resources
