*** Settings ***
Documentation    Zone Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Replica Zone Hard Anti Affinity
    [Documentation]    Test replica scheduling with replica-zone-soft-anti-affinity set to false
    Given Set setting replica-zone-soft-anti-affinity to false

    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone1

    When Create volume 0    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    Then Wait for volume 0 condition scheduled to be false
    And Wait for volume 0 degraded

    When Set k8s node 2 zone lh-zone2
    Then Wait for volume 0 condition scheduled to be true
    And Wait for volume 0 healthy

Test Replica Zone Soft Anti Affinity
    [Documentation]    Test replica scheduling with replica-zone-soft-anti-affinity set to true
    Given Set setting replica-zone-soft-anti-affinity to true

    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone0
    And Set k8s node 2 zone lh-zone0

    When Create volume 0    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    Then Wait for volume 0 condition scheduled to be true
    And Wait for volume 0 healthy
