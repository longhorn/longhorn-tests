*** Settings ***
Documentation    Manual Test Cases
Test Tags    upgrade    negative

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

    IF    '${DATA_ENGINE}' == 'v2'
        Fail    Test case not support for v2 data engine
    END

    ${BACKING_IMAGE_MANAGER_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE
    ${ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE

    Given Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    When Install Longhorn stable version
    And Set setting concurrent-automatic-engine-upgrade-per-node-limit to 3

    When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=${DATA_ENGINE}    minNumberOfCopies=3
    And Create volume 0 with    backingImage=bi    dataEngine=${DATA_ENGINE}
    And Create volume 1 with    backingImage=bi    dataEngine=${DATA_ENGINE}
    Then Attach volume 0
    And Attach volume 1
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Write data to volume 0
    And Write data to volume 1

    When Create backing image bi-large with    url=https://github.com/rancher/k3os/releases/download/v0.11.0/k3os-amd64.iso    dataEngine=${DATA_ENGINE}    minNumberOfCopies=1
    And Create volume 2 with    backingImage=bi-large    dataEngine=${DATA_ENGINE}
    And Create volume 3 with    backingImage=bi-large    dataEngine=${DATA_ENGINE}
    And Attach volume 2 without waiting for attachment
    And Attach volume 3 without waiting for attachment

    When Upgrade Longhorn to custom version
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Wait for volume 2 healthy
    And Wait for volume 3 healthy

    IF    '${DATA_ENGINE}' == 'v1'
        And Verify volume 0 is using engine image ${ENGINE_IMAGE}
        And Verify volume 1 is using engine image ${ENGINE_IMAGE}
        And Verify volume 2 is using engine image ${ENGINE_IMAGE}
        And Verify volume 3 is using engine image ${ENGINE_IMAGE}
    END

    When Check longhorn backing image manager image is ${BACKING_IMAGE_MANAGER_IMAGE}
    And Verify all disk file status of backing image bi are ready
    And Verify all disk file status of backing image bi-large are ready

    When Wait for Longhorn components all running
    And Then Check volume 0 data is intact
    And Then Check volume 1 data is intact
    Then Write data to volume 2
    And Write data to volume 3
    And Then Check volume 2 data is intact
    And Then Check volume 3 data is intact

    When Delete volume 0
    And Delete volume 1
    And Delete volume 2
    And Delete volume 3
    And Delete backing image bi
    And Delete backing image bi-large

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
    ...                6. Check at latest one disk file status of the backing image becomes unknown then ready during the longhorn manager pods termination and restart. (May need to refresh the UI page after restart.)
    ...                7. After the longhorn manager pods restart, Verify there is no backing image data source pod launched for the backing image in the output of step4.
    ...                8. Repeat step4 ~ step8 for 10 times.
    ...    
    ...                https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/backing-image-during-upgrade/
    ${BACKING_IMAGE_MANAGER_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE
    IF    '${DATA_ENGINE}' == 'v2'
        Fail    Test case not support for v2 data engine
    END

    When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=${DATA_ENGINE}    minNumberOfCopies=1
    And Create volume 0 with    backingImage=bi    dataEngine=${DATA_ENGINE}
    And Create volume 1 with    backingImage=bi    dataEngine=${DATA_ENGINE}
    Then Attach volume 0
    And Attach volume 1
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Verify all disk file status of backing image bi are ready

    FOR    ${i}    IN RANGE    10
        When Delete Longhorn DaemonSet longhorn-manager pod on all nodes simultaneously    
        And Verify not all disk file status of backing image bi are ready
        And No backimg image data source exist
        Then Wait for Longhorn components all running
        And Wait for all disk file status of backing image bi are ready
    END

    When Delete volume 0
    And Delete volume 1    
    And Delete backing image bi
