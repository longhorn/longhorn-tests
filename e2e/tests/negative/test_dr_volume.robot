*** Settings ***
Documentation    Test DR volume

Test Tags    manual    negative    dr-volume

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource


Test Setup    Set up test environment
Test Teardown    Cleanup test resources


*** Test Cases ***
DR Volume Node Reboot During Initial Restoration
    [Documentation]    Test DR volume node reboot during initial restoration
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/1366
    ...                https://github.com/longhorn/longhorn/issues/1328
    ...                - Create a pod with Longhorn volume.
    ...                - Write data to the volume and get the md5sum.
    ...                - Create the 1st backup for the volume.
    ...                - Create a DR volume from the backup.
    ...                - Wait for the DR volume starting the initial restore.
    ...                - Then reboot the DR volume attached node immediately.
    ...                - Wait for the DR volume detached then reattached.
    ...                - Wait for the DR volume restore complete after the reattachment.
    ...                - Activate the DR volume and check the data md5sum.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    Then Volume 0 backup 0 should be able to create
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Then Create DR volume 1 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
        And Wait for volume 1 restoration from backup 0 of volume 0 start
        Then Reboot volume 1 volume node
        And Wait for volume 1 restoration from backup 0 of volume 0 completed
        When Activate DR volume 1
        And Attach volume 1
        And Wait for volume 1 healthy
        Then Check volume 1 data is backup 0 of volume 0
        Then Detach volume 1
        And Delete volume 1
    END

DR Volume Node Reboot During Incremental Restoration
    [Documentation]    Test DR volume node reboot During Incremental Restoration
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/1366
    ...                https://github.com/longhorn/longhorn/issues/1328
    ...
    ...                - Create a pod with Longhorn volume.
    ...                - Write data to the volume and get the md5sum.
    ...                - Create the 1st backup for the volume.
    ...                - Create a DR volume from the backup.
    ...                - Wait for the DR volume to complete the initial restore.
    ...                - Write more data to the original volume and get the md5sum.
    ...                - Create the 2nd backup for the volume.
    ...                - Wait for the DR volume incremental restore getting triggered.
    ...                - Then reboot the DR volume attached node immediately.
    ...                - Wait for the DR volume detached then reattached.
    ...                - Wait for the DR volume restore complete after the reattachment.
    ...                - Activate the DR volume and check the data md5sum.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    Then Volume 0 backup 0 should be able to create
    Then Create DR volume 1 from backup 0 of volume 0   dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 0 of volume 0 completed
    Then Write data 1 to volume 0
    And Volume 0 backup 1 should be able to create
    And Wait for volume 1 restoration from backup 1 of volume 0 start
    Then Reboot volume 1 volume node
    Then Wait for volume 1 restoration from backup 1 of volume 0 completed
    And Activate DR volume 1
    And Attach volume 1
    And Wait for volume 1 healthy
    And Check volume 1 data is backup 1 of volume 0

Sync Up With Backup Target During DR Volume Activation
    [Documentation]
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/5292
    ...                https://github.com/longhorn/longhorn/issues/7945
    ...
    ...                1. Launch 2 clusters and both have Longhorn installed
    ...                2. Set up a backup target.
    ...                3. Create a volume and write data in the 1st cluster. Then create 1st backup.
    ...                4. Restore the backup as a DR volume in the 2nd cluster.
    ...                5. Modify the backup poll interval to a large value.
    ...                6. Write more data for the volume in the 1st cluster, and create the 2nd backup.
    ...                7. Activate the DR volume in the 2nd cluster. Then verify the data
    ...                8. The activated DR volume should contain the latest data.
    Given Create dummy backup from backup-1.tar.gz
    And Create DR volume 0 from backup backup-96b3a82b011e4b76
    # the name of precreated backup 1 is backup-96b3a82b011e4b76
    # the name of precreated backup 2 is backup-b823c0557efa4a4f
    And Wait for volume 0 restoration from backup backup-96b3a82b011e4b76 to complete

    When Set backupstore poll interval to 3600 seconds
    And Create dummy backup from backup-2.tar.gz
    And Activate DR volume 0
    And Wait for volume 0 detached
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create pod 0 using volume 0
    And Wait for pod 0 running
    # there is a file version-info.txt in backup 1 and backup 2
    # the content of version-info.txt in backup 1 is version-1
    # and the checksum is fb735ea6a5dddf137c7229513cae6296
    # the content of version-info.txt in backup 2 is version-2
    # and the checksum is d51dc42f616b67126fd2aa1e1f43385b
    Then Check pod 0 file version-info.txt has checksum d51dc42f616b67126fd2aa1e1f43385b

