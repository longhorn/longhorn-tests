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
    [Tags]    upgrade
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
    ...                3. Upgrade Longhorn with maxUnavailable=1 for longhorn-manager (don't wait)
    ...                4. Monitor during upgrade that running longhorn-manager pods count is not 0
    
    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed
    
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END
    
    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    
    # Prepare custom command for upgrade with maxUnavailable=1
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        # Start upgrade without waiting - returns process object
        Upgrade Longhorn to custom version
        ...    custom_cmd=yq eval -i '.longhornManager.updateStrategy.rollingUpdate.maxUnavailable = 1' values.yaml
        ...    wait=${False}
    ELSE
        # For manifest, maxUnavailable is in longhorn.yaml DaemonSet spec
        Upgrade Longhorn to custom version
        ...    custom_cmd=yq eval -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.updateStrategy.rollingUpdate.maxUnavailable = 1' longhorn.yaml
        ...    wait=${False}
    END
    
    # Monitor longhorn-manager pods during upgrade
    # At least some pods should always be running
    WHILE    True
        Run command and not expect output
        ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=longhorn-manager --field-selector=status.phase=Running --no-headers | wc -l
        ...    0
        
        # Check if all Longhorn components are running (upgrade finished)
        ${all_running}=    Is Longhorn components all running
        IF    ${all_running} == ${True}
            Log To Console    Upgrade completed - all Longhorn components are running
            BREAK
        ELSE
            Log To Console    Upgrade in progress - monitoring pod availability
        END
        
        Sleep    1s
    END
    
    Then Wait for Longhorn components all running

Test CSI Components Rolling Update Configuration During Upgrade
    [Tags]    upgrade
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
    ...                3. Upgrade Longhorn (don't wait)
    ...                4. Monitor during upgrade that running CSI pods count is not 0 for each component
    
    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed
    
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END
    
    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    
    # Start upgrade without waiting (CSI components should have maxUnavailable=1 by default)
    Upgrade Longhorn to custom version    wait=${False}
    
    # Monitor CSI component pods during upgrade
    # At least some pods of each component should always be running
    WHILE    True
        # Check csi-attacher
        Run command and not expect output
        ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=csi-attacher --field-selector=status.phase=Running --no-headers | wc -l
        ...    0
        
        # Check csi-provisioner
        Run command and not expect output
        ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=csi-provisioner --field-selector=status.phase=Running --no-headers | wc -l
        ...    0
        
        # Check csi-resizer
        Run command and not expect output
        ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=csi-resizer --field-selector=status.phase=Running --no-headers | wc -l
        ...    0
        
        # Check csi-snapshotter
        Run command and not expect output
        ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=csi-snapshotter --field-selector=status.phase=Running --no-headers | wc -l
        ...    0
        
        # Check if all Longhorn components are running (upgrade finished)
        ${all_running}=    Is Longhorn components all running
        IF    ${all_running} == ${True}
            Log To Console    Upgrade completed - all Longhorn components are running
            BREAK
        ELSE
            Log To Console    Upgrade in progress - monitoring pod availability
        END
        
        Sleep    1s
    END
    
    Then Wait for Longhorn components all running
