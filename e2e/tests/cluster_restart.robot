*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}    0

*** Test Cases ***
Restart Cluster While Workload Heavy Writing
    Given Create deployment 0 with rwo volume
    And Create deployment 1 with rwx volume
    And Create deployment 2 with rwo and strict-local volume
    And Create statefulset 0 with rwo volume
    And Create statefulset 1 with rwx volume
    And Create statefulset 2 with rwo and strict-local volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to deployment 0
        And Keep writing data to deployment 1
        And Keep writing data to deployment 2
        And Keep writing data to statefulset 0
        And Keep writing data to statefulset 1
        And Keep writing data to statefulset 2

        When Restart cluster

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END
