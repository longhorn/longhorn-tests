*** Settings ***
Documentation    Orphan Test Cases
...
...              Reference: /docs/content/manual/release-specific/v1.9.0/test-orphaned-instance.md

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Orphaned Engine Detection
    [Tags]    robot:skip
    [Documentation]    Test the orphaned engine instance detection
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. When create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    3. And wait for the instance is listed in instance manager's engine list
    ...    4. Then an orphan CR should be created
    ...    5. And the orphan CR's orphanType should be "engine-instance"
    ...    6. And the orphan CR's nodeID, and dataEngine, should be identical with the created engine instance
    ...    7. And in the orphan CR's parameters, the InstanceName should be the created engine instance's name
    ...    8. And in the orphan CR's parameters, the InstanceManager should be the instance manager's name
    ...    9. When delete the orphan engine CR
    ...    10. Then the orphaned engine instance should be deleted from instance manager CR
    Skip

Test Orphaned Replica Detection
    [Tags]    robot:skip
    [Documentation]    Test the orphaned replica instance detection
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. When create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    3. And wait for the instance is listed in instance manager's replica list
    ...    4. Then an orphan CR should be created
    ...    5. And the orphan CR's orphanType should be "replica-instance"
    ...    6. And the orphan CR's nodeID, and dataEngine, should be identical with the created replica instance
    ...    7. And in the orphan CR's parameters, the InstanceName should be the created replica instance's name
    ...    8. And in the orphan CR's parameters, the InstanceManager should be the instance manager's name
    ...    9. When delete the orphan replica CR
    ...    10. Then the orphaned replica instance should be deleted from instance manager CR
    Skip

Test Orphaned Instance Auto Deletion
    [Tags]    robot:skip
    [Documentation]    Test the orphaned instance can be deleted automatically
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. When create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    3. And create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    4. And wait engine-instance and replica-instance orphan CR creation
    ...    5. When modify the orphan-resource-auto-deletion setting to "engineInstance;replicaInstance"
    ...    6. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    ...    7. And no engine-instance and replica-instance orphan CRs in the cluster
    ...    8. When create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    9. And create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    10. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    ...    11. And no engine-instance and replica-instance orphan CRs in the cluster
    Skip

Test Orphaned Instance Deletion When Node Disconnect
    [Tags]    robot:skip
    [Documentation]    Test the orphan instance CRs should be removed when node disconnects from the cluster
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    3. And create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    4. When forcely shutdown the node
    ...    5. Then both the engine and replica orphan CRs should be deleted in 90 second
    Skip

Test Orphaned Instance Deletion During Node Eviction
    [Tags]    robot:skip
    [Documentation]    Test the orphaned instance should be deleted on evicted node
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    3. And create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    4. When enable the node's evictionRequested
    ...    5. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    Skip

