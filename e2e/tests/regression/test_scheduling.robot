*** Settings ***
Documentation    Scheduling Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

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
