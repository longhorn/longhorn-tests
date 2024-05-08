*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Force Drain Volume Node While Replica Rebuilding
    Given Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuilding started on volume node
        And Force drain volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached to another node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact
    END

Force Drain Replica Node While Replica Rebuilding
    Given Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        And Force drain volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached to the original node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact
    END
