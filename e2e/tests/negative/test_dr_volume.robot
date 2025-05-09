*** Settings ***
Documentation    Test DR volume node reboot
...              https://github.com/longhorn/longhorn/issues/8425

Test Tags    manual

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


Test Setup    Set test environment
Test Teardown    Cleanup test resources


*** Test Cases ***
DR Volume Node Reboot During Initial Restoration
    [Tags]    longhorn-8425
    [Documentation]    Test DR volume node reboot during initial restoration
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/8425
    ...
    ...                Create a pod with Longhorn volume.
    ...                Write data to the volume and get the md5sum.
    ...                Create the 1st backup for the volume.
    ...                Create a DR volume from the backup.
    ...                Wait for the DR volume starting the initial restore.
    ...                Then reboot the DR volume attached node immediately.
    ...                Wait for the DR volume detached then reattached.
    ...                Wait for the DR volume restore complete after the reattachment.
    ...                Activate the DR volume and check the data md5sum.
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
    [Tags]    longhorn-8425
    [Documentation]    Test DR volume node reboot During Incremental Restoration
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/8425
    ...
    ...                Create a pod with Longhorn volume.
    ...                Write data to the volume and get the md5sum.
    ...                Create the 1st backup for the volume.
    ...                Create a DR volume from the backup.
    ...                Wait for the DR volume to complete the initial restore.
    ...                Write more data to the original volume and get the md5sum.
    ...                Create the 2nd backup for the volume.
    ...                Wait for the DR volume incremental restore getting triggered.
    ...                Then reboot the DR volume attached node immediately.
    ...                Wait for the DR volume detached then reattached.
    ...                Wait for the DR volume restore complete after the reattachment.
    ...                Activate the DR volume and check the data md5sum.
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

    When Set backupstore poll intervel to 3600 seconds
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
