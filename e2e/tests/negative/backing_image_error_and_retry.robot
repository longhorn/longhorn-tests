*** Settings ***
Documentation    Backing Image Test Cases

Test Tags    manual    backing_image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/backup_backing_image.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/node.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Retry interval should match expected backoff window
    [Arguments]    ${recreation_time}    ${creation_time}    ${retry_times}
    ${recreation_time}=    Convert Date    ${recreation_time}    epoch
    ${creation_time}=    Convert Date    ${creation_time}    epoch
    ${elapsed}=    Evaluate    ${recreation_time} - ${creation_time}

    Log    Retry ${retry_times} pod recreated after ${elapsed} seconds
    Should Be True    ${elapsed} > 60
    # Max retry interval is 300s; extra 60s tolerance added for scheduling timing variations
    Should Be True    ${elapsed} <= 360

*** Test Cases ***
Backing image with an invalid URL schema
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/backing-image-error-reporting-and-retry/    
    ...                - Create a backing image via a invalid download URL.
    ...                - Wait for the download start. The backing image data source pod, should be cleaned up after download fail.    
    ...                - The corresponding and only entry in the disk file status should be failed. 
    ...                  The error message in this entry should explain why the downloading or the pod becomes failed.
    ...                - Check if there is a backoff window for the downloading retry. The initial duration is 1 minute. The max interval is 5 minute.
    Given Create backing image bi-test with    url=httpsinvalid://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=${DATA_ENGINE}    minNumberOfCopies=3    wait=False
    ${creation_time}=     Wait backimg image bi-test data source pod created
    And Wait for all disk file status of backing image bi-test are failed
    And Wait for all disk file status of backing image bi-test are failed-and-cleanup
    And Wait backing image data source pod terminated

    FOR    ${i}    IN RANGE    3
        ${recreation_time}=    Wait backimg image bi-test data source pod created
        Then Retry interval should match expected backoff window   ${recreation_time}    ${creation_time}    ${i}
        And Wait for all disk file status of backing image bi-test are failed
        And Wait for all disk file status of backing image bi-test are failed-and-cleanup
        And Disk file message of backing image bi-test should contain failed to process sync file
        And Wait backing image data source pod terminated
        ${creation_time}=    Set Variable    ${recreation_time}
    END

Backing image with sync failure
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/backing-image-error-reporting-and-retry/
    ...                - Create a backing image. Then create and attach a volume using this backing image
    ...                - Exec into one of the worker node, remove the files in that backing image directory and set the directory as immutable
    ...                - Monitor the backing-image-manager pod log. Verify the backoff works for the sync retry as well.
    ...                - Unset the immutable flag for the backing image directory. Then the retry should succeed, and the volume should become healthy
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    Given Create backing image bi-test with    url=https://longhorn-backing-image.s3.dualstack.us-west-1.amazonaws.com/parrot.qcow2    dataEngine=${DATA_ENGINE}    minNumberOfCopies=3
    When Create volume 0 with    backingImage=bi-test    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    When Get test start time
    And Remove backing image bi-test files and set immutable on node 1
    And Wait for volume 0 degraded
    And Sleep    5
    And Verify backing image manager log on node 1 contain failed to process sync file after test start
    And Verify backing image manager log on node 1 contain prepare to sync backing image after test start

    When Unset backing image bi-test folder immutable on node 1    
    And Wait for volume 0 healthy
    And Verify all disk file status of backing image bi-test are ready
