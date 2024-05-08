*** Settings ***
Documentation    Basic Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Keywords ***
Create volume with invalid name should fail
  [Arguments]    ${invalid_volume_name}
  Given Create volume     ${invalid_volume_name}
  Then No volume created

*** Test Cases ***
Test Invalid Volume Name
    [Tags]    coretest
    [Documentation]    Test invalid volume name
    [Template]    Create volume with invalid name should fail
        wrong_volume-name-1.0
        wrong_volume-name

Test Volume Basic
    [Tags]    coretest
    [Documentation]    Test basic volume operations
    ...
    ...                1. Create a volume and attach to the current node, then check volume states
    ...                2. Write then read back to check volume data
    Given Create volume 0 with 2 GB and 3 replicas
    When Attach volume 0
    And Wait for volume 0 healthy

    When Write data to volume 0
    Then Check volume 0 data is intact

    And Detach volume 0
    And Delete volume 0

Test Snapshot
    [Tags]    coretest
    [Documentation]    Test snapshot operations
    Given Create volume 0
    When Attach volume 0
    And Wait for volume 0 healthy

    And Create snapshot 0 of volume 0

    And Write data 1 to volume 0
    And Create snapshot 1 of volume 0

    And Write data 2 to volume 0
    And Create snapshot 2 of volume 0

    Then Validate snapshot 0 is parent of snapshot 1 in volume 0 snapshot list
    And Validate snapshot 1 is parent of snapshot 2 in volume 0 snapshot list
    And Validate snapshot 2 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 2 of volume 0
    Then Validate snapshot 2 is in volume 0 snapshot list
    And Validate snapshot 2 is marked as removed in volume 0 snapshot list
    And Check volume 0 data is data 2

    When Detach volume 0
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy

    And Revert volume 0 to snapshot 1
    And Detach volume 0
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 1
    And Validate snapshot 1 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 1 of volume 0
    And Delete snapshot 0 of volume 0

    And Purge volume 0 snapshot
    Then Validate snapshot 0 is not in volume 0 snapshot list
    And Validate snapshot 1 is in volume 0 snapshot list
    And Validate snapshot 1 is marked as removed in volume 0 snapshot list
    And Validate snapshot 2 is not in volume 0 snapshot list

    And Check volume 0 data is data 1
