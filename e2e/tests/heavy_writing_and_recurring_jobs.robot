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

*** Test Cases ***
Reboot Volume Node While Heavy Writing And Recurring Jobs Exist
    Create volume 0 with size 2 GB and 1 replicas
    Create volume 1 with size 2 GB and 3 replicas
    Keep writing data to volume 0
    Keep Writing data to volume 1
    Create snapshot and backup recurring job for volume 0
    Create snapshot and backup recurring job for volume 1
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Reboot volume 0 volume node
        Check recurring jobs for volume 0 work
        Check recurring jobs for volume 1 work
        Check volume 0 works
        Check volume 1 works
    END

Reboot Replica Node While Heavy Writing And Recurring Jobs Exist
    Create volume 0 with size 2 GB and 1 replicas
    Create volume 1 with size 2 GB and 3 replicas
    Keep Writing data to volume 0
    Keep Writing data to volume 1
    Create snapshot and backup recurring job for volume 0
    Create snapshot and backup recurring job for volume 1
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Reboot volume 1 replica node
        Check recurring jobs for volume 0 work
        Check recurring jobs for volume 1 work
        Check volume 0 works
        Check volume 1 works
    END
