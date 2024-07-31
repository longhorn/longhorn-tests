*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/common.resource
Resource    ../keywords/network.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${LATENCY_IN_MS}    0
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${RWX_VOLUME_FAST_FAILOVER}    false
${DATA_ENGINE}    v1

*** Test Cases ***
Disconnect Volume Node Network While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        When Disconnect volume nodes network for 10 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1
        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        When Disconnect volume nodes network for 360 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1
        Then Check statefulset 0 works
        And Check statefulset 1 works
    END