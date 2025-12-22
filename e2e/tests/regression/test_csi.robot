*** Settings ***
Documentation    CSI Test Cases

Test Tags    regression    csi

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource

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
    [Tags]    custom-setting
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
    [Tags]    custom-setting
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
    [Tags]    custom-setting
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
