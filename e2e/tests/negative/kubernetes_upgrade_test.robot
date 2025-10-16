*** Settings ***
Documentation    Manual Test Cases
Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Upgrade Kubernetes To Latest Version
    Given Create volume 0    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create volume 1    dataEngine=${DATA_ENGINE}

    When Install system upgrade controller
    Then Upgrade kubernetes to latest version

    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Attach volume 1
    And Wait for volume 1 healthy

Test Upgrade Kubernetes To Latest Version With Drain
    Given Create volume 0    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create volume 1    dataEngine=${DATA_ENGINE}

    When Install system upgrade controller
    Then Upgrade kubernetes to latest version    drain=True

    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Attach volume 1
    And Wait for volume 1 healthy
