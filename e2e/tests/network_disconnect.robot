*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/common.resource
Resource    ../keywords/network.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${LATENCY_IN_MS}    0
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Disconnect Volume Node Network While Workload Heavy Writing
    Given Create statefulset 0 using RWO volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
<<<<<<< HEAD
        When Disconnect volume node network of statefulset 0 for 10 seconds
=======
        And Keep writing data to pod of statefulset 1
        When Disconnect volume nodes network for 20 seconds    statefulset 0    statefulset 1
>>>>>>> bdce3880 (fix: adjust disconnect time for negative test)
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable
        Then Check statefulset 0 works
    END

Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create statefulset 0 using RWO volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        When Disconnect volume node network of statefulset 0 for 360 seconds
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable
        Then Check statefulset 0 works
    END