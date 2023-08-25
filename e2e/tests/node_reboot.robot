*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource

Test setup    set_test_environment
Test Teardown    cleanup_resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Replica Rebuilding While Volume Attached Node Reboot
    Create a volume 5 GB with 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica on the volume attached node to trigger replica rebuilding
        During replica rebuilding, reboot the volume attached node
        Wait until replica on the volume attached node rebuilt
        Check data is intact
    END

Replica Rebuilding While Replica Node Reboot
    Create a volume 5 GB with 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica to trigger replica rebuilding
        During replica rebuilding, reboot the replica node
        Wait until replica rebuilt
        Check data is intact
    END