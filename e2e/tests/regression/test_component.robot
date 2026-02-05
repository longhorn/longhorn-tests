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

Test Longhorn Manager Rolling Update Configuration During Upgrade
    [Documentation]    Test that longhorn-manager rolling update is configured correctly for upgrade
    ...
    ...                https://github.com/longhorn/longhorn/issues/12240
    ...
    ...                This test validates that longhorn-manager DaemonSet rolling update strategy
    ...                is configured with maxUnavailable=1 during upgrade, ensuring at least 2 out of 3 pods
    ...                remain running during upgrades.
    ...
    ...                Test steps:
    ...                1. Uninstall existing Longhorn
    ...                2. Install stable version of Longhorn
    ...                3. Upgrade Longhorn with maxUnavailable=1 for longhorn-manager
    ...                4. Verify the rolling update strategy is correctly configured
    
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
        
        # Upgrade with custom maxUnavailable setting
        Upgrade Longhorn With Custom Command    ${custom_cmd}
        
        # Verify the configuration was applied
        Then Check DaemonSet Rolling Update Max Unavailable    longhorn-manager    expected_max_unavailable=1
    ELSE
        Log    Skipping test for ${LONGHORN_INSTALL_METHOD} - only helm supports custom maxUnavailable configuration
        Skip    Test only applicable for helm installation method
    END
    
    Then Wait for Longhorn workloads pods stable    longhorn-manager

Test CSI Components Rolling Update Configuration During Upgrade
    [Documentation]    Test that CSI components rolling update is configured correctly for upgrade
    ...
    ...                https://github.com/longhorn/longhorn/issues/12240
    ...
    ...                This test validates that CSI deployment components (csi-attacher, csi-provisioner,
    ...                csi-resizer, csi-snapshotter) have rolling update strategy configured with
    ...                maxUnavailable=1, ensuring at least 2 out of 3 replicas remain available during upgrades.
    ...
    ...                Test steps:
    ...                1. Uninstall existing Longhorn
    ...                2. Install stable version of Longhorn
    ...                3. Upgrade Longhorn with maxUnavailable=1 for CSI components
    ...                4. Verify the rolling update strategy is correctly configured for all CSI components
    
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
    
    # Verify after upgrade that CSI components have maxUnavailable=1 configured
    # This should be the default in the code for CSI deployments
    When Upgrade Longhorn to custom version
    
    Then Check Deployment Rolling Update Max Unavailable    csi-attacher    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-provisioner    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-resizer    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-snapshotter    expected_max_unavailable=1
    
    Then Wait for Longhorn workloads pods stable
    ...    csi-attacher
    ...    csi-provisioner
    ...    csi-resizer
    ...    csi-snapshotter
