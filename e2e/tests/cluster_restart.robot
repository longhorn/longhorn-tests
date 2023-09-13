*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Restart Cluster While Workload Heavy Writing
    Create deployment 0 with rwo volume
    Create deployment 1 with rwx volume
    Create statefulset 0 with rwo volume
    Create statefulset 1 with rwx volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Keep writing data to deployment 0
        Keep writing data to deployment 1
        Keep writing data to statefulset 0
        Keep writing data to statefulset 1
        Restart cluster
        Check deployment 0 works
        Check deployment 1 works
        Check statefulset 0 works
        Check statefulset 1 works
    END