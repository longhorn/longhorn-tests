*** Settings ***
Documentation    Volume Expansion Test Cases

Test Tags    regression    expansion

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Volume Expansion When Node Disk Is Full
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12134
    ...    1. Prepare a new 10Gi Disk without any used data
    ...    2. Create a Volume with 1Gi
    ...    3. Expand the volume to 3Gi
    ...    4. IO to 3Gi, sudo dd if=/dev/zero of=/dev/sda bs=1G count=3
    ...    5. Expanding the volume to 8Gi will fail:
    ...       unable to expand volume: error while CheckReplicasSizeExpansion for volume: disk does not have enough actual space for expansion:
    ...       Physical free space would drop below minimal: left < minimal
    IF    "${DATA_ENGINE}" == "v1"
        Given Create 10 Gi filesystem type disk local-disk on node 0
        And Disable node 0 default disk
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 10 Gi block type disk local-disk on node 0
        And Disable disk block-disk scheduling on node 0
    END

    And Create volume 0 with    size=1Gi    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    When Expand volume 0 to 3Gi
    Then Wait for volume 0 size to be 3Gi

    When Write 3 GB data to volume 0
    Then Expand volume 0 to 8Gi should fail
    And Wait for volume 0 size to be 3Gi
    And Delete volume 0
