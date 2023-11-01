*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
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
        And Stress the CPU of all volume nodes

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

Stress Volume Node CPU When Volume Is Online Expanding
    @{data_checksum_list} =    Create List
    Set Test Variable    ${data_checksum_list}

    Given Create statefulset 0 with rwo volume
    And Write 1024 MB data to statefulset 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Stress the CPU of all volume nodes
        When Expand statefulset 0 volume by 100 MiB

        Then Wait for statefulset 0 volume size expanded
        And Check statefulset 0 data is intact
    END

Stress Volume Node CPU When Volume Is Offline Expanding
    @{data_checksum_list} =    Create List
    Set Test Variable    ${data_checksum_list}

    Given Create statefulset 0 with rwo volume
    And Write 1024 MB data to statefulset 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Scale down statefulset 0 to detach volume
        And Stress the CPU of all worker nodes

        When Expand statefulset 0 volume by 100 MiB

        Then Wait for statefulset 0 volume size expanded
        And Scale up statefulset 0 to attach volume
        And Check statefulset 0 data is intact
    END
