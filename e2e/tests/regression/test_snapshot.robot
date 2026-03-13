*** Settings ***
Documentation    Snapshot Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource

Test Setup   Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Test Allow Snapshots Removal During Trim
    [Arguments]    ${FILESYSTEM}
    [Documentation]    Migrated from test_basic.py::test_filesystem_trim
    ...   This test verifies that when the option `unmapMarkSnapChainRemoved` is enabled,
    ...   the latest snapshot and the preceding continuous chain of snapshots are automatically marked as removed,
    ...   allowing Longhorn to reclaim space for as many snapshots as possible.
    ...
    ...   1. Create a volume with option `unmapMarkSnapChainRemoved` enabled
    ...   2. Create PV/PVC for the volume, and create a pod to mount the volume
    ...   3. write file 0 to the volume, then take snapshot snap 0
    ...   4. Write file 1 to the volume, then take snapshot snap 1
    ...   5. Detach and re-attach the volume without frontend, and revert the volume to snap 0
    ...   6. Recreate a pod to mount the volume
    ...   7. Write file 2, then take snapshot snap 2
    ...   8. Write file 3, then take snapshot snap 3
    ...   9. Write file 4, then take snapshot snap 4
    ...   10. Write file 5
    ...   11. Remove file 0, file 2, file 3, file 4, and file 5
    ...       Verify the snapshots and volume head size are not shrunk
    ...   12. Do filesystem trim
    ...   13. Verify that snap 2, snap 3, snap 4 are marked as removed,
    ...       and snap 2, snap 3, snap 4, and volume head size are shrunk
    ...
    ...   14. Disable option `unmapMarkSnapChainRemoved` for the volume
    ...   15. Write file 6, then take snapshot snap 6
    ...   16. Write file 7
    ...   17. Remove file 6 and file 7
    ...   18. Do filesystem trim
    ...   19. Verify that snap 6 is not marked as removed,
    ...       and snap 6 and volume head size are shrunk
    ...
    ...   20. Detach and re-attach the volume without frontend, and revert the volume to snap 1
    ...   21. Recreate a pod to mount the volume. Verify the file 0 and file 1
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 volumes don't support unmapMarkSnapChainRemoved option
    END
    Given Create volume 0
    And Update volume 0 unmapMarkSnapChainRemoved to enabled
    And Create persistentvolume for volume 0    fsType=${FILESYSTEM}
    And Create persistentvolumeclaim for volume 0
    And Create pod 0 using volume 0
    And Wait for pod 0 running
    And Wait for volume 0 healthy

    And Write 256 MB data to file file0 in pod 0
    And Record file file0 checksum in pod 0 as checksum 0
    And Create snapshot 0 of volume 0
    And Write 256 MB data to file file1 in pod 0
    And Record file file1 checksum in pod 0 as checksum 1
    And Create snapshot 1 of volume 0

    And Delete pod 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 attached
    And Wait for volume 0 healthy
    And Revert volume 0 to snapshot 0
    And Detach volume 0
    And Wait for volume 0 detached

    And Create pod 0 using volume 0
    And Wait for pod 0 running
    And Wait for volume 0 healthy
    And Write 256 MB data to file file2 in pod 0
    And Create snapshot 2 of volume 0
    And Write 256 MB data to file file3 in pod 0
    And Create snapshot 3 of volume 0
    And Write 256 MB data to file file4 in pod 0
    And Create snapshot 4 of volume 0
    And Write 256 MB data to file file5 in pod 0

    When Run commands in pod 0    commands=rm /data/file0 /data/file2 /data/file3 /data/file4 /data/file5 && sync
    # There are some extra metadata
    # so the size would be greater than 256Mi
    Then Volume 0 snapshot 0 size should be greater than 256Mi
    And Volume 0 snapshot 2 size should be greater than 256Mi
    And Volume 0 snapshot 3 size should be greater than 256Mi
    And Volume 0 snapshot 4 size should be greater than 256Mi
    And Volume 0 volume head size should be greater than 256Mi

    When Trim volume 0
    Then Validate snapshot 2 is marked as removed in volume 0 snapshot list
    And Validate snapshot 3 is marked as removed in volume 0 snapshot list
    And Validate snapshot 4 is marked as removed in volume 0 snapshot list
    # There are some extra metadata
    # so the size would be greater than 0
    And Volume 0 snapshot 2 size should be less than 16Mi
    And Volume 0 snapshot 3 size should be less than 16Mi
    And Volume 0 snapshot 4 size should be less than 16Mi
    # volume head stores even more metadata than other snapshots
    And Volume 0 volume head size should be less than 64Mi

    When Update volume 0 unmapMarkSnapChainRemoved to disabled
    And Write 256 MB data to file file6 in pod 0
    And Create snapshot 6 of volume 0
    And Write 256 MB data to file file7 in pod 0
    Then Run commands in pod 0    commands=rm /data/file6 /data/file7 && sync
    And Volume 0 snapshot 6 size should be greater than 256Mi
    And Volume 0 volume head size should be greater than 256Mi

    When Trim volume 0
    Then Validate snapshot 6 is not marked as removed in volume 0 snapshot list
    And Volume 0 snapshot 6 size should be less than 16Mi
    And Volume 0 volume head size should be less than 64Mi

    And Delete pod 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 attached
    And Wait for volume 0 healthy
    When Revert volume 0 to snapshot 1
    And Detach volume 0
    And Wait for volume 0 detached

    And Create pod 0 using volume 0
    And Wait for pod 0 running
    And Wait for volume 0 healthy
    Then Check pod 0 file file0 checksum matches checksum 0
    And Check pod 0 file file1 checksum matches checksum 1

