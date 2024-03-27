*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
#TODO
# test cases in this file don't use pvc related keywords
# but it needs to import persistentvolumeclaim.resource
# just because of the cleanup function
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/volume.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Delete Replica While Replica Rebuilding
    Given Create volume 0 with 2 GB and 3 replicas
    And Attach volume 0
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on volume node
        And Wait until volume 0 replica rebuilding started on volume node
        And Delete volume 0 replica on replica node
        And Wait until volume 0 replica rebuilding completed on volume node
        And Delete volume 0 replica on test pod node

        Then Check volume 0 data is intact
        And Wait until volume 0 replicas rebuilding completed
    END

Reboot Volume Node While Replica Rebuilding
    Given Create volume 0 with 5 GB and 3 replicas
    And Attach volume 0
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on volume node
        And Wait until volume 0 replica rebuilding started on volume node
        And Reboot volume 0 volume node
        And Wait for volume 0 healthy

        Then Wait until volume 0 replica rebuilding completed on volume node
        And Check volume 0 data is intact
    END

Reboot Replica Node While Replica Rebuilding
    Given Create volume 0 with 5 GB and 3 replicas
    And Attach volume 0
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on replica node
        And Wait until volume 0 replica rebuilding started on replica node
        And Reboot volume 0 replica node
        And Wait for volume 0 healthy

        Then Wait until volume 0 replica rebuilding completed on replica node
        And Check volume 0 data is intact
    END
