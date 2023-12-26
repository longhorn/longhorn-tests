*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Delete Replica While Replica Rebuilding
    Given Create a volume with 2 GB and 3 replicas
    And Write data to the volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica 0 to trigger replica 0 rebuilding
        And During replica 0 rebuilding, delete replica 1
        And Wait until replica 0 rebuilt, delete replica 2

        Then Check data is intact
        And Wait until all replicas rebuilt
    END
