*** Settings ***
Documentation    Cloning Test Cases

Test Tags    regression    cloning

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
