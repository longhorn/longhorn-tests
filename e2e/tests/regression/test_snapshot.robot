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
