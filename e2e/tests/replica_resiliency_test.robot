*** Settings ***
Documentation       Negative Test Cases

Resource            ../keywords/common.resource
Resource            ../keywords/replica.resource
Resource            ../keywords/volume.resource

Suite Setup         set_test_suite_environment
Test Setup          set_test_environment    ${TEST NAME}
Test Teardown       Cleanup resource and resume state


*** Variables ***
${Gi}=                  2**30
${LOOP_COUNT}           1
${volume_size_gb}=      2
${volume_type}=         RWO


*** Test Cases ***
Replica Rebuilding While Replica Deletion
    ${number_of_replicas}=    Convert To Integer    3
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Wait for all replicas to be created
    And Attach volume to node 1
    And Write data into mount point

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete the replica on node 1
        And Wait for replica on node 1 start rebuilding
        And Delete the replica on node 2
        And Wait for replica on node 1 complete rebuilding
        And Delete the replica on node 3

        Then Check data is intact
        And Wait until all replicas rebuilt
    END
    [Teardown]    Teardown
