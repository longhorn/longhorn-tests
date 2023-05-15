*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/volume.resource

Test setup    set_test_name    ${TEST NAME}

Test Teardown    cleanup_resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Replica Rebuilding While Replica Deletion
    Create a volume 2 GB with 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Delete replica 0 to trigger replica 0 rebuilding
        During replica 0 rebuilding, delete replica 1
        Wait until replica 0 rebuilt, delete replica 2
        Check data is intact
        Wait until all replicas rebuilt
    END
