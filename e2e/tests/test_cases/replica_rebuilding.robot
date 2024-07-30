*** Settings ***
Documentation    Replica Rebuilding

Test Tags    manual_test_case

Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    30
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
Replica Rebuilding
    [Documentation]    -- Manual test plan --
    ...                1. Create and attach a volume.
    ...                2. Write a large amount of data to the volume.
    ...                3. Disable disk scheduling and the node scheduling for one replica.
    ...                4. Crash the replica progress. Verify
    ...                    - the corresponding replica in not running state.
    ...                    - the volume will keep robustness Degraded.
    ...                5. Enable the disk scheduling. Verify nothing changes.
    ...                6. Enable the node scheduling. Verify.
    ...                    - the failed replica is reused by Longhorn.
    ...                    - the data content is correct after rebuilding.
    ...                    - volume r/w works fine.
    ...
    ...                == Not implemented ==
    ...                7. Direct delete one replica via UI. Verify
    ...                - a new replica will be replenished immediately.
    ...                - the rebuilding progress in UI page looks good.
    ...                - the data content is correct after rebuilding.
    ...                - volume r/w works fine.
    When Create volume 0 with    size=10Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    And Write 1 GB data to volume 0

    And Disable node 1 scheduling
    And Disable node 1 default disk

    And Crash volume 0 replica process on node 1
    Then Wait volume 0 replica on node 1 stopped
    And Wait for volume 0 degraded

    And Enable node 1 default disk
    Then Check volume 0 replica on node 1 kept in stopped
    And Check for volume 0 kept in degraded

    And Enable node 1 scheduling
    Then Wait until volume 0 replica rebuilding started on node 1
    And Wait for volume 0 healthy
    And Check volume 0 crashed replica reused on node 1

    And Check volume 0 data is intact
    And Check volume 0 works
