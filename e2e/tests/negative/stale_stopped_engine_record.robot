*** Settings ***
Documentation    Negative Test Cases
...
...              Reference: https://github.com/longhorn/longhorn/issues/13687

Test Tags    negative    volume    v1

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/engine.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Attach V1 Volume With Stale Stopped Engine Process Record On Target Node
    [Documentation]    Reproduce longhorn/longhorn#13687: a stale `stopped` v1 engine
    ...    process record left in an instance manager registry must not turn
    ...    createInstance into a silent no-op. Before the fix (v1.12.0/v1.12.1) the
    ...    volume stays stuck in `attaching` forever; after the fix the stale record is
    ...    reaped and the attach proceeds.
    ...
    ...    1. Given a healthy v1 RWO volume attached to node 0
    ...    2. And data written to the volume
    ...    3. When the volume is detached
    ...    4. And a stale stopped engine process record is injected into node 1 instance manager
    ...    5. And the volume is attached to node 1
    ...    6. Then the volume should become healthy (fails on v1.12.0/v1.12.1, passes with the fix)
    ...    7. And the volume data should be intact
    Given Create volume 0 with    dataEngine=v1    numberOfReplicas=2    accessMode=RWO
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    When Detach volume 0
    And Wait for volume 0 detached

    And Inject stale stopped v1 engine process for volume 0 on node 1
    And Volume 0 engine process should exist on node 1

    And Attach volume 0 to node 1
    Then Wait for volume 0 healthy
    And Volume 0 should be attached to node 1
    And Check volume 0 data is data 0
