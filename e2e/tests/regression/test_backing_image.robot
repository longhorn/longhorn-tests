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
Resource    ../keywords/host.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

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
    [Tags]    uninstall
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

Test backing image handle node disk deleting events
    [Documentation]   Validates that the backing image manager and backing image disk files
    ...               are removed after a broken disk is removed from Longhorn node.
    ...
    ...               Issue: https://github.com/longhorn/longhorn/issues/10983
    Given Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=v1    minNumberOfCopies=3
    Then Record node 0 default disk uuid
    When Run command on node    0
    ...    rm /var/lib/longhorn/longhorn-disk.cfg
    Then Wait for node 0 default disk broken
    And Wait for backing image manager on node 0 unknown

    When Disable node 0 default disk
    And Delete node 0 default disk
    And Wait for backing image manager on node 0 terminated
    And Backing image bi should not have the removed disk in its DiskFileSpecMap

Test backing image download to local
    [Documentation]    Validates backimage can download to local successfully
    ...
    ...    1. Create and attach a volume (recommended volume size > 1Gi).
    ...    2. Write some data into the file then calculate the SHA512 checksum of the volume block device.
    ...    3. Create a backing image from the above volume. And wait for the 1st backing image file ready.
    ...    4. Download the backing image to local via UI (Clicking button Download in Operation list of the backing image). => Verify the downloaded file checksum is the same as the volume checksum & the backing image current checksum (when Exported Backing Image Type is raw).
    ...    5. Create and attach the volume with the backing image. Wait for the attachment complete.
    ...    6. Re-download the backing image to local. => Verify the downloaded file checksum still matches.
    Given Create volume vol-0 with    size=100Mi    dataEngine=v1
    And Attach volume vol-0
    And Wait for volume vol-0 healthy
    And Write 50 Mi data to volume vol-0

    &{bi_params} =    Create Dictionary    volume-name=vol-0   export-type=raw
    When Create backing image bi with    url=    parameters=&{bi_params}    minNumberOfCopies=3    dataEngine=v1
    And Download backing image bi
    And Check downloaded backing image bi data matches source backingimage
    And Check downloaded backing image bi data matches volume vol-0

    When Create volume vol-1 with    backingImage=bi    numberOfReplicas=3
    And Attach volume vol-1
    And Wait for volume vol-1 healthy
    And Download backing image bi
    And Check downloaded backing image bi data matches source backingimage

Test Node ID Change During Backing Image Creation
    [Documentation]    Validate node ID of backing image data source node changed when new node added
    ...    1. Delete longohorn node 0
    ...    2. Download a large backing image
    ...    3. While download in progress, add node 0 back
    ...    4. The download complete.
    ...    5. No error log "but the pod became not ready" in longhorn manager log
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/4887
    When Get test start time
    And Disable node 0 scheduling
    And Evict node 0
    And Delete Longhorn node 0

    When Create backing image bi-large with    url=https://cchien-backing-image.s3.us-west-1.amazonaws.com/400MB.qcow2    minNumberOfCopies=1
    And Download backing image bi-large    is_async=${True}
    Then Add Longhorn node 0 back
    And Wait for Longhorn node 0 up
    And Enable node 0 scheduling
    And Unevict evicted nodes

    When Wait backimg image bi-large download complete
    And Check backing image bi-large download file checksum matches
    And Verify longhorn manager logs does not contain but the pod became not ready after test start

Test Backing Image Size Mismatch - Volume Size Smaller Than Backing Image
    [Documentation]    Test that when volume size is smaller than backing image virtual size,
    ...                the system displays a clear error condition on the volume CR.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11673
    ...
    ...                1. Create a backing image with virtual size of 2.2GB (ubuntu-20.04-minimal-cloudimg-amd64.img)
    ...                2. Create a StorageClass with this backing image configured
    ...                3. Create a PVC requesting 2Gi storage (smaller than backing image virtual size)
    ...                4. Create a Pod using this PVC
    ...                5. Wait for volume creation
    ...                6. Wait for all replicas' WaitForBackingImage status to become false
    ...                7. Verify the volume CR contains a condition indicating backing image size mismatch
    ...                8. Verify the condition message clearly states that volume size is smaller than backing image virtual size
    ...                9. Verify the volume does not enter attached state
    Given Create backing image bi-size-test with    url=https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img    minNumberOfCopies=3
    And Create storageclass sc-bi-size-test with    backingImage=bi-size-test
    When Create persistentvolumeclaim 0    storage_size=2Gi    sc_name=sc-bi-size-test
    And Create pod 0 using persistentvolumeclaim 0
    And Wait for volume of persistentvolumeclaim 0 to be created

    # Wait for replicas to finish waiting for backing image
    And Wait for all replicas of volume of persistentvolumeclaim 0 WaitForBackingImage status to be False

    # Verify the volume has a scheduled condition with error message about size mismatch
    Then Volume of persistentvolumeclaim 0 should have condition scheduled
    And Volume of persistentvolumeclaim 0 condition scheduled should contain message volume size
    And Volume of persistentvolumeclaim 0 condition scheduled should contain message backing image

Test Backing Image Size Match - Volume Size Equal To Or Greater Than Backing Image
    [Documentation]    Test that when volume size is equal to or greater than backing image virtual size,
    ...                the volume works normally without size mismatch error.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11673
    ...
    ...                1. Create a backing image with virtual size of 2.2GB
    ...                2. Create a StorageClass with this backing image configured
    ...                3. Create a PVC requesting 3Gi storage (larger than backing image virtual size)
    ...                4. Create a Pod using this PVC
    ...                5. Wait for volume to become healthy
    ...                6. Verify the volume CR does not contain a backing image size mismatch error
    ...                7. Verify the volume successfully enters attached state
    Given Create backing image bi-size-ok with    url=https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img    minNumberOfCopies=3
    And Create storageclass sc-bi-size-ok with    backingImage=bi-size-ok
    When Create persistentvolumeclaim 1    storage_size=3Gi    sc_name=sc-bi-size-ok
    And Create pod 1 using persistentvolumeclaim 1
    And Wait for volume of persistentvolumeclaim 1 healthy

    # Verify no scheduling error condition exists
    Then Wait for volume of persistentvolumeclaim 1 condition scheduled to be true
