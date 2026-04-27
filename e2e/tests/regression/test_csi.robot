*** Settings ***
Documentation    CSI Test Cases

Test Tags    regression    csi

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/node.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test CSI Storage Capacity Without DataEngine Parameter
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11906
    When Create storageclass longhorn-test with    volumeBindingMode=WaitForFirstConsumer
    # expect no error message like:
    # err: rpc error: code = InvalidArgument desc = storage class parameters missing 'dataEngine'
    Then Run command and not expect output
    ...    kubectl logs -l app=longhorn-csi-plugin -n longhorn-system -c longhorn-csi-plugin
    ...    InvalidArgument
    # csistoragecapacity should be created like:
    # NAME          CREATED AT
    # csisc-c8r8z   2025-10-13T03:13:03Z
    # csisc-gl479   2025-10-13T03:13:03Z
    # csisc-2lm6j   2025-10-13T03:13:03Z
    And Run command and expect output
    ...    kubectl get csistoragecapacity -n longhorn-system
    ...    csisc

Test CSI Pod Soft Anti Affinity
    [Tags]    custom-setting    uninstall
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11617
    ...    1. Create a single node cluster by cordoning and tainting the rest of worker nodes with NoExecute
    ...    2. Edit deployment YAML. Add the environment variable CSI_POD_ANTI_AFFINITY_PRESET = soft
    ...       to the longhorn-driver-deployer deployment
    ...    3. Check that all CSI pods were deployed on the same node
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    # cordon and taint node 0 and node 1
    And Run command
    ...    kubectl cordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute
    And Run command
    ...    kubectl cordon ${NODE_1}
    And Run command
    ...    kubectl taint node ${NODE_1} node-role.kubernetes.io/worker=true:NoExecute

    # install Longhorn with CSI_POD_ANTI_AFFINITY_PRESET = soft
    IF    '${LONGHORN_INSTALL_METHOD}' == 'manifest'
        When Install Longhorn
        ...    custom_cmd=sed -i '/- name: CSI_ATTACHER_IMAGE/i\\${SPACE * 10}- name: CSI_POD_ANTI_AFFINITY_PRESET' longhorn.yaml && sed -i '/- name: CSI_POD_ANTI_AFFINITY_PRESET/a\\${SPACE * 12}value: soft' longhorn.yaml
    ELSE IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        When Install Longhorn
        ...    custom_cmd=echo -e 'csi:\n${SPACE * 2}podAntiAffinityPreset: soft' > values.yaml
    ELSE
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    # all CSI pods were deployed on node 2
    Then Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running

Test CSI Pod Hard Anti Affinity
    [Tags]    custom-setting    uninstall
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11617
    ...    1. Create a single node cluster by cordoning and tainting the rest of worker nodes with NoExecute
    ...    2. Edit deployment YAML. Add the environment variable CSI_POD_ANTI_AFFINITY_PRESET = hard
    ...       to the longhorn-driver-deployer deployment
    ...    3. Check that only one pod per CSI type has been deployed
    ...    4. Add worker nodes back to the cluster by uncordoning and removing the NoExecute taint
    ...    5. Observe CSI pods being deployed to all worker nodes
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    # cordon and taint node 0 and node 1
    And Run command
    ...    kubectl cordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute
    And Run command
    ...    kubectl cordon ${NODE_1}
    And Run command
    ...    kubectl taint node ${NODE_1} node-role.kubernetes.io/worker=true:NoExecute

    # install Longhorn with CSI_POD_ANTI_AFFINITY_PRESET = hard
    IF    '${LONGHORN_INSTALL_METHOD}' == 'manifest'
        When Install Longhorn
        ...    custom_cmd=sed -i '/- name: CSI_ATTACHER_IMAGE/i\\${SPACE * 10}- name: CSI_POD_ANTI_AFFINITY_PRESET' longhorn.yaml && sed -i '/- name: CSI_POD_ANTI_AFFINITY_PRESET/a\\${SPACE * 12}value: hard' longhorn.yaml
    ELSE IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        When Install Longhorn
        ...    custom_cmd=echo -e 'csi:\n${SPACE * 2}podAntiAffinityPreset: hard' > values.yaml
    ELSE
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    # only 1 pod per CSI type has been deployed, and it's on node 2
    Then Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running --no-headers | wc -l
    ...    1

    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1

    # uncordon and untaint node 0 and node 1
    When Run command
    ...    kubectl uncordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute-
    And Run command
    ...    kubectl uncordon ${NODE_1}
    And Run command
    ...    kubectl taint node ${NODE_1} node-role.kubernetes.io/worker=true:NoExecute-
    And Sleep    120

    # 3 pods per CSI type have been deployed
    Then Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running --no-headers | wc -l
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running --no-headers | wc -l
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running --no-headers | wc -l
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running --no-headers | wc -l
    ...    3

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running

