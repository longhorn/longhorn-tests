*** Settings ***
Documentation    Metric Test Cases

Test Tags    regression    metric

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/metrics.resource

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks

*** Test Cases ***
Test longhorn_node_storage_scheduled_bytes Metric
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11949
    When Create volume 0 with    size=2Gi    dataEngine=v1
    And Create volume 1 with    size=4Gi    dataEngine=v2
    Then Metric longhorn_node_storage_scheduled_bytes value should be 6Gi
