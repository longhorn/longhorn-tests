*** Settings ***
Documentation    Disk I/O Error Test Cases

Test Tags    negative    disk    io-error

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/io.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Setup device mapper environment
    Set up test environment
    Setup dm disk environment on node 0

Cleanup device mapper environment
    Cleanup dm disk environment on node 0 for ${DATA_ENGINE}
    Cleanup test resources

Setup dm disk environment on node ${node_id}
    [Documentation]    Setup device mapper disk for testing I/O errors.
    ...                For V1: creates dm device and adds as filesystem disk.
    ...                For V2: removes block disk from Longhorn, creates dm device, adds as block disk.
    Set disk path based on host provider and architecture
    ${dm_device_name} =    Generate random disk name    prefix=dm-dev    length=8
    ${disk_name} =    Generate random disk name    prefix=dm-disk
    ${mount_path} =    Set Variable    /mnt/disk
    Set Test Variable    ${disk_name}
    Set Test Variable    ${dm_device_name}
    Set Test Variable    ${mount_path}

    IF    '${DATA_ENGINE}' == 'v1'
        Setup dm disk for v1 on node ${node_id}
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        Setup dm disk for v2 on node ${node_id}
    END

Setup dm disk for v1 on node ${node_id}
    [Documentation]    Setup dm device as filesystem disk for V1 data engine.
    When Create and mount dm disk from block device ${DISK_PATH} as ${dm_device_name} on node ${node_id} to ${mount_path}
    And Disable node ${node_id} default disk
    And Add filesystem disk ${disk_name} to node ${node_id} with path ${mount_path}

Setup dm disk for v2 on node ${node_id}
    [Documentation]    Setup dm device as block disk for V2 data engine.
    ...                Removes default BLOCK disk (which uses /dev/xvdh), creates dm-linear on /dev/xvdh, adds dm device as block disk.
    When Disable default block disk on node ${node_id}
    And Delete default block disk on node ${node_id}
    And Create dm linear device from block device ${DISK_PATH} as ${dm_device_name} on node ${node_id}
    Then Disable node ${node_id} default disk
    And Add block disk ${disk_name} to node ${node_id} with path /dev/mapper/${dm_device_name}

Cleanup dm disk environment on node ${node_id} for ${data_engine}
    [Documentation]    Cleanup device mapper disk and restore default disk.
    When Switch dm device to linear mode    ${dm_device_name}    ${node_id}    ${DISK_PATH}
    And Delete volume 2    wait=False
    IF    '${data_engine}' == 'v1'
        Then Force unmount dm disk at ${mount_path} on node ${node_id}
    END
    And Wait for volume 2 deleted

    When Disable disk ${disk_name} scheduling on node ${node_id}
    And Delete disk ${disk_name} on node ${node_id}
    And Cleanup dm disk ${dm_device_name} on node ${node_id}
    IF    '${data_engine}' == 'v1'
        And Remove dir ${mount_path} on node ${node_id}
        And Wipe block device ${DISK_PATH} on node ${node_id}
        And Enable node ${node_id} default disk
    END

*** Test Cases ***
Replica Fails When Disk Has I/O Errors
    [Documentation]    Verify that replica fails when the underlying disk encounters I/O errors.
    ...
    ...                Uses device mapper error target to inject I/O errors at kernel block layer.
    ...                Supports both V1 (filesystem disk) and V2 (block disk) data engines.
    ...                Requires extra block devices on nodes (RUN_V2_TEST=true).
    ...
    ...                Device Mapper Chain:
    ...                /dev/mapper/dm-device
    ...                -> linear/error
    ...                -> /dev/xvdh (physical disk)
    ...
    ...                Test Flow:
    ...                1. Setup: Create dm-linear device, add as Longhorn disk
    ...                   V1: Format as ext4, mount to /mnt/disk, add as filesystem disk
    ...                   V2: Remove default block disk, add dm device as block disk
    ...                2. Create volume with 3 replicas, attach to node 0
    ...                3. Switch dm device to error mode
    ...                4. Write data to trigger I/O errors on replica
    ...                5. Verify volume degraded, no running replica on node 0, data intact on others
    ...
    ...                Known Issues on v2 data engine: https://github.com/longhorn/longhorn/issues/13354
    ...
    ...                Future enhance: https://github.com/longhorn/longhorn/issues/13395            
    [Setup]    Setup device mapper environment
    [Teardown]    Cleanup device mapper environment
    Given Create volume 2 with    size=1Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 2 to node 0
    And Wait for volume 2 healthy

    When Switch dm device to error mode    dm_device_name=${dm_device_name}    node_id=0
    And Write data 0 500 MB to volume 2
    Then Wait for volume 2 degraded
    And Volume 2 should have no running replica on node 0
    And Check volume 2 data is intact
