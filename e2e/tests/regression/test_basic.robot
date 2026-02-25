*** Settings ***
Documentation    Basic Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/engine.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Create volume with invalid name should fail
  [Arguments]    ${invalid_volume_name}
  Given Create volume     ${invalid_volume_name}
  Then No volume created

*** Test Cases ***
Test Invalid Volume Name
    [Tags]    coretest
    [Documentation]    Test invalid volume name
    [Template]    Create volume with invalid name should fail
        wrong_volume-name-1.0
        wrong_volume-name

Test Volume Basic
    [Tags]    coretest
    [Documentation]    Test basic volume operations
    ...
    ...                1. Create a volume and attach to the current node, then check volume states
    ...                2. Write then read back to check volume data
    Given Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    When Attach volume 0
    And Wait for volume 0 healthy

    When Write data to volume 0
    Then Check volume 0 data is intact

    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0

Test V1 Snapshot
    [Tags]    coretest    snapshot-purge
    [Documentation]    Test snapshot operations
    Given Create volume 0 with    dataEngine=v1
    When Attach volume 0
    And Wait for volume 0 healthy

    And Create snapshot 0 of volume 0

    And Write data 1 to volume 0
    And Create snapshot 1 of volume 0

    And Write data 2 to volume 0
    And Create snapshot 2 of volume 0

    Then Validate snapshot 0 is parent of snapshot 1 in volume 0 snapshot list
    And Validate snapshot 1 is parent of snapshot 2 in volume 0 snapshot list
    And Validate snapshot 2 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 2 of volume 0
    Then Validate snapshot 2 is in volume 0 snapshot list
    And Validate snapshot 2 is marked as removed in volume 0 snapshot list
    And Check volume 0 data is data 2

    When Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy
    And Create snapshot 3 of volume 0
    Then Validate snapshot 3 is parent of volume-head in volume 0 snapshot list

    When Revert volume 0 to snapshot 1
    And Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 1
    And Validate snapshot 1 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 1 of volume 0
    And Delete snapshot 0 of volume 0

    And Purge volume 0 snapshot
    Then Validate snapshot 0 is not in volume 0 snapshot list
    And Validate snapshot 1 is in volume 0 snapshot list
    And Validate snapshot 1 is marked as removed in volume 0 snapshot list
    And Validate snapshot 2 is not in volume 0 snapshot list

    And Check volume 0 data is data 1

Test Strict Local Volume Disabled Revision Counter By Default
    [Tags]    coretest    single-replica
    [Documentation]
    ...    1. Set the global setting disable-revision-counter to false
    ...    2. Create a volume with 1 replica and strict-local data locality
    ...    3. See that the revisionCounterDisabled: true for volume/engine/replica CRs
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Setting disable-revision-counter is not supported for v2 data engine
    END

    Given Setting disable-revision-counter is set to {"v1":"false"}

    When Create volume 0 with    numberOfReplicas=1    dataLocality=strict-local
    And Wait for volume 0 detached
    Then Volume 0 setting revisionCounterDisabled should be True
    And Volume 0 engine revisionCounterDisabled should be True
    And Volume 0 replica revisionCounterDisabled should be True

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
    Given Create volume 0 with    size=10Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    And Write 1 GB data to volume 0

    And Disable node 1 scheduling
    And Disable node 1 default disk

    When Record volume 0 replica name on node 1
    And Delete ${DATA_ENGINE} instance manager on node 1
    Then Wait volume 0 replica on node 1 stopped
    And Wait for volume 0 degraded

    When Enable node 1 default disk
    Then Check volume 0 replica on node 1 kept in stopped
    And Check volume 0 kept in degraded

    When Enable node 1 scheduling
    # it isn’t guaranteed to catch the moment when the replica is rebuilding.
    # a replica could become healthy directly without showing the rebuilding progress
    Then Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    And Check volume 0 crashed replica reused on node 1

    And Check volume 0 data is intact
    And Check volume 0 works

Test File Ownership And Permission By Executing Git Clone
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1

    When Run commands in deployment 0    commands=git clone https://github.com/longhorn/longhorn.git
    And Run commands in deployment 1    commands=git clone https://github.com/longhorn/longhorn.git
    Then Test should pass

Test Rapid Volume Detachment
    Given Setting orphan-resource-auto-deletion is set to instance
    And Setting orphan-resource-auto-deletion-grace-period is set to 60
    And Create volume 0 with    dataEngine=${DATA_ENGINE}

    FOR    ${i}    IN RANGE    100
        When Attach volume 0 to node 0    wait=False
        And Detach volume 0
        And Wait for volume 0 detached
        Then Wait for engine instances in ${DATA_ENGINE} instance manager CR on node 0 to be cleaned up
    END

Test Deploy V2 Volume With Disabled V1 Data Engine
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test case not support for v1 data engine
    END
    Given Setting v1-data-engine is set to false
    And Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=v2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    When Write data to volume 0
    Then Check volume 0 data is intact
