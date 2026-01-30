*** Settings ***
Documentation    Manual Test Cases
Test Tags    upgrade    negative    backing-image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
System upgrade with compatible backing image manager image
    [Documentation]    1. Deploy Longhorn. Then set `Concurrent Automatic Engine Upgrade Per Node Limit` to a positive value to enable volume engine auto upgrade.
    ...                2. Create 2 backing images: a large one and a small one. Longhorn will start preparing the 1st file for both backing image immediately via launching backing image data source pods.
    ...                3. Wait for the small backing image being ready in the 1st disk. Then create and attach volumes with the backing image.
    ...                4. Wait for volumes attachment. Verify the backing image content then write random data in the volumes.
    ...                5. Wait for the large backing image being ready in the 1st disk. Then create and attach one more volume with this large backing image.
    ...                6. Before the large backing image is synced to other nodes and the volume becomes attached, upgrade the whole Longhorn system:
    ...                    1. A new engine image will be used.
    ...                    2. The default backing image manager image will be updated.
    ...                    3. The new longhorn manager is compatible with the old backing image manager.
    ...                7. Wait for system upgrade complete. Then verify:
    ...                    1. All old backing image manager and the related pod will be cleaned up automatically after the current downloading is complete. And the existing backing image files won't be removed.
    ...                    2. New default backing image manager will take over all backing image ownerships and show the info in the status map:
    ...                    3. All backing image files are ready on each nodes.
    ...                    4. All attached volumes still work fine without replica crash, and the content is correct in the volumes after the upgrade.
    ...                    5. The last volume get attached successfully without replica crash, and the content is correct.
    ...                8. Verify volumes and backing images can be deleted.
    ...
    ...                https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/backing-image-during-upgrade/
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    ${BACKING_IMAGE_MANAGER_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE
    ${ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    When Install Longhorn stable version
    And Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 3

    When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=3
    FOR    ${i}    IN RANGE    2
        And Create volume ${i} with    size=3Gi    backingImage=bi
        And Create persistentvolume for volume ${i}
        And Create persistentvolumeclaim for volume ${i}
        And Create pod vol-${i}-pod-bi using volume ${i}
        Then Wait for volume ${i} healthy
        And Check file guests/catparrot.gif exists in pod vol-${i}-pod-bi
        And Write 1024 MB data to file data.txt in pod vol-${i}-pod-bi
    END

    When Create backing image bi-large with    url=https://cchien-backing-image.s3.us-west-1.amazonaws.com/400MB.qcow2    minNumberOfCopies=1
    FOR    ${i}    IN RANGE    2    4
        Then Create volume ${i} with    size=3Gi    backingImage=bi-large
        And Create persistentvolume for volume ${i}
        And Create persistentvolumeclaim for volume ${i}
    END
    And Create pod vol-2-pod-bi using volume 2
    And Create pod vol-3-pod-bi using volume 3

    When Upgrade Longhorn to custom version
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Wait for volume 2 healthy
    And Wait for volume 3 healthy

    When Wait for Longhorn components all running
    And Verify volume 0 is using engine image ${ENGINE_IMAGE}
    And Verify volume 1 is using engine image ${ENGINE_IMAGE}
    And Verify volume 2 is using engine image ${ENGINE_IMAGE}
    And Verify volume 3 is using engine image ${ENGINE_IMAGE}

    When Check longhorn backing image manager image is ${BACKING_IMAGE_MANAGER_IMAGE}
    And Verify all disk file status of backing image bi are ready
    And Verify all disk file status of backing image bi-large are ready

    When Check file guests/catparrot.gif exists in pod vol-0-pod-bi
    And Check file guests/catparrot.gif exists in pod vol-1-pod-bi
    And Check file 400MB.txt exists in pod vol-2-pod-bi
    And Check file 400MB.txt exists in pod vol-3-pod-bi

    When Write 1024 MB data to file data.txt in pod vol-2-pod-bi
    And Write 1024 MB data to file data.txt in pod vol-3-pod-bi
    Then Check pod vol-0-pod-bi data in file data.txt is intact
    And Check pod vol-1-pod-bi data in file data.txt is intact
    And Check pod vol-2-pod-bi data in file data.txt is intact
    And Check pod vol-3-pod-bi data in file data.txt is intact

System upgrade with incompatible backing image manager image
    [Documentation]    1. Deploy Longhorn.
    ...                2. Create a backing images. Wait for the backing image being ready in the 1st disk.
    ...                3. Create and attach volumes with the backing image.
    ...                4. Wait for volumes attachment. Verify the backing image content then write random data in the volumes.
    ...                5. Upgrade the whole Longhorn system:
    ...                    1. The default backing image manager image will be updated.
    ...                    2. The new longhorn manager is not compatible with the old backing image manager.
    ...                6. Wait for system upgrade complete. Then verify:
    ...                    1. All old incompatible backing image manager and the related pod will be cleaned up automatically.
    ...                    2. New default backing image manager will take over all backing image ownerships and show the info in the status map.
    ...                    3. All attached volumes still work fine without replica crash, and the content is correct in the volumes during/after the upgrade.
    ...
    ...                https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/backing-image-during-upgrade/
    Skip    After upgrade path enforcement was introduced in v1.5.0, this test case became a corner case and is now rarely executed.

System upgrade with the same backing image manager image
    [Documentation]    1. Deploy Longhorn.
    ...                2. Create a backing images. Wait for the backing image being ready in the 1st disk.
    ...                3. Create and attach volumes with the backing image. Wait for all disk files of the backing image being ready.
    ...                4. Run kubectl -n longhorn system get pod -w in a separate session.
    ...                5. Upgrade Longhorn manager but with the backing image manager image unchanged. (Actually we can mock this upgrade by removing all longhorn manager pods simultaneously.)
    ...                6. After the longhorn manager pods restart, Verify there is no backing image data source pod launched for the backing image in the output of step4.
    ...                7. Repeat step4 ~ step8 for 10 times.
    ...
    ...                https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/backing-image-during-upgrade/
    ${BACKING_IMAGE_MANAGER_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE

    When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    minNumberOfCopies=1
    And Create volume 0 with    backingImage=bi
    And Create volume 1 with    backingImage=bi
    Then Attach volume 0
    And Attach volume 1
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Verify all disk file status of backing image bi are ready

    FOR    ${i}    IN RANGE    10
        When Delete Longhorn DaemonSet longhorn-manager pod on all nodes simultaneously
        And No backimg image data source pod exist
        Then Wait for Longhorn components all running
        And Wait for all disk file status of backing image bi are ready
    END
