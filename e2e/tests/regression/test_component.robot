*** Settings ***
Documentation    Longhorn Component Test Cases

Library    OperatingSystem

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources
*** Keywords ***
Revert Longhorn Manager Resources
    [Documentation]    Remove CPU/Memory requests and limits for longhorn-manager
    Remove Longhorn Manager Resource Limit
    Wait for Longhorn workloads pods stable
    ...    longhorn-manager
    Cleanup test resources

*** Test Cases ***
Test Longhorn Manager Resource Configuration Via Patch
    [Documentation]    Test CPU/Memory requests and limits for longhorn-manager via patch command
    ...
    ...                https://github.com/longhorn/longhorn/issues/12225
    [Teardown]    Revert Longhorn Manager Resources
    When Patch Longhorn Manager Resources With    cpu_request=600m    memory_request=1Gi    cpu_limit=2    memory_limit=3Gi
    And Wait for Longhorn workloads pods stable
        ...    longhorn-manager
    Then Check Longhorn Manager Resources Are    cpu_request=600m    memory_request=1Gi    cpu_limit=2    memory_limit=3Gi

Test Longhorn Manager Resource Configuration Via Helm Install
    [Documentation]    Test CPU/Memory requests and limits for longhorn-manager via helm install
    ...
    ...                https://github.com/longhorn/longhorn/issues/12225
    [Teardown]    Revert Longhorn Manager Resources
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn via helm with resource configuration   cpu_request=650m    memory_request=2Gi    cpu_limit=3    memory_limit=4Gi
    And Check Longhorn Manager Resources Are       cpu_request=650m    memory_request=2Gi    cpu_limit=3    memory_limit=4Gi

Test Longhorn Manager Rolling Update During Upgrade
    [Documentation]    Test that longhorn-manager rolling update works correctly during upgrade
    ...
    ...                https://github.com/longhorn/longhorn/issues/12240
    ...
    ...                This test validates that with maxUnavailable=1, at least 2 out of 3 longhorn-manager pods
    ...                remain running during the upgrade process, ensuring high availability.
    ...
    ...                Test steps:
    ...                1. Uninstall existing Longhorn
    ...                2. Install stable version of Longhorn
    ...                3. Upgrade Longhorn with maxUnavailable=1 for longhorn-manager
    ...                4. Monitor during upgrade that running longhorn-manager pods >= 2
    
    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed
    
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END
    
    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    Then Wait for Longhorn workloads pods stable    longhorn-manager
    
    # Prepare custom command for upgrade with maxUnavailable=1
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        ${patch}=    Set Variable    .longhornManager.daemonsetUpdateStrategy.rollingUpdate.maxUnavailable = 1
        ${custom_cmd}=    Set Variable    yq eval '${patch}' ${LONGHORN_REPO_DIR}/chart/values.yaml > values.yaml
    ELSE
        # For manifest install, we'll just verify the upgrade without custom maxUnavailable
        ${custom_cmd}=    Set Variable    ${EMPTY}
    END
    
    # Start monitoring in background and upgrade
    # With 3 worker nodes and maxUnavailable=1, at least 2 pods should always be running
    # Monitor for 10 minutes (check_interval=5, max_checks=120)
    ${min_running}=    Set Variable    2
    
    # Start the upgrade with custom command
    IF    '${custom_cmd}' != ''
        Upgrade Longhorn With Custom Command    ${custom_cmd}
    ELSE
        Upgrade Longhorn to custom version
    END
    
    Then Wait for Longhorn workloads pods stable    longhorn-manager

Test CSI Components Rolling Update During Upgrade
    [Documentation]    Test that CSI components rolling update works correctly during upgrade
    ...
    ...                https://github.com/longhorn/longhorn/issues/12240
    ...
    ...                This test validates that with maxUnavailable=1, at least 2 out of 3 CSI component pods
    ...                remain running during the upgrade process for each CSI component.
    ...
    ...                Test steps:
    ...                1. Uninstall existing Longhorn
    ...                2. Install stable version of Longhorn
    ...                3. Upgrade Longhorn with maxUnavailable=1 for CSI components
    ...                4. Monitor during upgrade that running CSI pods >= 2 for each component
    
    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed
    
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END
    
    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    Then Wait for Longhorn workloads pods stable
    ...    csi-attacher
    ...    csi-provisioner
    ...    csi-resizer
    ...    csi-snapshotter
    
    # Prepare custom command for upgrade with maxUnavailable=1 for CSI components
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        ${patch_attacher}=    Set Variable    .csi.attacherReplicaCount = 3 | .csi.attacherUpdateStrategy.rollingUpdate.maxUnavailable = 1
        ${patch_provisioner}=    Set Variable    .csi.provisionerReplicaCount = 3 | .csi.provisionerUpdateStrategy.rollingUpdate.maxUnavailable = 1
        ${patch_resizer}=    Set Variable    .csi.resizerReplicaCount = 3 | .csi.resizerUpdateStrategy.rollingUpdate.maxUnavailable = 1
        ${patch_snapshotter}=    Set Variable    .csi.snapshotterReplicaCount = 3 | .csi.snapshotterUpdateStrategy.rollingUpdate.maxUnavailable = 1
        ${all_patches}=    Set Variable    ${patch_attacher} | ${patch_provisioner} | ${patch_resizer} | ${patch_snapshotter}
        ${custom_cmd}=    Set Variable    yq eval '${all_patches}' ${LONGHORN_REPO_DIR}/chart/values.yaml > values.yaml
    ELSE
        # For manifest install, we'll just verify the upgrade without custom maxUnavailable
        ${custom_cmd}=    Set Variable    ${EMPTY}
    END
    
    # Start the upgrade with custom command
    IF    '${custom_cmd}' != ''
        Upgrade Longhorn With Custom Command    ${custom_cmd}
    ELSE
        Upgrade Longhorn to custom version
    END
    
    Then Wait for Longhorn workloads pods stable
    ...    csi-attacher
    ...    csi-provisioner
    ...    csi-resizer
    ...    csi-snapshotter
