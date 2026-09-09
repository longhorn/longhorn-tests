*** Settings ***
Documentation    Negative Test Cases for v2 block disk device recovery
...    Ref: https://github.com/longhorn/longhorn/issues/13893

Test Tags    negative    v2    node-disk-mgmt

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource

Test Setup    Set up v2 block disk test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 block disk test environment
    Set up test environment
    Enable v2 data engine and add block disks
    Skip test if disk path ${DISK_PATH} is not a PCI BDF

*** Test Cases ***
V2 Block Disk Should Become Ready When Its Device Is Left Bound To Userspace Driver
    [Documentation]    An interrupted disk creation can leave the NVMe device bound to
    ...    vfio-pci. With diskDriver auto, the device must still be resolved back to the
    ...    nvme driver, otherwise the disk stays Ready=False and Schedulable=False forever.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Disable disk ${DEFAULT_BLOCK_DISK_NAME} scheduling without ready check on node 0
    And Delete disk ${DEFAULT_BLOCK_DISK_NAME} on node 0
    And Wait for device ${DISK_PATH} on node 0 released from userspace driver

    When Bind device ${DISK_PATH} on node 0 to userspace driver
    And Add block disk ${DEFAULT_BLOCK_DISK_NAME} to node 0 with path ${DISK_PATH}

    Then Wait for disk ${DEFAULT_BLOCK_DISK_NAME} on node 0 schedulable

V2 Block Disk Device Should Be Released After The Disk Is Removed
    [Documentation]    Removing a block disk must hand the device back to the kernel.
    ...    Leaving it bound to a userspace driver makes the disk unusable on re-provisioning.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Wait for disk ${DEFAULT_BLOCK_DISK_NAME} on node 0 schedulable

    When Disable disk ${DEFAULT_BLOCK_DISK_NAME} scheduling without ready check on node 0
    And Delete disk ${DEFAULT_BLOCK_DISK_NAME} on node 0

    Then Wait for device ${DISK_PATH} on node 0 released from userspace driver
    And Add block disk ${DEFAULT_BLOCK_DISK_NAME} to node 0 with path ${DISK_PATH}
    And Wait for disk ${DEFAULT_BLOCK_DISK_NAME} on node 0 schedulable

V2 Block Disk Device Should Be Released After Instance Manager Restart
    [Documentation]    The disk record only lives in the instance manager memory. After a
    ...    restart the disk deletion must still release the device instead of reporting
    ...    success and leaking it.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Wait for disk ${DEFAULT_BLOCK_DISK_NAME} on node 0 schedulable

    # Deleting the disk while the instance manager has no record of it forces the
    # deletion through the orphan device release path.
    When Disable disk ${DEFAULT_BLOCK_DISK_NAME} scheduling without ready check on node 0
    And Delete v2 instance manager on node 0
    And Wait for node 0 block disk unschedulable
    And Delete disk ${DEFAULT_BLOCK_DISK_NAME} on node 0

    Then Wait for device ${DISK_PATH} on node 0 released from userspace driver
    And Add block disk ${DEFAULT_BLOCK_DISK_NAME} to node 0 with path ${DISK_PATH}
    And Wait for disk ${DEFAULT_BLOCK_DISK_NAME} on node 0 schedulable
