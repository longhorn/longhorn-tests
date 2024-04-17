*** Settings ***
Documentation    Basic Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Volume Basic Test
    [Tags]  coretest
    [Documentation]    Test basic volume operations
    ...
    ...                1. Check volume name and parameter
    ...                2. Create a volume and attach to the current node, then check volume states
    ...                3. Check soft anti-affinity rule
    ...                4. Write then read back to check volume data
    When Create volume wrong_volume-name-1.0
    Then No volume created

    When Create volume wrong_volume-name
    Then No volume created

    When Create volume 0 with frontend invalid_frontend
    Then No volume created

    When Create volume 0 with 2 GB and 3 replicas
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Validate volume 0 replicas anti-affinity

    And Write data to volume 0
    Then Check volume 0 data is intact

    And Detach volume 0
    And Delete volume 0
