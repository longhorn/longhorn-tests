*** Settings ***
Documentation    Cloning Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

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
