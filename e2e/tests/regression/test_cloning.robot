*** Settings ***
Documentation    Cloning Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/node.resource
Resource    ../keywords/deployment.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Cloning Basic
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-pvc    volume_type=${volume_type}    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim source-pvc to be created
    And Wait for volume of persistentvolumeclaim source-pvc detached
    And Create pod source-pod using persistentvolumeclaim source-pvc
    And Wait for pod source-pod running
    And Wait for volume of persistentvolumeclaim source-pvc healthy
    And Write 256 MB data to file data.txt in pod source-pod
    And Record file data.txt checksum in pod source-pod as checksum source-pvc

    When Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim cloned-pvc to be created
    And Wait for volume of persistentvolumeclaim cloned-pvc cloning to complete
    And Wait for volume of persistentvolumeclaim cloned-pvc detached
    Then Create pod cloned-pod using persistentvolumeclaim cloned-pvc
    And Wait for pod cloned-pod running
    And Wait for volume of persistentvolumeclaim cloned-pvc healthy
    And Check pod cloned-pod file data.txt checksum matches checksum source-pvc

Test Degraded Cloned Volume
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12206
    ...    1. Disable 1 node. Make sure that 2 other nodes are schedulable and as enough storage
    ...    2. Deploy a PVC. Verify that volume is degraded because it need 3 replica but there is only 2 schedulable nodes
    ...    3. Create a cloned-pvc from the previous PVC
    ...    4. Create a pod using cloned-pvc. Verify that the pod is not stuck and Longhorn can attach cloned-pvc
    ...    5. Enable scheduling for the node that you disable at the beginning
    ...       Verify that volume cloned-pvc rebuild and become healthy
    Given Run command
    ...    kubectl cordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute

    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-pvc    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim source-pvc to be created
    And Wait for volume of persistentvolumeclaim source-pvc detached
    And Create pod source-pod using persistentvolumeclaim source-pvc
    And Wait for pod source-pod running
    And Wait for volume of persistentvolumeclaim source-pvc degraded
    And Write 256 MB data to file data.txt in pod source-pod
    And Record file data.txt checksum in pod source-pod as checksum source-pvc

    When Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim cloned-pvc to be created
    And Wait for volume of persistentvolumeclaim cloned-pvc degraded
    And Create pod cloned-pod using persistentvolumeclaim cloned-pvc

    Then Wait for pod cloned-pod running
    And Wait for volume of persistentvolumeclaim cloned-pvc degraded
    And Check pod cloned-pod file data.txt checksum matches checksum source-pvc

    When And Run command
    ...    kubectl uncordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute-

    Then Wait for volume of persistentvolumeclaim cloned-pvc healthy
    And Check pod cloned-pod file data.txt checksum matches checksum source-pvc

Test Clone Volume With Cordoned Node
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13639
    ...    1. Drain node 0
    ...    2. Create a storageclass and a pvc source-pvc with size 3 Gi
    ...    3. Create a pod to use the pvc, write 2 Gi data to the volume, record the checksum
    ...    4. Delete the pod to detach the volume
    ...    5. Create a pvc cloned-pvc from the source-pvc
    ...    6. Wait for the volume of source-pvc to be attached, it should not be attached to node 0
    ...    7. Wait for the volume of cloned-pvc to be created and attached, it should not be attached to node 0
    ...    8. Wait for the cloning to complete
    ...    9. Create a pod to use the cloned-pvc, and check the data integrity
    Given Drain node 0

    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-pvc    storage_size=3Gi    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim source-pvc to be created
    And Wait for volume of persistentvolumeclaim source-pvc detached
    And Create pod source-pod using persistentvolumeclaim source-pvc
    And Wait for pod source-pod running
    And Write 2048 MB data to file data.txt in pod source-pod
    And Record file data.txt checksum in pod source-pod as checksum source-pvc

    When Delete pod source-pod
    And Wait for volume of persistentvolumeclaim source-pvc detached

    And Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc    sc_name=longhorn-test
    And Wait for volume of persistentvolumeclaim source-pvc attached
    And Volume of persistentvolumeclaim source-pvc should not be attached to node 0
    And Wait for volume of persistentvolumeclaim cloned-pvc to be created
    And Wait for volume of persistentvolumeclaim cloned-pvc attached
    And Volume of persistentvolumeclaim cloned-pvc should not be attached to node 0
    And Wait for volume of persistentvolumeclaim cloned-pvc cloning to complete
    And Wait for volume of persistentvolumeclaim cloned-pvc detached

    Then Create pod cloned-pod using persistentvolumeclaim cloned-pvc
    And Wait for pod cloned-pod running
    And Check pod cloned-pod file data.txt checksum matches checksum source-pvc

