*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Delete Volume Node While Replica Rebuilding
    Given Set node-down-pod-deletion-policy to do-nothing
    And Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 2048 MB data to file data in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuidling started on volume node
        And Delete volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached and unknown
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact
    END

Delete Replica Node While Replica Rebuilding
    Given Set node-down-pod-deletion-policy to do-nothing
    And Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 2048 MB data to file data in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuidling started on replica node
        And Delete volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached and degraded
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact
    END
