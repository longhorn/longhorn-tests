*** Settings ***
Documentation    Backing Image Test Cases

Test Tags    manual    backing-image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/backup_backing_image.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/node.resource

Suite Setup    Skip If    '${DATA_ENGINE}' == 'v2'    reason=v2 data engine doesn't support backing image

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Backing image with sync failure
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/backing-image-error-reporting-and-retry/
    ...                - Create a backing image. Then create and attach a volume using this backing image
    ...                - Exec into one of the worker node, remove the files in that backing image directory and set the directory as immutable
    ...                - Monitor the backing-image-manager pod log. Verify the backoff works for the sync retry as well.
    ...                - Unset the immutable flag for the backing image directory. Then the retry should succeed, and the volume should become healthy
    Given Create backing image bi-test    url=https://longhorn-backing-image.s3.dualstack.us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
    When Create volume 0 with    backingImage=bi-test    numberOfReplicas=3
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