Test CSI Clone Respects Node And Disk Selector
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12792
    ...    1. Keep all Longhorn nodes schedulable.
    ...    2. Create an extra disk on node 1 so node 1 has multiple disks.
    ...    3. Tag node 1 with hosting.
    ...    4. Tag default disk on node 1 with hosting-fast, and extra disk with hosting-slow.
    ...    5. Create a StorageClass with nodeSelector=hosting and diskSelector=hosting-fast and strict-local.
    ...    6. Create the source PVC on node 1 and write test data.
    ...    7. Verify source replica is scheduled on node 1 default disk (not extra disk, not other nodes).
    ...    8. Detach the source volume before creating the clone.
    ...    9. Create the clone PVC and immediately verify clone/source temporary attachments respect node selector.
    ...    10. Wait for the clone controller to finish and detach the clone.
    ...    11. Attach the cloned PVC to node 1 using a deployment.
    ...    12. Verify clone replica is scheduled on node 1 default disk (not extra disk, not other nodes).
    ...    13. Verify data integrity.
    [Tags]    clone    csi    scheduling

    ${EXTRA_DISK}=    Generate random disk name
    IF    "${DATA_ENGINE}" == "v1"
        And Create 4 Gi filesystem type disk ${EXTRA_DISK} on node 1
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 4 Gi block type disk ${EXTRA_DISK} on node 1
    END

    ${DEFAULT_DISK}=    Get default disk name on node 1

    Given Set node 1 tags    hosting
    And Set disk ${DEFAULT_DISK} tags on node 1    hosting-fast
    And Set disk ${EXTRA_DISK} tags on node 1    hosting-slow

    And Create storageclass longhorn-hosting-clone with
    ...    numberOfReplicas=1
    ...    dataLocality=strict-local
    ...    nodeSelector=hosting
    ...    diskSelector=hosting-fast
    ...    dataEngine=${DATA_ENGINE}

    And Create persistentvolumeclaim source-pvc
    ...    sc_name=longhorn-hosting-clone
    ...    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim source-pvc to be created

    And Create deployment source-deploy with persistentvolumeclaim source-pvc
    ...    node_selector={"kubernetes.io/hostname":"${NODE_1}"}
    And Wait for deployment source-deploy pods stable
    And Wait for volume of persistentvolumeclaim source-pvc healthy

    And Volume of persistentvolumeclaim source-pvc should have running replicas on node 1
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 0
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 2
    And Volume of persistentvolumeclaim source-pvc should have running replicas on node 1 disk ${DEFAULT_DISK}
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 1 disk ${EXTRA_DISK}

    And Write 1024 MB data to file data.txt in deployment source-deploy
    And Record file data.txt checksum in deployment source-deploy as checksum source-pvc

    When Delete deployment source-deploy
    And Wait for volume of persistentvolumeclaim source-pvc detached

    And Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc
    ...    sc_name=longhorn-hosting-clone
    ...    storage_size=2GiB

    When Wait for volume of persistentvolumeclaim source-pvc attached
    And Volume of persistentvolumeclaim source-pvc should not be attached to node 0
    And Volume of persistentvolumeclaim source-pvc should not be attached to node 2
    And Wait for volume of persistentvolumeclaim cloned-pvc to be created
    And Wait for volume of persistentvolumeclaim cloned-pvc attached
    And Volume of persistentvolumeclaim cloned-pvc should not be attached to node 0
    And Volume of persistentvolumeclaim cloned-pvc should not be attached to node 2

    # The clone-controller attachment is removed after cloning finishes.
    # Waiting attached -> detached is a stable completion signal and avoids
    # polling the transient copy-completed-awaiting-healthy cloneStatus.
    And Wait for volume of persistentvolumeclaim cloned-pvc detached

    Then Wait for volume of persistentvolumeclaim cloned-pvc condition Scheduled to be true

    Then Create deployment cloned-deploy with persistentvolumeclaim cloned-pvc
    ...    node_selector={"kubernetes.io/hostname":"${NODE_1}"}
    And Wait for deployment cloned-deploy pods stable
    And Wait for volume of persistentvolumeclaim cloned-pvc healthy

    And Volume of persistentvolumeclaim cloned-pvc should have running replicas on node 1
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 0
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 2
    And Volume of persistentvolumeclaim cloned-pvc should have running replicas on node 1 disk ${DEFAULT_DISK}
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 1 disk ${EXTRA_DISK}
    And Check deployment cloned-deploy file data.txt checksum matches checksum source-pvc

