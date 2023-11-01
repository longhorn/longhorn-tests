*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource
Resource    ../keywords/recurring_job.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Reboot Volume Node While Heavy Writing And Recurring Jobs Exist
    Given Create volume 0 with 2 GB and 1 replicas
    And Create volume 1 with 2 GB and 3 replicas
    And Keep writing data to volume 0
    And Keep Writing data to volume 1
    And Create snapshot and backup recurring job for volume 0
    And Create snapshot and backup recurring job for volume 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Reboot volume 0 volume node

        Then Check recurring jobs for volume 0 work
        And Check recurring jobs for volume 1 work
        And Check volume 0 works
        And Check volume 1 works
    END

Reboot Replica Node While Heavy Writing And Recurring Jobs Exist
    Given Create volume 0 with 2 GB and 1 replicas
    And Create volume 1 with 2 GB and 3 replicas
    And Keep Writing data to volume 0
    And Keep Writing data to volume 1
    And Create snapshot and backup recurring job for volume 0
    And Create snapshot and backup recurring job for volume 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Reboot volume 1 replica node

        Then Check recurring jobs for volume 0 work
        And Check recurring jobs for volume 1 work
        And Check volume 0 works
        And Check volume 1 works
    END
