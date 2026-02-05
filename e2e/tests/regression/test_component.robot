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

Test Rolling Update Strategy Configuration
    [Documentation]    Test rolling update strategy configuration for longhorn-manager and CSI deployments
    ...
    ...                https://github.com/longhorn/longhorn/issues/12240
    ...
    ...                Validates that:
    ...                1. longhorn-manager DaemonSet has a RollingUpdate strategy with maxUnavailable configured
    ...                2. longhorn-csi-plugin DaemonSet has a RollingUpdate strategy with maxUnavailable configured
    ...                3. CSI deployment components (csi-attacher, csi-provisioner, csi-resizer, csi-snapshotter) have RollingUpdate strategy with maxUnavailable set to 1

    # Check longhorn-manager DaemonSet has rolling update strategy configured
    # Note: maxUnavailable is user-configurable, so we only verify it's set (not checking a specific value)
    Then Check DaemonSet Rolling Update Max Unavailable    longhorn-manager

    # Check longhorn-csi-plugin DaemonSet has rolling update strategy configured
    # Note: maxUnavailable is user-configurable, so we only verify it's set (not checking a specific value)
    Then Check DaemonSet Rolling Update Max Unavailable    longhorn-csi-plugin

    # Check CSI deployment components have rolling update strategy with maxUnavailable=1
    # Note: CSI deployments should have maxUnavailable=1 by default for safer rolling updates
    Then Check Deployment Rolling Update Max Unavailable    csi-attacher    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-provisioner    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-resizer    expected_max_unavailable=1
    Then Check Deployment Rolling Update Max Unavailable    csi-snapshotter    expected_max_unavailable=1
