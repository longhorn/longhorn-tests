*** Settings ***
Documentation    Engine Image Test Cases

Test Tags    regression    engine_image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/engine_image.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Replica Rebuilding After Engine Upgrade
    [Tags]    coretest
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support engine image upgrade
    END
    
    Given Create compatible engine image
    And Create volume 0
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    When Upgrade volume 0 engine to compatible engine image
    Then Delete volume 0 replica on node 1
    And Wait until volume 0 replica rebuilding started on node 1
    And Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Engine Upgrade With Extra Replicas
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support engine image upgrade
    END

    Given Create compatible engine image
    And Create volume 0    numberOfReplicas=3
    And Attach volume 0
    And Wait for volume 0 healthy
    When Update volume 0 replica count to 2
    Then Upgrade volume 0 engine to compatible engine image