Test CSI Pod Anti Affinity Update
    [Tags]    custom-setting    uninstall
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12100
    ...    1. Create a single node cluster by cordoning and tainting the rest of worker nodes with NoExecute
    ...    2. Edit deployment YAML. Add the environment variable CSI_POD_ANTI_AFFINITY_PRESET = soft
    ...       to the longhorn-driver-deployer deployment
    ...    3. Check that all CSI pods were deployed on the same node
    ...    4. Edit the environment variable CSI_POD_ANTIAFFINITY_PRESET = hard on the longhorn-driver-deployer deployment
    ...    5. Check that only one pod per CSI type is Running. The other two pods are Pending.
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    # cordon and taint node 0 and node 1
    And Run command
    ...    kubectl cordon ${NODE_0}
    And Run command
    ...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute
    And Run command
    ...    kubectl cordon ${NODE_1}
    And Run command
    ...    kubectl taint node ${NODE_1} node-role.kubernetes.io/worker=true:NoExecute

    # install Longhorn with CSI_POD_ANTI_AFFINITY_PRESET = soft
    IF    '${LONGHORN_INSTALL_METHOD}' == 'manifest'
        When Install Longhorn
        ...    custom_cmd=sed -i '/- name: CSI_ATTACHER_IMAGE/i\\${SPACE * 10}- name: CSI_POD_ANTI_AFFINITY_PRESET' longhorn.yaml && sed -i '/- name: CSI_POD_ANTI_AFFINITY_PRESET/a\\${SPACE * 12}value: soft' longhorn.yaml
    ELSE IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        When Install Longhorn
        ...    custom_cmd=echo -e 'csi:\n${SPACE * 2}podAntiAffinityPreset: soft' > values.yaml
    ELSE
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    # all CSI pods were deployed on node 2
    Then Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    3

    # update CSI_POD_ANTI_AFFINITY_PRESET to hard
    IF    '${LONGHORN_INSTALL_METHOD}' == 'manifest'
        When Run command
        ...    kubectl -n longhorn-system patch deployment longhorn-driver-deployer --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/env/3/value", "value": "hard"}]'
    ELSE IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        # update the value by helm upgrade
        When Install Longhorn
        ...    custom_cmd=echo -e 'csi:\n${SPACE * 2}podAntiAffinityPreset: hard' > values.yaml
    ELSE
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    # only 1 pod per CSI type has been deployed, and it's on node 2
    Then Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running --no-headers | wc -l
    ...    1

    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-provisioner --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-resizer --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-attacher --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
    ...    1

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running

