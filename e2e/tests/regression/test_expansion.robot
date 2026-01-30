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

Test Volume Expansion During Volume Cloning
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11484
    ...    1. Create a source volume. Write some data to the volume
    ...    2. Create a target volume from the source volume
    ...    3. While data cloning is still in progress, expand the size of target volume.
    ...       Longhorn should block the expansion request. User can only expand the target volume after cloning finish
    ...    4. Data in the target volume is intact after the expansion
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-pvc    sc_name=longhorn-test    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim source-pvc to be created
    And Wait for volume of persistentvolumeclaim source-pvc detached
    And Create pod source-pod using persistentvolumeclaim source-pvc
    And Wait for pod source-pod running
    And Wait for volume of persistentvolumeclaim source-pvc healthy
    And Write 1024 MB data to file data.txt in pod source-pod
    And Record file data.txt checksum in pod source-pod as checksum source-pvc

    FOR   ${i}    IN RANGE    5
        When Create persistentvolumeclaim cloned-pvc-${i} from persistentvolumeclaim source-pvc    sc_name=longhorn-test    storage_size=2GiB
        And Wait for volume of persistentvolumeclaim cloned-pvc-${i} to be created
        And Wait for volume of persistentvolumeclaim cloned-pvc-${i} degraded
        Then Expand persistentvolumeclaim cloned-pvc-${i} size to 3Gi
        And Wait for volume of persistentvolumeclaim cloned-pvc-${i} detached
        And Create pod cloned-pod-${i} using persistentvolumeclaim cloned-pvc-${i}
        And Wait for pod cloned-pod-${i} running
        And Wait for volume of persistentvolumeclaim cloned-pvc-${i} healthy
        And Check pod cloned-pod-${i} file data.txt checksum matches checksum source-pvc
    END

Test Volume Expansion Without Schedulable Nodes
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11484
    ...    1. Disable scheduling for all nodes
    ...    2. Create a volume of 1 GiB. Notice that it will be unschedulale because all nodes are disabled
    ...    3. Try expand the volume. Note your have to use kubectl edit to change volume size
    ...    4. Verify that Longhorn block the expansion request
    Given Disable node 0 scheduling
    And Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create volume vol with    size=2Gi    dataEngine=${DATA_ENGINE}

    When Run command and expect output
    ...    kubectl patch volume -n longhorn-system vol --type='merge' -p '{"spec": {"size": "3221225472"}}'
    ...    The request is invalid
    Then Wait for volume vol size to be 2Gi

Test Volume Expansion
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11484
    ...    1. Create a volume
    ...    2. Make sure all replicas are schedule
    ...    3. Expand the volume -> verify that it is ok
    ...    4. Attach the volume
    ...    5. Try to expand the volume again-> verify that it is ok
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim 0 to be created
    And Wait for volume of persistentvolumeclaim 0 detached
    # offline expansion
    When Expand persistentvolumeclaim 0 size to 3Gi
    Then Wait for volume of persistentvolumeclaim 0 size to be 3Gi
    And Create pod 0 using persistentvolumeclaim 0
    And Wait for pod 0 running
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 1024 MB data to file data.txt in pod 0

    # online expansion
    When Expand persistentvolumeclaim 0 size to 4Gi
    Then Wait for volume of persistentvolumeclaim 0 size to be 4Gi
    And Check pod 0 data in file data.txt is intact
