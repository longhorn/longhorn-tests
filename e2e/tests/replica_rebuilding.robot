*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Reboot Volume Node While Replica Rebuilding
    Given Create a volume with 5 GB and 3 replicas
    And Write data to the volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on volume node to trigger replica rebuilding
        And During replica rebuilding, reboot volume node

        Then Wait until replica on volume node rebuilt
        And Check data is intact
    END

Reboot Replica Node While Replica Rebuilding
    Given Create a volume with 5 GB and 3 replicas
    And Write data to the volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on replica node to trigger replica rebuilding
        And During replica rebuilding, reboot replica node

        Then Wait until replica on replica node rebuilt
        And Check data is intact
    END
