*** Settings ***
Documentation    Longhorn Component Test Cases

Test Tags    regression

Library    OperatingSystem

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Revert Longhorn Manager Resources
    [Documentation]    Remove CPU/Memory requests and limits for longhorn-manager
    Remove Longhorn Manager Resource Limit
    Wait for Longhorn workloads pods stable
    ...    longhorn-manager
    Cleanup test resources

Reinstall Longhorn With Default Resources
    [Documentation]    Reinstall Longhorn with the default helm values to drop the
    ...                custom resource requests and limits.
    ${reinstall_required} =    Get Variable Value    \${longhorn_reinstall_required}    ${False}
    IF    ${reinstall_required}
        Setting deleting-confirmation-flag is set to true
        Uninstall Longhorn
        Check all Longhorn CRD removed
        Install Longhorn
        Wait for Longhorn components all running
    END
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
    Then Run command and wait for output
    ...    kubectl get pod -l app=longhorn-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-manager")].resources.requests}' -n longhorn-system
    ...    {"cpu":"600m","memory":"1Gi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-manager")].resources.limits}' -n longhorn-system
    ...    {"cpu":"2","memory":"3Gi"}

Test Longhorn Components Resource Limits Configuration
    [Tags]    uninstall    helm    upgrade
    [Documentation]    Test CPU/Memory requests and limits for longhorn-manager,
    ...                longhorn-global-manager and longhorn-ui are applied when
    ...                they are configured via helm values.
    ...
    ...                Issues: https://github.com/longhorn/longhorn/issues/14306
    ...                        https://github.com/longhorn/longhorn/issues/12225
    ...
    ...                1. Skip if the install method is not helm.
    ...                2. If LONGHORN_STABLE_VERSION is set, uninstall Longhorn and
    ...                   install the stable version first.
    ...                3. Install (or upgrade to) Longhorn with the resource requests and
    ...                   limits of longhorn-manager, longhorn-global-manager and
    ...                   longhorn-ui set by helm values.
    ...                4. Verify the pods of each component have the configured resources.
    ...                5. Create and attach a volume, and verify data can be written and read.
    [Teardown]    Reinstall Longhorn With Default Resources
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    Set Test Variable    ${longhorn_reinstall_required}    ${True}

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    ${custom_cmd} =    Catenate    SEPARATOR=${SPACE}
    ...    yq -i '
    ...    .longhornManager.resources = {"requests":{"cpu":"250m","memory":"512Mi"},"limits":{"cpu":"500m","memory":"1Gi"}} |
    ...    .longhornGlobalManager.resources = {"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"200m","memory":"256Mi"}} |
    ...    .longhornUI.resources = {"requests":{"cpu":"50m","memory":"64Mi"},"limits":{"cpu":"100m","memory":"128Mi"}}
    ...    ' values.yaml
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
        And Upgrade Longhorn to custom version    custom_cmd=${custom_cmd}
    ELSE
        When Install Longhorn    custom_cmd=${custom_cmd}
    END
    And Wait for Longhorn components all running

    Then Run command and wait for output
    ...    kubectl get pod -l app=longhorn-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-manager")].resources.requests}' -n longhorn-system
    ...    {"cpu":"250m","memory":"512Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-manager")].resources.limits}' -n longhorn-system
    ...    {"cpu":"500m","memory":"1Gi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-global-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-global-manager")].resources.requests}' -n longhorn-system
    ...    {"cpu":"100m","memory":"128Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-global-manager -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-global-manager")].resources.limits}' -n longhorn-system
    ...    {"cpu":"200m","memory":"256Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-ui -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-ui")].resources.requests}' -n longhorn-system
    ...    {"cpu":"50m","memory":"64Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-ui -o jsonpath='{.items[0].spec.containers[?(@.name=="longhorn-ui")].resources.limits}' -n longhorn-system
    ...    {"cpu":"100m","memory":"128Mi"}

    # Longhorn still works with the resource requests and limits
    IF    "${DATA_ENGINE}" == "v2"
        And Enable v2 data engine and add block disks
    END
    When Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact

Test Longhorn Manager Rolling Update Configuration During Upgrade
    [Tags]    upgrade    helm
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
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END

    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed
    
    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    
    # Prepare custom command for upgrade with maxUnavailable=1
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        # Start upgrade without waiting - returns process object
        Upgrade Longhorn to custom version
        ...    custom_cmd=yq -i '.longhornManager.updateStrategy.rollingUpdate.maxUnavailable = 1' values.yaml
        ...    wait=${False}
    ELSE
        # For manifest, maxUnavailable is in longhorn.yaml DaemonSet spec
        Upgrade Longhorn to custom version
        ...    custom_cmd=yq -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.updateStrategy.rollingUpdate.maxUnavailable = 1' longhorn.yaml
        ...    wait=${False}
    END
    
    # Wait for longhorn-driver-deployer pods to be recreated to ensure upgrade started
    And Wait for deployment longhorn-driver-deployer pods recreated    namespace=${LONGHORN_NAMESPACE}
    
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
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END

    # Uninstall and install stable version
    Given Setting deleting-confirmation-flag is set to true
    When Uninstall Longhorn
    Then Check Longhorn CRD removed

    When Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
    
    # Start upgrade without waiting (CSI components should have maxUnavailable=1 by default)
    Upgrade Longhorn to custom version    wait=${False}
    
    # Wait for longhorn-driver-deployer pods to be recreated to ensure upgrade started
    And Wait for deployment longhorn-driver-deployer pods recreated    namespace=${LONGHORN_NAMESPACE}
    
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
