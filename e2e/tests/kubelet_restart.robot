*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Restart Volume Node Kubelet While Workload Heavy Writing
    Given Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1

        When Stop volume nodes kubelet for 10 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1

        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1

        When Stop volume nodes kubelet for 360 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1

        Then Check statefulset 0 works
        And Check statefulset 1 works
    END
