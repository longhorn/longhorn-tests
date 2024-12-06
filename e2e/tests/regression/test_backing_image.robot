*** Settings ***
Documentation    Backing Image Test Cases

Test Tags    regression    backing_image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Backing Image Basic Operation
    [Tags]    coretest
    [Documentation]    Test Backing Image APIs.
    Given Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    When Create volume 0 with    backingImage=bi    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact
    And Verify all disk file status of backing image bi are ready
    And Verify clean up backing image bi from a disk will fail
    And Verify delete backing image bi will fail
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0
    And Clean up backing image bi from a disk
    And Delete backing image bi
