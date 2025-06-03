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
    ...    2. And a ready volume attached on node A
    ...    3. And save the spec of engine on node A
    ...    4. When suspend node A to simulate the temporary network outage
    ...    5  And detach and delete the volume
    ...    6. And resume node A to simulate the network resume
    ...    7. Then an orphan CRs with orphanType "engine-instance" should be created
    ...    8. And the nodeID, and dataEngine, should be identical with the engine instance
    ...    9. And in the orphan CR's parameters, the InstanceName should be the instance's name
    ...    10. And in the orphan CR's parameters, the InstanceManager should be the instance manager's name
    ...    11. And in the orphan CR's parameters, the process UUID should be recorded
    ...    12. When delete the orphan engine CR
    ...    13. Then the orphaned engine instance should be deleted from instance manager CR
    Skip

Test Orphaned Replica Detection
    [Tags]    robot:skip
    [Documentation]    Test the orphaned replica instance detection
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And a ready volume attached on node A
    ...    3. And save the spec of replica on node A
    ...    4. When suspend node A to simulate the temporary network outage
    ...    5  And detach and delete the volume
    ...    6. And resume node A to simulate the network resume
    ...    7. Then an orphan CRs with orphanType "replica-instance" should be created
    ...    8. And the nodeID, and dataEngine, should be identical with the replica instance
    ...    9. And in the orphan CR's parameters, the InstanceName should be the instance's name
    ...    10. And in the orphan CR's parameters, the InstanceManager should be the instance manager's name
    ...    11. And in the orphan CR's parameters, the process UUID should be recorded
    ...    12. When delete the orphan replica CR
    ...    13. Then the orphaned replica instance should be deleted from instance manager CR
    Skip

Test Orphaned Instance Auto Deletion
    [Tags]    robot:skip
    [Documentation]    Test the orphaned instance can be deleted automatically
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And a ready volume attached on node A
    ...    3. When suspend node A to simulate the temporary network outage
    ...    4  And detach and delete the volume
    ...    5. And resume node A to simulate the network resume
    ...    6. And wait for engine-instance and replica-instance orphan CR creation
    ...    7. When modify the orphan-resource-auto-deletion setting to "engineInstance;replicaInstance"
    ...    8. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    ...    9. And no engine-instance and replica-instance orphan CRs in the cluster
    ...    10. When create an orphaned engine instance with random name on instance manager without creating the engine CR
    ...    11. And create an orphaned replica instance with random name on instance manager without creating the replica CR
    ...    12. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    ...    13. And no engine-instance and replica-instance orphan CRs in the cluster
    Skip

Test Orphaned Instance Deletion When Node Disconnect
    [Tags]    robot:skip
    [Documentation]    Test the orphan instance CRs should be removed when node disconnects from the cluster
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And a ready volume attached on node A
    ...    3. And suspend node A to simulate the temporary network outage
    ...    4  And detach and delete the volume
    ...    5. And resume node A to simulate the network resume
    ...    6. And wait for engine-instance and replica-instance orphan CR creation
    ...    7. When forcely shutdown the node A
    ...    8. And wait for Longhorn node A offline
    ...    9. Then both the engine and replica orphan CRs should be deleted in 90 second
    Skip

Test Orphaned Instance Deletion During Node Eviction
    [Tags]    robot:skip
    [Documentation]    Test the orphaned instance should be deleted on evicted node
    ...
    ...    1. Given the cluster that the orphan-resource-auto-deletion setting is empty
    ...    2. And a ready volume attached on node A
    ...    3. And suspend node A to simulate the temporary network outage
    ...    4  And detach and delete the volume
    ...    5. And resume node A to simulate the network resume
    ...    6. And wait for engine-instance and replica-instance orphan CR creation
    ...    4. When enable the node's evictionRequested
    ...    5. Then both the created engine and replica instance should be deleted from instance manager in 90 second
    Skip

