*** Settings ***
Documentation    System Backup Test Cases

Test Tags    regression    system-backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/system_backup.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/snapshot.resource

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

Test System Backup Ready After Volume Backup Triggered During Creation
    [Documentation]    Test system backup reaches Ready when another backup of
    ...                a volume is triggered while the system backup is still
    ...                creating volume backups.
    ...                Issue: https://github.com/longhorn/longhorn/issues/14374
    ...                On v1.12.1, the system backup stays in CreatingVolumeBackups.
    FOR    ${i}    IN RANGE    10
        Create volume ${i} with    dataEngine=${DATA_ENGINE}
        Attach volume ${i}
        Wait for volume ${i} healthy
        # volume 0 has less data so its backup completes before the others
        IF    ${i} == 0
            Write 16 Mi data to volume ${i}
        ELSE
            Write 256 Mi data to volume ${i}
        END
    END

    When Create system backup 0    wait=${False}
    And Wait for volume 0 backup to be created
    And Create backup 1 for volume 0

    Then Wait for system backup 0 ready

Test System Backup Ready After Volume Backup Snapshot Deleted During Creation
    [Documentation]    Test system backup reaches Ready when the snapshot used
    ...                by the volume backup is deleted while the system backup
    ...                is still creating volume backups.
    ...                Issue: https://github.com/longhorn/longhorn/issues/14374
    ...                On v1.12.1, it logs "Failed to get snapshot" repeatedly.
    FOR    ${i}    IN RANGE    10
        Create volume ${i} with    dataEngine=${DATA_ENGINE}
        Attach volume ${i}
        Wait for volume ${i} healthy
        # volume 0 has less data so its backup completes before the others
        IF    ${i} == 0
            Write 16 Mi data to volume ${i}
        ELSE
            Write 256 Mi data to volume ${i}
        END
    END

    When Create system backup 0    wait=${False}
    And Wait for volume 0 backup to be created
    ${snapshot_name} =    Get snapshot of volume 0
    # the extra snapshot moves the snapshot chain away from volume-head,
    # which allows the system backup snapshot to be deleted
    And Create snapshot extra of volume 0
    And Remove snapshot ${snapshot_name} by name from volume 0

    Then Wait for system backup 0 ready
