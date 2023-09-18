*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Delete Replica While Replica Rebuilding
    Create a volume with 2 GB and 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica 0 to trigger replica 0 rebuilding
        During replica 0 rebuilding, delete replica 1
        Wait until replica 0 rebuilt, delete replica 2
        Check data is intact
        Wait until all replicas rebuilt
    END