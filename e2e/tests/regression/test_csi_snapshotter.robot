*** Settings ***
Documentation    CSI Volume Snapshot Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/csi_volume_snapshot.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test CSI Volume Snapshot Associated With Longhorn Snapshot
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy
    And Write 256 MB data to file data.txt in deployment 0

    When Create csi volume snapshot class 0    type=snap
    And Create csi volume snapshot 0 for persistentvolumeclaim 0
    Then Wait for csi volume snapshot 0 to be ready
    And Longhorn snapshot associated with csi volume snapshot 0 of deployment 0 should be created