Test DR Volume Live Upgrade And Rebuild
    [Tags]    manual    negative    dr-volume-live-upgrade-and-rebuild
    [Documentation]    - Test DR volume live upgrade and rebuild
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/1279
    ...                - Manual test plan - 
    ...                - Launch Longhorn at the previous version and Launch a Pod with a Longhorn volume.
    ...                - Write 1st data to the volume, take the 1st backup, and create two DR volumes from the 1st backup.
    ...                - Shutdown the Pod and expand the original volume and wait for the expansion complete.
    ...                - Write 2nd data that exceeds the original volume size, then take the 2nd backup.
    ...                - Trigger incremental restore for the DR volumes and wait for the restoration to complete.
    ...                - Upgrade Longhorn to the latest version.
    ...                - Crash one replica for the first DR volume and verify the rebuild process and state transition from Degraded to Healthy.
    ...                - Write 3rd data to the original volume, take the 3rd backup, and trigger incremental restore for the DR volumes.
    ...                - Do live upgrade for the 1st DR volume. This live upgrade call should success
    ...                - Activate the 1st DR volume and launch a Pod for the activated DR volume, then verify the restored data is correct.
    ...                - Do live upgrade for the original volume and the 2nd DR volume
    ...                - Crash one replica for the 2nd DR volume and verify the rebuild process and state transition from Degraded to Healthy.
    ...                - Crash one random replica for the 2nd DR volume and wait for the restore & rebuild complete.
    ...                - Delete one replica for the 2nd DR volume, then activate the 2nd DR volume before the rebuild complete.
    ...                - Verify the DR volume will be auto detached after the rebuild complete.
    ...                - Launch a pod for the 2nd activated volume, and verify the restored data is correct.
    ...                - Crash one replica for the 2nd activated volume.
    ...                - Wait for the rebuild complete, then verify the volume still works fine by reading/writing more data.

    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    # Precondition: Set up environment and install Longhorn
    Given Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And Set backupstore
    And Enable v2 data engine and add block disks

    # Scenario 1: Create initial deployment and backups
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test    storage_size=1GiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    When Write 512 MB data to file data0 in deployment 0
    Then Record file data0 checksum in deployment 0 as checksum 0

    When Create backup 0 for deployment 0 volume
    Then Verify backup list contains backup 0 of deployment 0 volume
    And Create DR volume 1 from backup 0 of deployment 0 volume
    And Create DR volume 2 from backup 0 of deployment 0 volume

    # Scenario 2: Volume expansion and data restoration
    Given Scale deployment 0 to 0
    And Wait for volume of deployment 0 detached
    When Expand deployment 0 volume to 3 GiB
    Then Wait for deployment 0 volume size expanded
    When Scale deployment 0 to 1
    Then Wait for volume of deployment 0 attached
    And Wait for volume of deployment 0 healthy
    When Write 1024 MB data to file data1 in deployment 0
    Then Record file data1 checksum in deployment 0 as checksum 1

    When Create backup 1 for deployment 0 volume
    And Wait for volume 1 restoration from backup 1 of deployment 0 volume completed
    And Wait for volume 2 restoration from backup 1 of deployment 0 volume completed

    # Scenario 3: Upgrade Longhorn and crash recovery
    When Upgrade Longhorn to custom version
    And Delete volume 1 replica on node 1
    Then Wait for volume 1 degraded
    And Wait until volume 1 replica rebuilding completed on node 1
    And Wait for volume 1 healthy

    When Write 128 MB data to file data2 in deployment 0
    Then Record file data2 checksum in deployment 0 as checksum 2

    When Create backup 2 for deployment 0 volume
    And Wait for volume 1 restoration from backup 2 of deployment 0 volume completed
    And Wait for volume 2 restoration from backup 2 of deployment 0 volume completed

    # Scenario 4: Volume engines upgrade and data verification
    ${CUSTOM_LONGHORN_ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default='undefined'
    When Upgrade volume 1 engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
    And Activate DR volume 1
    Then Wait for volume 1 detached
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    Then Wait for pod 1 running
    And Check pod 1 file data0 checksum matches checksum 0
    And Check pod 1 file data1 checksum matches checksum 1
    And Check pod 1 file data2 checksum matches checksum 2

    When Upgrade volume deployment 0 engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
    And Upgrade volume 2 engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}

    When Delete volume 2 replica on node 2
    Then Wait for volume 2 degraded
    And Wait until volume 2 replica rebuilding completed on node 2
    And Wait for volume 2 healthy

    When Delete volume 2 replica on node 2
    And Activate DR volume 2
    Then Wait for volume 2 detached
    And Create persistentvolume for volume 2
    And Create persistentvolumeclaim for volume 2
    And Create pod 2 using volume 2
    Then Wait for pod 2 running
    And Check pod 2 file data0 checksum matches checksum 0
    And Check pod 2 file data1 checksum matches checksum 1
    And Check pod 2 file data2 checksum matches checksum 2

    When Delete volume 2 replica on volume node
    Then Wait until volume 2 replicas rebuilding completed
    And Wait for volume 2 healthy
    And Check pod 2 file data0 checksum matches checksum 0
    And Check pod 2 file data1 checksum matches checksum 1
    And Check pod 2 file data2 checksum matches checksum 2
    And Check pod 2 works
