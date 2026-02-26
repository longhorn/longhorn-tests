*** Settings ***
Documentation    Engine Image Test Cases

Test Tags    regression    engine_image

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/engine_image.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/network.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Replica Rebuilding After Engine Upgrade
    [Tags]    coretest
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support engine image upgrade
    END
    
    Given Create compatible engine image
    And Create volume 0
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    When Upgrade volume 0 engine to compatible engine image
    Then Delete volume 0 replica on node 1
    And Wait until volume 0 replica rebuilding started on node 1
    And Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Engine Upgrade With Extra Replicas
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support engine image upgrade
    END

    Given Create compatible engine image
    And Create volume 0    numberOfReplicas=3
    And Attach volume 0
    And Wait for volume 0 healthy
    When Update volume 0 replica count to 2
    Then Upgrade volume 0 engine to compatible engine image

Test Replicas Not Accumulate During Engine Upgrade
    [Documentation]    Verify that replicas do not accumulate during concurrent engine upgrade
    ...    Issue: https://github.com/longhorn/longhorn/issues/12111
    ...    1. Uninstall Longhorn
    ...    2. Reinstall stable version of Longhorn
    ...    3. Create 10 volumes
    ...    4. Set concurrent-automatic-engine-upgrade-per-node-limit = 10
    ...    5. Apply network latency to the control plane
    ...    6. Upgrade Longhorn to custom version
    ...    7. For all volumes, wait for their replica count to be 3
    [Tags]    coretest    upgrade

    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support engine image upgrade
    END

    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        ${CUSTOM_LONGHORN_ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default='undefined'
    ELSE
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn

    And Install Longhorn stable version

    FOR    ${i}    IN RANGE    10
        And Create volume ${i} with    dataEngine=v1
        And Attach volume ${i}
        And Wait for volume ${i} healthy
    END

    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 10

    And Setup control plane network latency to 1500 ms

    And Upgrade Longhorn to custom version

    FOR    ${i}    IN RANGE    10
        Then Volume ${i} should have 3 replicas
    END

    FOR    ${i}    IN RANGE    10
        And Wait for volume ${i} engine to be upgraded to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
    END

    FOR    ${i}    IN RANGE    10
        And Check volume ${i} works
    END