Test CSI Node Server Can Recover Corrupted Block Mount Point
    [Tags]    block-volume
    [Documentation]    Reproduce CSI block mount issue with broken symlink and verify workload launch succeeds.
    ...    1. Cordon non-target nodes.
    ...    2. Create single replica Longhorn volume `vol`.
    ...    3. Corrupt mount point on target node with explicit host commands.
    ...    4. Create block-volume workload using pre-created volume.
    ...    5. Verify workload is launched successfully and the broken symlink issue is resolved.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/12006
    Given Cordon node 1
    And Cordon node 2
    And Create volume vol    size=200Mi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    # corrupt the mount point on the target node (node 0)
    And Corrupt CSI block volume staging mount point on node 0 for volume vol
    And Verify CSI block volume staging mount point is corrupted on node 0 for volume vol

    When Create persistentvolume for volume vol    volumeMode=Block
    And Create persistentvolumeclaim for volume vol    volumeMode=Block
    And Create deployment csi-block-mount-recovery with block persistentvolumeclaim vol
    Then Wait for deployment csi-block-mount-recovery pods stable
    And Verify CSI block volume staging mount point is recovered on node 0 for volume vol
    And Make block device filesystem in deployment csi-block-mount-recovery
    And Mount block device on /data in deployment csi-block-mount-recovery
    And Write 100 MB data to file data.txt in deployment csi-block-mount-recovery
    And Check deployment csi-block-mount-recovery data in file data.txt is intact

Test Volume With WaitForFirstConsumer Binding Mode And Node Selector Without CSI Storage Capacity
    [Documentation]    Test WaitForFirstConsumer volume binding with nodeSelector on compute nodes without disks.
    ...
    ...    1. Set up a 3-node cluster with node roles: 1 compute node, 2 storage nodes
    ...    2. Verify csi-storage-capacity-tracking setting is false (default)
    ...    3. Verify CSIDriver storageCapacity is false (default)
    ...    4. Label nodes: node 0 as compute, nodes 1-2 as storage
    ...    5. Set tag 'storage' on nodes 1-2 for replica scheduling
    ...    6. Remove disk on node 0 (compute node)
    ...    7. Create storage class with volumeBindingMode: WaitForFirstConsumer and nodeSelector: storage
    ...    8. Create PVC with the storage class and verify it's Pending
    ...    9. Create deployment with PVC, forcing pod to run on compute node (node 0)
    ...    10. Verify:
    ...        - Pod is scheduled to compute node without Longhorn disk
    ...        - PVC is successfully bound
    ...        - Pod is running on compute node
    ...        - Longhorn replica is scheduled on storage node
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/12807

    # Step 1-3: Verify default settings
    Given Setting csi-storage-capacity-tracking should be false
    And Check CSI driver storage capacity is false

    # Step 4: Label nodes for pod scheduling
    When Label node 0 with longhorn-test-role=compute
    And Label node 1 with longhorn-test-role=storage
    And Label node 2 with longhorn-test-role=storage

    # Step 5: Set tags on storage nodes for replica scheduling
    And Set node 1 tags    storage
    And Set node 2 tags    storage

    # Step 6: Remove disk on compute node
    IF    "${DATA_ENGINE}" == "v1"
        And Disable node 0 default disk
        And Delete node 0 default disk
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Disable default block disk on node 0
        And Delete default block disk on node 0
    END

    # Step 7: Create storage class with WaitForFirstConsumer and nodeSelector
    And Create storageclass longhorn-wffc-storage with
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    numberOfReplicas=2
    ...    nodeSelector=storage
    ...    dataEngine=${DATA_ENGINE}

    # Step 8: Create PVC without waiting for bound (it should be Pending)
    And Create persistentvolumeclaim 0 without waiting for bound
    ...    sc_name=longhorn-wffc-storage
    And Wait for persistentvolumeclaim 0 status to be Pending

    # Step 9: Create deployment with nodeSelector for compute node
    And Create deployment 0 with persistentvolumeclaim 0
    ...    node_selector={"longhorn-test-role":"compute"}

    # Step 10: Verify the results
    Then Wait for persistentvolumeclaim 0 status to be Bound
    And Wait for volume of deployment 0 healthy
    And Wait for deployment 0 pods stable
    And Check deployment 0 pod is running on node ${NODE_0}
    And Check deployment 0 volume replica is not on node ${NODE_0}
    And Write 100 MB data to file data.bin in deployment 0
    And Check deployment 0 data in file data.bin is intact
