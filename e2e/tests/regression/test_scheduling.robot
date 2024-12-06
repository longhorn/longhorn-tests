*** Settings ***
Documentation    Scheduling Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/node.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
Test Soft Anti Affinity Scheduling
    [Tags]    coretest
    [Documentation]    Test that volumes with Soft Anti-Affinity work as expected.
    ...
    ...    With Soft Anti-Affinity, a new replica should still be scheduled on a node
    ...    with an existing replica, which will result in "Healthy" state but limited
    ...    redundancy.
    ...
    ...    1. Create a volume and attach to the current node
    ...    2. Generate and write `data` to the volume.
    ...    3. Set `soft anti-affinity` to true
    ...    4. Disable current node's scheduling.
    ...    5. Remove the replica on the current node
    ...    6. Wait for the volume to complete rebuild. Volume should have 3 replicas.
    ...    7. Verify `data`
    Given Create volume 0 with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Set setting replica-soft-anti-affinity to true
    # disabling scheduling on a node only sets the node status to "Disable", not "Unschedulable"
    # therefore disabling scheduling doesn't alter the node["conditions"]["Schedulable"]["status"] field
    # only cordoning a node can set it to "Unschedulable"
    And Cordon node 1
    And Delete volume 0 replica on node 1

    Then Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Replica Auto Balance Disk In Pressure
    [Tags]    coretest
    [Documentation]    Test replica auto balance disk in pressure
    ...    This test simulates a scenario where a disk reaches a certain
    ...    pressure threshold (80%), triggering the replica auto balance
    ...    to rebuild the replicas to another disk with enough available
    ...    space. Replicas should not be rebuilt at the same time.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/4105
    Given Set setting replica-soft-anti-affinity to false
    And Set setting replica-auto-balance-disk-pressure-percentage to 80

    And Create 1 Gi disk 0 on node 0
    And Create 1 Gi disk 1 on node 0
    And Disable disk 1 scheduling on node 0
    And Disable node 0 default disk
    And Disable node 1 scheduling
    And Disable node 2 scheduling

    And Create storageclass one-replica with    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    # 1 Gi disk, but only 950 Mi available, 950 Mi / 3 = 316 Mi
    And Create statefulset 0 using RWO volume with one-replica storageclass and size 316 Mi
    And Create statefulset 1 using RWO volume with one-replica storageclass and size 316 Mi
    And Create statefulset 2 using RWO volume with one-replica storageclass and size 316 Mi
    And Check volume of statefulset 0 replica on node 0 disk 0
    And Check volume of statefulset 1 replica on node 0 disk 0
    And Check volume of statefulset 2 replica on node 0 disk 0

    # Write 950 Mi * 80% / 3 = 254 Mi data to disk 0 to make it in pressure
    And Write 254 MB data to file data.bin in statefulset 0
    And Write 254 MB data to file data.bin in statefulset 1
    And Write 254 MB data to file data.bin in statefulset 2
    And Check node 0 disk 0 is in pressure

    When Enable disk 1 scheduling on node 0
    And set setting replica-auto-balance to best-effort

    # auto balance should happen
    Then There should be replicas running on node 0 disk 0
    And There should be replicas running on node 0 disk 1
    And Check node 0 disk 0 is not in pressure
    And Check node 0 disk 1 is not in pressure

    And Check statefulset 0 data in file data.bin is intact
    And Check statefulset 1 data in file data.bin is intact
    And Check statefulset 2 data in file data.bin is intact

Test Replica Auto Balance Node Least Effort
    [Tags]    coretest
    [Documentation]    Scenario: replica auto-balance nodes with `least_effort`
    Given Set setting replica-soft-anti-affinity to true
    And Set setting replica-auto-balance to least-effort

    When Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create volume 0 with    numberOfReplicas=6    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Volume 0 should have 6 replicas running on node 0
    And Volume 0 should have 0 replicas running on node 1
    And Volume 0 should have 0 replicas running on node 2

    When Enable node 1 scheduling
    # wait for auto balance
    Then Volume 0 should have replicas running on node 1
    And Volume 0 should have 6 replicas running
    # loop 3 times with 5-second wait and compare the replica count to:
    # ensure no additional scheduling occurs
    # the replica count remains unchanged
    And Volume 0 should have 5 replicas running on node 0 and no additional scheduling occurs
    And Volume 0 should have 1 replicas running on node 1 and no additional scheduling occurs
    And Volume 0 should have 0 replicas running on node 2 and no additional scheduling occurs

    When Enable node 2 scheduling
    # wait for auto balance
    Then Volume 0 should have replicas running on node 2
    And Volume 0 should have 6 replicas running
    # loop 3 times with 5-second wait and compare the replica count to:
    # ensure no additional scheduling occurs
    # the replica count remains unchanged
    And Volume 0 should have 4 replicas running on node 0 and no additional scheduling occurs
    And Volume 0 should have 1 replicas running on node 1 and no additional scheduling occurs
    And Volume 0 should have 1 replicas running on node 2 and no additional scheduling occurs

    And Wait for volume 0 healthy
    And Check volume 0 data is intact
