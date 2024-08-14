*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/common.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/stress.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***

Stress Volume Node Memory When Replica Is Rebuilding
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3
    And Attach volume 0
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on volume node
        And Wait until volume 0 replica rebuilding started on volume node
        And Stress memory of node with volume 0

        Then Wait until volume 0 replica rebuilding completed on volume node
        And Check volume 0 data is intact
    END

Stress Volume Node Memory When Volume Is Detaching and Attaching
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3
    And Attach volume 0
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stress memory of node with volume 0

        And Detach volume 0
        And Attach volume 0
        And Wait for volume 0 healthy
        Then Check volume 0 data is intact
    END

Stress Volume Node Memory When Volume Is Online Expanding
    Given Create statefulset 0 using RWO volume
    And Write 1024 MB data to file 0.txt in statefulset 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Stress memory of volume nodes

        When Expand statefulset 0 volume by 100 MiB

        Then Wait for statefulset 0 volume size expanded
        And Check statefulset 0 data in file 0.txt is intact
    END

Stress Volume Node Memory When Volume Is Offline Expanding
    Given Create statefulset 0 using RWO volume
    And Write 1024 MB data to file 0.txt in statefulset 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Scale down statefulset 0 to detach volume
        And Stress memory of all worker nodes

        When Expand statefulset 0 volume by 100 MiB

        Then Wait for statefulset 0 volume size expanded
        And Wait for statefulset 0 volume detached
        And Scale up statefulset 0 to attach volume
        And Wait for volume of statefulset 0 healthy
        And Check statefulset 0 data in file 0.txt is intact
    END
