*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource
Resource    ../keywords/kubelet.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Restart Volume Node Kubelet While Workload Heavy Writing
    Given Create statefulset 0 with rwo volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to statefulset 0
        When Stop volume node kubelet of statefulset 0 for 10 seconds
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 stable
        Then Check statefulset 0 works
    END

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create statefulset 0 with rwo volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to statefulset 0
        When Stop volume node kubelet of statefulset 0 for 360 seconds
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 stable
        Then Check statefulset 0 works
    END
