*** Settings ***
Documentation    CSI Test Cases

Test Tags    regression    csi

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource

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