*** Test Cases ***
Test Snapshot During Active IO
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12140
    ...    Concurrent snapshot/revert during active I/O
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
    And Create snapshot 0 of volume 0
    And Write 100 MB data to file data.txt in pod 0

    And Delete pod 0 to detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy

    When Revert volume 0 to snapshot 0
    And Detach volume 0
    And Wait for volume 0 detached
    And Create pod 1 using volume 0
    And Wait for pod 1 running
    Then Check pod 1 file data.txt checksum matches checksum 0

Test Volume Snapshot Checksum When Healthy Replicas More Than 1
    [Tags]    volume setting snapshot
    [Documentation]
    ...    This test validates that snapshot checksum calculation is performed when the number of healthy replicas is more than 1.
    
    Given Setting snapshot-data-integrity-immediate-check-after-snapshot-creation is set to {"v1":"true","v2":"true"}
    And Create volume 0 with    size=100Mi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}

    When Attach volume 0
    And Wait for volume 0 healthy
    And Create snapshot 0 of volume 0

    Then Validate snapshot 0 is in volume 0 snapshot list
    And Wait for volume 0 snapshot 0 checksum to be calculated

Test Volume Snapshot Checksum Skipped When Less Than 2 Healthy Replicas
    [Tags]    volume setting snapshot
    [Documentation]
    ...    This test validates that snapshot checksum calculation is skipped when the number of healthy replicas is less than 2.

    Given Setting snapshot-data-integrity-immediate-check-after-snapshot-creation is set to {"v1":"true","v2":"true"}
    And Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create volume 0 with    size=100Mi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}

    When Attach volume 0
    And Wait for volume 0 degraded
    And Create snapshot 0 of volume 0

    Then Validate snapshot 0 is in volume 0 snapshot list
    And Validate snapshot 0 checksum of volume 0 is skipped for 60 seconds

Test Concurrent Job Limit For Snapshot Purge
    [Tags]    snapshot-purge
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11635
    ...    This test case only supports v1 volumes: https://github.com/longhorn/longhorn/issues/11635#issuecomment-3588360359
    ...    1. Set snapshot-heavy-task-concurrent-limit to 1
    ...    2. Set disable-snapshot-purge to false
    ...    3. Create and Attach a volume
    ...    4. Write data to the volume and take snapshot 1
    ...    5. Write data to the volume and take snapshot 2
    ...    6. Write data to the volume and take snapshot 3
    ...    7. Remove snapshot 2, trigger snapshot purge
    ...    8. During the snapshot deletion, try to trigger snapshot purge again manually
    ...    curl -X POST \
    ...    'http://localhost:8080/v1/volumes/<volume-name>?action=snapshotPurge' \
    ...    -H 'Accept: application/json'
    ...    9. It fails with an error: cannot start snapshot purge: concurrent snapshot purge limit reached
    ...    10. Once the snapshot deletion is complete, execute the curl request again. It should succeed
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 volume not support snapshot purge now
    END

    Given Setting snapshot-heavy-task-concurrent-limit is set to 1
    And Setting disable-snapshot-purge is set to false
    And Create volume 0    dataEngine=v1
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create snapshot 0 of volume 0
    And Write data to volume 0
    And Create snapshot 1 of volume 0
    And Write data to volume 0
    And Create snapshot 2 of volume 0

    When Delete snapshot 1 of volume 0
    And Purge volume 0 snapshot    wait=False
    And Wait for snapshot purge for volume 0 start
    # manually trigger another snapshot purge will fail
    # because snapshot-heavy-task-concurrent-limit is set to 1
    Then Purge volume 0 snapshot should fail
    ...    expected_error_message=concurrent snapshot purge limit reached

    When Wait for snapshot purge for volume 0 completed
    Then Purge volume 0 snapshot

Test Allow Snapshots Removal During Trim With Filesystem XFS
    Test Allow Snapshots Removal During Trim    FILESYSTEM=xfs

Test Allow Snapshots Removal During Trim With Filesystem EXT4
    Test Allow Snapshots Removal During Trim    FILESYSTEM=ext4
