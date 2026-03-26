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

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Backing Image Basic Operation
    [Tags]    coretest
    [Documentation]    Test Backing Image APIs.
    Given Create backing image bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
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
        Given Create backing image bi-qcow2    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
        And Create backing image bi-raw    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
        And Setting deleting-confirmation-flag is set to true

        When Uninstall Longhorn

        Then Check all Longhorn CRD removed
        And Install Longhorn
    END

Test Backup Backing Image
    Given Create backing image bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
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
    Given Create backing image bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
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
    Given Create backing image bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=v1    minNumberOfCopies=3
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
    When Create backing image bi    url=    parameters=&{bi_params}    minNumberOfCopies=3    dataEngine=v1
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

    When Create backing image bi-large    url=https://cchien-backing-image.s3.us-west-1.amazonaws.com/400MB.qcow2    minNumberOfCopies=1
    And Download backing image bi-large    is_async=${True}
    Then Add Longhorn node 0 back
    And Wait for Longhorn node 0 up
    And Enable node 0 scheduling
    And Unevict evicted nodes

    When Wait backimg image bi-large download complete
    And Check backing image bi-large download file checksum matches
    And Verify longhorn manager logs does not contain but the pod became not ready after test start

Test Backing Image Non-existent Disk UUID Warning
    [Documentation]    Validate backing image generates warning log when referencing non-existent disk UUID
    ...    1. Create a backing image
    ...    2. Record original diskFileSpecMap
    ...    3. Add one non-existent UUID entry into spec.diskFileSpecMap
    ...    4. Verify warning log "Disk xxx is not ready or does not exist" appears in longhorn-manager pod
    ...    5. Restore original diskFileSpecMap and verify all disk file status are ready
    ...
    ...    Expected log: "Disk <random-uuid> is not ready or does not exist.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/4887
    Given Create backing image test-bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3

    ${original_diskFileSpecMap} =    Get diskFileSpecMap of backing image test-bi
    ${nonexistent_disk_uuid} =    Generate new uuid
    When Run command
    ...    kubectl patch backingimage test-bi -n longhorn-system --type=merge -p='{"spec":{"diskFileSpecMap":{"${nonexistent_disk_uuid}":{}}}}'

    Then Run command and wait for output
    ...    kubectl logs -n longhorn-system -l app=longhorn-manager --since=30s | grep "${nonexistent_disk_uuid}"
    ...    Disk ${nonexistent_disk_uuid} is not ready or does not exist

    When Run command
    ...    kubectl patch backingimage test-bi -n longhorn-system --type=json -p='[{"op":"replace","path":"/spec/diskFileSpecMap","value":${original_diskFileSpecMap}}]'
    Then Verify all disk file status of backing image test-bi are ready

Test Reduce Backing Image Min Number Of Copies
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12584
    ...    1. Create a backing image with min number of copies 3
    ...    2. Reduce the min number of copies to 1
    ...    3. Check unused backing image files are cleaned up after the waiting interval of backing image cleanup
    Given Setting backing-image-cleanup-wait-interval is set to 1
    And Create backing image bi    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
    And Wait for disk file status of backing image bi are expected    expected_ready_count=3

    When Update backing image bi min number of copies to 1
    And Wait for disk file status of backing image bi are expected    expected_ready_count=1

    Then Run command and expect output
    ...    kubectl logs -l app=longhorn-manager -n longhorn-system --since=3m
    ...    Cleaning up the unused file in disk.*failedDiskFileCount.*fileState.*handlingDiskFileCount.*minNumberOfCopies.*readyDiskFileCount

Test Volume Size Smaller Than Backing Image Virtual Size Should Show Error
    [Documentation]    Validates that when volume size is smaller than backing image virtual size,
    ...                - the longhorn manager log shows a clear error condition.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11673

    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    Given Get test start time
    # The virtual size of this image is 2.20 GiB, which is larger than the 2Gi PVC size used below.
    And Create backing image bi-ubuntu-focal    url=https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img    minNumberOfCopies=3    dataEngine=${DATA_ENGINE}
    And Wait for all disk file status of backing image bi-ubuntu-focal are ready
    When Create storageclass sc-backing-image-size-test with    backingImage=bi-ubuntu-focal    numberOfReplicas=3    dataEngine=${DATA_ENGINE}

    # Attempt to create PVC with size smaller than backing image virtualSize.
    # The admission webhook will reject the volume creation; no volume CR will be created.
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=sc-backing-image-size-test    storage_size=2Gi

    # Verify the admission webhook rejection is recorded in the longhorn-manager logs.
    Then Verify longhorn manager log contains volume size should be larger than the backing image size after test start

Test Volume Size Smaller Than Backing Image Virtual Size Should Show BackingImageIncompatible Condition
    [Documentation]    Validates that when volume size is smaller than backing image virtual size
    ...                - and the backing image is created on-demand, the volume CR's BackingImageIncompatible
    ...                - condition is set by the controller after the virtualSize becomes known.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11673

    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    # The virtual size of this image is ~2.20 GiB, which is larger than the 2Gi PVC size used below.
    Given Create storageclass sc-backing-image-size-test with    backingImage=bi-ubuntu-focal    backingImageDataSourceType=download    backingImageDataSourceParameters={"url": "https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img"}    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    # Create PVC with size smaller than backing image virtualSize.
    # The backing image does not exist yet (virtualSize=0), so the webhook allows volume CR creation.
    And Create persistentvolumeclaim 0    sc_name=sc-backing-image-size-test    storage_size=2Gi
    And Wait for volume of persistentvolumeclaim 0 to be created
    # Once the backing image finishes downloading, virtualSize becomes known.
    # The controller then detects the incompatibility and sets the condition.
    And Wait for all disk file status of backing image bi-ubuntu-focal are ready
    Then Wait for volume of persistentvolumeclaim 0 condition BackingImageIncompatible to be True    reason=BackingImageVirtualSizeTooLarge

