*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource

Test setup    set_test_environment
Test Teardown    cleanup_resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Reboot Volume Node While Replica Rebuilding
    Create a volume with 5 GB and 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica on volume node to trigger replica rebuilding
        During replica rebuilding, reboot volume node
        Wait until replica on volume node rebuilt
        Check data is intact
    END

Reboot Replica Node While Replica Rebuilding
    Create a volume with 5 GB and 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica on replica node to trigger replica rebuilding
        During replica rebuilding, reboot replica node
        Wait until replica on replica node rebuilt
        Check data is intact
    END