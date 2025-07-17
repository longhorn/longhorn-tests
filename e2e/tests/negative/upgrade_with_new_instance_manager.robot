*** Settings ***
Documentation    Negative Test Cases

Test Tags    upgrade    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test System Upgrade with New Instance Manager
    # Test case only work in 2 stage upgrade scenario due to
    # maximum value of guaranteed-instance-manager-cpu is 40
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    ${LONGHORN_TRANSIENT_VERSION}=    Get Environment Variable    LONGHORN_TRANSIENT_VERSION    default=''
    IF    '${LONGHORN_TRANSIENT_VERSION}' == ''
        Fail    Environment variable LONGHORN_TRANSIENT_VERSION is not set
    END

    Given Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And Set setting guaranteed-instance-manager-cpu to 40
    And Check v1 instance manager pods recreated
    And Create volume vol1 with    dataEngine=v1
    And Attach volume vol1
    And Wait for volume vol1 healthy

    When Upgrade Longhorn to transient version
    And Create volume vol2 with    dataEngine=v1
    And Attach volume vol2
    And Wait for volume vol2 healthy

    # Instance Manager flapping between ContainerCreating, OutOfcpu, Terminating,
    # It is hard to detect and we can use vol3 faulted to validate the situation
    When Upgrade Longhorn to custom version should fail
    And Create volume vol3 with    dataEngine=v1
    And Wait for volume vol3 faulted
    And Detach volume vol1
    And Wait for volume vol1 detached
    And Attach volume vol3
    Then Wait for volume vol3 healthy
