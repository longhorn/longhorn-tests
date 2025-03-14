*** Settings ***
Documentation    Snapshot Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource

Test Setup   Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Volume Snapshot Checksum When Healthy Replicas More Then 1
    [Tags]    volume setting snapshot
    [Documentation]
    ...    This test validates that snapshot checksum calculation is performed when the number of healthy replicas is more than 1.
    
    Given Set setting snapshot-data-integrity-immediate-check-after-snapshot-creation to true
    And Create volume 0 with    size=100Mi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}

    When Attach volume 0
    And Wait for volume 0 healthy
    And Create snapshot 0 of volume 0

    Then Validate snapshot 0 is in volume 0 snapshot list
    And Validate snapshot 0 checksum of volume 0 is calculated within 60 seconds

Test Volume Snapshot Checksum Skipped When Less Than 2 Healthy Replicas
    [Tags]    volume setting snapshot
    [Documentation]
    ...    This test validates that snapshot checksum calculation is skipped when the number of healthy replicas is less than 2.

    Given Set setting snapshot-data-integrity-immediate-check-after-snapshot-creation to true
    And Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create volume 0 with    size=100Mi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}

    When Attach volume 0
    And Wait for volume 0 degraded
    And Create snapshot 0 of volume 0

    Then Validate snapshot 0 is in volume 0 snapshot list
    And Validate snapshot 0 checksum of volume 0 is skipped for 60 seconds
