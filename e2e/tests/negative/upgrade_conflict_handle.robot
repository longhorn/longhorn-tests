*** Settings ***
Documentation    Manual Test Cases
Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/recurringjob.resource
Library     DateTime

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Get test start time
    ${test_start_time}=    Get Current Date    result_format=datetime
    Log    ${test_start_time}
    Set Test Variable    ${test_start_time}

*** Test Cases ***
Test Stability of Longhorn with Large Workload
    ${NUM_VOLUMES} =    Set Variable    100
    ${NUM_VOLUMES_DETACH} =    Set Variable    10

    Given Set setting deleting-confirmation-flag to true
    And Get test start time
    
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    FOR    ${i}    IN RANGE    ${NUM_VOLUMES}
        And Create statefulset ${i} using RWO volume with longhorn-test storageclass and size 10 Mi
        And Write 1 MB data to file data.txt in statefulset ${i}
    END

    And Create snapshot recurringjob 0
    ...    groups=["default"]
    ...    cron=*/1 * * * *
    ...    concurrency=5
    ...    labels={"test":"recurringjob"}

    FOR    ${i}    IN RANGE    ${NUM_VOLUMES_DETACH}
        When Create backup ${i} for statefulset ${i} volume
        Then Scale down statefulset ${i} to detach volume
        And Scale up statefulset ${i} to attach volume
    END
            
    And Check longhorn manager pods not restarted after test start
   
Test Upgrade Stability with Large Workload
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    ${NUM_VOLUMES} =    Set Variable    100
    ${NUM_VOLUMES_DETACH} =    Set Variable    10

    Given Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And set_backupstore

    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    FOR    ${i}    IN RANGE    ${NUM_VOLUMES}
        And Create statefulset ${i} using RWO volume with longhorn-test storageclass and size 10 Mi
        And Write 1 MB data to file data.txt in statefulset ${i}
    END

    FOR    ${i}    IN RANGE    ${NUM_VOLUMES_DETACH}
        When Create backup ${i} for statefulset ${i} volume
        And Scale down statefulset ${i} to detach volume
    END

    And Create snapshot recurringjob 0
    ...    groups=["default"]
    ...    cron=*/1 * * * *
    ...    concurrency=5
    ...    labels={"test":"recurringjob"}

    When Upgrade Longhorn to custom version
    And Get test start time

    FOR    ${i}    IN RANGE    10
        When Scale down statefulset ${i} to detach volume
        And Scale up statefulset ${i} to attach volume
    END

    And Check longhorn manager pods not restarted after test start
