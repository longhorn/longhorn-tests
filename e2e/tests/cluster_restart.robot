*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}    0

*** Test Cases ***
Restart Cluster While Workload Heavy Writing
    Given Create persistentvolumeclaim 0 using RWO volume
    And Create persistentvolumeclaim 1 using RWX volume
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2
    And Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume
    And Create statefulset 2 using RWO volume with strict-local storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2

        When Restart cluster
        And Wait for longhorn ready
        And Wait for deployment 0 pods stable
        And Wait for deployment 1 pods stable
        And Wait for deployment 2 pods stable
        And Wait for statefulset 0 pods stable
        And Wait for statefulset 1 pods stable
        And Wait for statefulset 2 pods stable

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END
