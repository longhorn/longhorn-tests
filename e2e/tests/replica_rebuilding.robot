*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/common.resource
Resource    ../keywords/workload.resource

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

Delete Volume Node While Replica Rebuilding
    Given Set node-down-pod-deletion-policy to do-nothing
    And Create deployment with rwo volume
    And Write 2048 MB data to deployment

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on volume node to trigger replica rebuilding
        And During replica rebuilding, delete volume node

        Then Wait for volume attached and unknown
        And Add deleted node back
        And Wait for volume attached and healthy
        And Wait for deployment stable
        And Check deployment data is intact
    END

Delete Replica Node While Replica Rebuilding
    Given Set node-down-pod-deletion-policy to do-nothing
    And Create deployment with rwo volume
    And Write 2048 MB data to deployment

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on replica node to trigger replica rebuilding
        And During replica rebuilding, delete replica node

        Then Wait for volume attached and degraded
        And Add deleted node back
        And Wait for volume attached and healthy
        And Check deployment data is intact
    END

Force Drain Volume Node While Replica Rebuilding
    And Create deployment with rwo volume
    And Write 2048 MB data to deployment

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on volume node to trigger replica rebuilding
        And Force Drain volume node

        Then Wait for volume attached and degraded
        And Uncordon volume node
        And Wait for volume attached and healthy
        And Wait for deployment stable
        And Check deployment data is intact
    END

Force Drain Replica Node While Replica Rebuilding
    And Create deployment with rwo volume
    And Write 2048 MB data to deployment

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica on replica node to trigger replica rebuilding
        And Force Drain replica node

        Then Wait for volume attached and degraded
        And Uncordon replica node
        And Wait for volume attached and healthy
        And Wait for deployment stable
        And Check deployment data is intact
    END
