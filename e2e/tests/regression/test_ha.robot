*** Settings ***
Documentation    HA Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/network.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/statefulset.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Disrupt Data Plane Traffic For Less Than Long Engine Replica Timeout
    Given Set setting engine-replica-timeout to 8
    And Set setting auto-salvage to false
    And Create storageclass longhorn-test with    dataEngine=v1
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Drop instance-manager egress traffic of statefulset 0 for 10 seconds without waiting for completion
    Then Write 1024 MB data to file data in statefulset 0
    And Wait for volume of statefulset 0 attached and degraded
    And Wait for volume of statefulset 0 healthy
    And Check statefulset 0 data in file data is intact
