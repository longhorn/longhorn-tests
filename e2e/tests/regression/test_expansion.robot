*** Settings ***
Documentation    Volume Expansion Test Cases

Test Tags    regression    expansion

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/deployment.resource
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
    ${DISK0}=    Generate random disk name

    IF    "${DATA_ENGINE}" == "v1"
        Given Create 10 Gi filesystem type disk ${DISK0} on node 0
        And Disable node 0 default disk
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 10 Gi block type disk ${DISK0} on node 0
        And Disable disk block-disk scheduling on node 0
    END

    And Create volume 0 with    size=1Gi    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    When Expand volume 0 to 3Gi
    Then Wait for volume 0 size to be 3Gi

    When Write 3 GB data to volume 0
    And Sleep    30s    # Wait for node disk status to be updated
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

Test Volume Expansion Without Fully Scheduled Replicas
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12606
    ...    1. Disable a node scheduling
    ...    2. Create a PVC
    ...    3. Create a pod to use this PVC, and write some data
    ...    4. Wait for the volume of the PVC degraded
    ...    5. Wait for the volume of the PVC condition Scheduled to be false
    ...    6. Expand the PVC to a larger size
    ...    7. Wait for the volume of the PVC size to be the larger size
    ...    8. Check the data is intact
    Given Disable node 2 scheduling
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim 0 to be created
    And Create pod 0 using persistentvolumeclaim 0
    And Wait for pod 0 running
    And Write 512 MB data to file data.txt in pod 0
    And Wait for volume of persistentvolumeclaim 0 degraded
    And Wait for volume of persistentvolumeclaim 0 condition Scheduled to be false

    When Expand persistentvolumeclaim 0 size to 3Gi
    Then Wait for volume of persistentvolumeclaim 0 size to be 3Gi
    And Check pod 0 data in file data.txt is intact

Test RWX Volume Automatic Online Expansion
    [Tags]    rwx    expansion    sharemanager
    [Documentation]    Test automatic online filesystem resize for RWX volumes
    ...                Ref: https://github.com/longhorn/longhorn/issues/8119
    ...                Related issues:
    ...                - https://github.com/longhorn/longhorn/issues/8118
    ...                - https://github.com/longhorn/longhorn/issues/9736
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test    storage_size=50MiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 10 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Expand deployment 0 volume to 100MiB
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    And Check no sharemanager pod of deployment 0 recreation
    And Assert disk size in sharemanager pod for deployment 0 is 100MiB
    # Wait for filesystem to be expanded in the workload pod before writing new data
    And Assert filesystem size in deployment 0 is 100MiB
    # Write data that covers the newly expanded blocks to verify filesystem expansion
    And Write 60 MB data to file data2.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 0 data in file data2.txt is intact

Test Volume Offline Expansion With Unscheduled Replica
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13355
    ...    Test offline expansion of direct volume (non-dynamic provisioning) with unscheduled replica
    ...    1. Disable node 0 scheduling
    ...    2. Create a 1Gi direct volume, support v1 and v2 data engine, do not attach it
    ...    3. Expand the detached volume to 2Gi
    ...    4. Wait for the volume expansion to complete
    ...    5. Attach the volume
    ...    6. Write 1.5 Gi data and check data
    Given Disable node 0 scheduling
    And Create volume 0 with    size=1Gi    dataEngine=${DATA_ENGINE}

    When Expand volume 0 to 2Gi
    Then Wait for volume 0 size to be 2Gi
    And Wait for volume 0 detached

    When Attach volume 0
    And Wait for volume 0 degraded
    And Write 1536 Mi data to volume 0
    Then Check volume 0 data is intact

Test Dynamic Provisioned Volume Offline Expansion With Unscheduled Replica
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13355
    ...    Test offline expansion of dynamically provisioned volume with unscheduled replica
    ...    1. Disable node 0 scheduling
    ...    2. Create a 1Gi PVC, support v1 and v2 data engine
    ...    3. Wait for volume to be created and detached
    ...    4. Expand the PVC to 2Gi while volume is detached
    ...    5. Wait for the volume expansion to complete
    ...    6. Attach the volume by creating a pod
    ...    7. Write 1.5 Gi data and check data
    Given Disable node 0 scheduling
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test    storage_size=1GiB
    And Wait for volume of persistentvolumeclaim 0 to be created
    And Wait for volume of persistentvolumeclaim 0 detached

    When Expand persistentvolumeclaim 0 size to 2Gi
    Then Wait for volume of persistentvolumeclaim 0 size to be 2Gi
    And Wait for volume of persistentvolumeclaim 0 detached

    When Create pod 0 using persistentvolumeclaim 0
    And Wait for pod 0 running
    And Wait for volume of persistentvolumeclaim 0 degraded
    And Write 1536 MB data to file data.txt in pod 0
    Then Check pod 0 data in file data.txt is intact
