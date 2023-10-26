*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***

Stress Volume Node CPU When Replica Is Rebuilding
    Given Create a volume with 5 GB and 3 replicas
    And Write data to the volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on volume node to trigger replica rebuilding
        And Stress volume node cpu

        Then Wait until replica on volume node rebuilt
        And Check data is intact
    END


Stress Volume Node CPU When Volume Is Detaching and Attaching
    Given Create a volume with 5 GB and 3 replicas
    And Write data to the volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stress volume node cpu

        And Detach volume from node
        And Attach volume to node

        And Check data is intact
    END
