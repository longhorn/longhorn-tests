*** Settings ***
Documentation    HA Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/network.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/statefulset.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Disrupt Data Plane Traffic For Less Than Long Engine Replica Timeout
    Given Setting engine-replica-timeout is set to {"v1":"15","v2":"15"}
    And Setting auto-salvage is set to false
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Drop instance-manager egress traffic of statefulset 0 for 25 seconds without waiting for completion
        Then Write 1024 MB data to file data in statefulset 0
        And Wait for volume of statefulset 0 attached and degraded
        And Wait for volume of statefulset 0 healthy
        And Check statefulset 0 data in file data is intact
    END

Don't Orphan Processes When Node Not Ready
    [Tags]    robot:skip
    [Documentation]    Don't orphan processes when a node becomes not ready.
    ...
    ...                1. Create a volume of any size and a number of replicas equal to the number of nodes.
    ...                2. Attach the volume to a node.
    ...                3. Stop kubelet on the attached node long enough the node to become not ready and its instance
    ...                   manager to have state unknown.
    ...                   NOTE: The timing is important here. The instance manager reaches state unknown after
    ...                   approximately 30 seconds. Approximately 6 minutes later, Kubernetes evicts most pods on the
    ...                   node, including the instance manager pod, so the instance manager transitions to state error.
    ...                   The remaining steps must be executed before this happens.
    ...                4. Detach the volume.
    ...                5. Verify that no instance-manager CR has a status.instanceEngines[<volume-name-e-...>].
    ...                6. Verify that no instance-manager CR has a status.instanceReplicas[<volume-name-r-...>].
    Skip