Test CSI Clone Respects Node And Disk Selector With Best Effort
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12792
    ...    1. Keep all Longhorn nodes schedulable.
    ...    2. Create an extra disk on node 1 so node 1 has multiple disks.
    ...    3. Tag node 1 with hosting.
    ...    4. Tag default disk on node 1 with hosting-fast, and extra disk with hosting-slow.
    ...    5. Create a StorageClass with nodeSelector=hosting and diskSelector=hosting-fast and best-effort.
    ...    6. Create the source PVC on node 1 and write test data.
    ...    7. Verify source replica is scheduled on node 1 default disk (not extra disk, not other nodes).
    ...    8. Detach the source volume before creating the clone.
    ...    9. Create the clone PVC and immediately verify clone/source temporary attachments respect node selector.
    ...    10. Wait for the clone controller to finish and detach the clone.
    ...    11. Attach the cloned PVC to node 1 using a deployment.
    ...    12. Verify clone replica is scheduled on node 1 default disk (not extra disk, not other nodes).
    ...    13. Verify data integrity.
    [Tags]    clone    csi    scheduling

    ${EXTRA_DISK}=    Generate random disk name
    IF    "${DATA_ENGINE}" == "v1"
        And Create 4 Gi filesystem type disk ${EXTRA_DISK} on node 1
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 4 Gi block type disk ${EXTRA_DISK} on node 1
    END

    ${DEFAULT_DISK}=    Get default disk name on node 1

    Given Set node 1 tags    hosting
    And Set disk ${DEFAULT_DISK} tags on node 1    hosting-fast
    And Set disk ${EXTRA_DISK} tags on node 1    hosting-slow

    And Create storageclass longhorn-hosting-clone-be with
    ...    numberOfReplicas=1
    ...    dataLocality=best-effort
    ...    nodeSelector=hosting
    ...    diskSelector=hosting-fast
    ...    dataEngine=${DATA_ENGINE}

    And Create persistentvolumeclaim source-pvc
    ...    sc_name=longhorn-hosting-clone-be
    ...    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim source-pvc to be created

    And Create deployment source-deploy with persistentvolumeclaim source-pvc
    ...    node_selector={"kubernetes.io/hostname":"${NODE_1}"}
    And Wait for deployment source-deploy pods stable
    And Wait for volume of persistentvolumeclaim source-pvc healthy

    And Volume of persistentvolumeclaim source-pvc should have running replicas on node 1
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 0
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 2
    And Volume of persistentvolumeclaim source-pvc should have running replicas on node 1 disk ${DEFAULT_DISK}
    And Volume of persistentvolumeclaim source-pvc should have no running replica on node 1 disk ${EXTRA_DISK}

    And Write 1024 MB data to file data.txt in deployment source-deploy
    And Record file data.txt checksum in deployment source-deploy as checksum source-pvc

    When Delete deployment source-deploy
    And Wait for volume of persistentvolumeclaim source-pvc detached

    And Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc
    ...    sc_name=longhorn-hosting-clone-be
    ...    storage_size=2GiB

    When Wait for volume of persistentvolumeclaim source-pvc attached
    And Volume of persistentvolumeclaim source-pvc should not be attached to node 0
    And Volume of persistentvolumeclaim source-pvc should not be attached to node 2
    And Wait for volume of persistentvolumeclaim cloned-pvc to be created
    And Wait for volume of persistentvolumeclaim cloned-pvc attached
    And Volume of persistentvolumeclaim cloned-pvc should not be attached to node 0
    And Volume of persistentvolumeclaim cloned-pvc should not be attached to node 2

    # The clone-controller attachment is removed after cloning finishes.
    # Waiting attached -> detached is a stable completion signal and avoids
    # polling the transient copy-completed-awaiting-healthy cloneStatus.
    And Wait for volume of persistentvolumeclaim cloned-pvc detached

    Then Wait for volume of persistentvolumeclaim cloned-pvc condition Scheduled to be true

    Then Create deployment cloned-deploy with persistentvolumeclaim cloned-pvc
    ...    node_selector={"kubernetes.io/hostname":"${NODE_1}"}
    And Wait for deployment cloned-deploy pods stable
    And Wait for volume of persistentvolumeclaim cloned-pvc healthy

    And Volume of persistentvolumeclaim cloned-pvc should have running replicas on node 1
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 0
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 2
    And Volume of persistentvolumeclaim cloned-pvc should have running replicas on node 1 disk ${DEFAULT_DISK}
    And Volume of persistentvolumeclaim cloned-pvc should have no running replica on node 1 disk ${EXTRA_DISK}
    And Check deployment cloned-deploy file data.txt checksum matches checksum source-pvc

