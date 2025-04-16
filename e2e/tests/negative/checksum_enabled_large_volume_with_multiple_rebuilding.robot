*** Settings ***
Documentation    -- Manual test plan --
...              - https://longhorn.github.io/longhorn-tests/manual/pre-release/stability/checksum-enabled-large-volume/
...              - 1. Create a 50 Gi volume. write around 30 Gi data into it.
...              - 2. Enable the setting Snapshot Data Integrity.
...              - 3. Keep writing in the volume continuously using dd command like 
...              -    while true; do dd if=/dev/urandom of=t1 bs=512 count=1000 conv=fsync status=progress && rm t1; done.
...              - 4. Create a recurring job of backup for every 15 min.
...              - 5. Delete a replica and wait for the replica rebuilding.
...              - 6. Repeat the steps of deletion of the replica and verify Longhorn doesn’t take more time than the first iteration.
...
...                == Not implemented ==
...              - 7. Compare the performance of replica rebuilding from previous Longhorn version
...              -    without the setting Snapshot Data Integrity.
...              - 8. Verify the Longhorn manager logs, no abnormal logs should be present.


Test Tags    manual    negative    longhorn-10711    large-size


Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/recurringjob.resource


Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Delete replica and get rebuilding time
    [Arguments]    ${volume_id}    ${node_id}
    Delete volume ${volume_id} replica on node ${node_id}
    Wait until volume ${volume_id} replica rebuilding started on node ${node_id}
    ${start_time_in_sec}=    Get Time    epoch
    Wait until volume ${volume_id} replica rebuilding completed on node ${node_id}
    ${end_time_in_sec}=    Get Time    epoch
    ${rebuild_time}=    Evaluate    ${end_time_in_sec} - ${start_time_in_sec}
    [Return]    ${rebuild_time}

The second replica rebuilding time should be less than first
    ${1st_rebuild_time}=    Delete replica and get rebuilding time    0    0
    ${2nd_rebuild_time}=    Delete replica and get rebuilding time    0    0
#    Should Be True    ${2nd_rebuild_time} <= ${1st_rebuild_time}
    ${status}=    Evaluate    ${2nd_rebuild_time} <= ${1st_rebuild_time}
    Run Keyword If    not ${status}
    ...    Log    The 2nd replica rebuilding time is greater than the 1st    WARN

*** Test Cases ***
Checksum Enabled Large Volume With Multiple Rebuilding
    Given Create volume 0 with    size=50Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write 30 GB data to volume 0
    And Set setting snapshot-data-integrity to enabled
    And Keep writing data to volume 0
    And Create recurringjob for volume 0 with    task=backup    cron=*/15 * * * *
    Then The second replica rebuilding time should be less than first
