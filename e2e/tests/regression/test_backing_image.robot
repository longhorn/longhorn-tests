*** Settings ***
Documentation    Backing Image Test Cases

Test Tags    regression    backing-image

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

*** Test Cases ***
Test Backing Image Basic Operation
    [Tags]    coretest
    [Documentation]    Test Backing Image APIs.
    Given Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    When Create volume 0 with    backingImage=bi
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact
    And Verify all disk file status of backing image bi are ready
    And Verify clean up backing image bi from a disk will fail
    And Verify delete backing image bi will fail
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0
    And Clean up backing image bi from a disk
    And Delete backing image bi

Test Uninstall When Backing Image Exists
    [Tags]    uninstall    backing image
    [Documentation]    Validates the uninstallation of Longhorn when backing
    ...                image exists.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/10044
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Given Create backing image bi-qcow2 with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
        And Create backing image bi-raw with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
        And Setting deleting-confirmation-flag is set to true

        When Uninstall Longhorn

        Then Check all Longhorn CRD removed
        And Install Longhorn
    END

Test Backup Backing Image
    Given Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    When Create backup backing image bi-backup for backing image bi
    Then Wait for backing image backup for backing image bi ready

Test Backing Image Download Timeout
    [Tags]    robot:skip
    [Documentation]    Test the backing image context timeout is enlarged to 30 sec
    ...
    ...    1. Given a backing image file ready for download
    ...    2. And create a backing image CR to download the given image
    ...    3. And wait for backing image data source pod get launched
    ...    4  When temporary block the download connection for 5 second
    ...    5. And resume the download connection
    ...    6. Then the backing image data source should be able to download the image without timeout error
    ...    7. When create a backing image CR to download the given image
    ...    8. And wait for backing image data source pod get launched
    ...    9  When temporary block the download connection for 35 second
    ...    10. And resume the download connection
    ...    11. Then the backing image data source should fail to download the image
    Skip

Test Evict Two Replicas Volume With Backing Image
    [Tags]    backing image
    [Documentation]    Validates that the Longhorn manager does not restart when evicting a replica
    ...                of a volume created from a backing image
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11034
    Given Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
    # To make sure replica node is node 1
    And Set node 2 with    allowScheduling=false    evictionRequested=false
    When Create volume 0 with    backingImage=bi    numberOfReplicas=2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Set node 2 with    allowScheduling=true    evictionRequested=false

    When Get test start time
    And Set node 1 with    allowScheduling=false    evictionRequested=true
    And Volume 0 should have 1 running replicas on node 2
    And Volume 0 should have 0 running replicas on node 1
    And Check longhorn manager pods not restarted after test start