Test CSI Clone Fails Gracefully When No Node And Disk Satisfies Selector
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12792
    ...    1. Keep all Longhorn nodes schedulable.
    ...    2. Create a source StorageClass with default settings.
    ...    3. Create a source PVC and write test data.
    ...    4. Detach the source volume.
    ...    5. Create a clone StorageClass with nonexistent nodeSelector and diskSelector.
    ...    6. Create a clone PVC from the source PVC using the clone StorageClass without waiting for Bound.
    ...    7. Verify the clone PVC reasonably remains in Pending state.
    [Tags]    clone    csi    scheduling    negative

    Given Create storageclass longhorn-normal with
    ...    numberOfReplicas=1
    ...    dataEngine=${DATA_ENGINE}

    And Create storageclass longhorn-bad-selector with
    ...    numberOfReplicas=1
    ...    dataLocality=strict-local
    ...    nodeSelector=hosting-nonexistent-12792
    ...    diskSelector=hosting-nonexistent-12792
    ...    dataEngine=${DATA_ENGINE}

    And Create persistentvolumeclaim source-pvc
    ...    sc_name=longhorn-normal
    ...    storage_size=2GiB
    And Wait for volume of persistentvolumeclaim source-pvc to be created

    And Create deployment source-deploy with persistentvolumeclaim source-pvc
    ...    node_selector={"kubernetes.io/hostname":"${NODE_1}"}
    And Wait for deployment source-deploy pods stable
    And Wait for volume of persistentvolumeclaim source-pvc healthy

    And Write 256 MB data to file data.txt in deployment source-deploy

    When Delete deployment source-deploy
    And Wait for volume of persistentvolumeclaim source-pvc detached

    When Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc without waiting for bound
    ...    sc_name=longhorn-bad-selector
    ...    storage_size=2GiB

    And Sleep    10s
    Then Wait for persistentvolumeclaim cloned-pvc status to be Pending
