*** Settings ***
Documentation    Pre-release Checks Test Case

Test Tags    pre-release

Library    OperatingSystem

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/engine_image.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Pre-release Checks
    [Documentation]    Pre-release Checks
    ...    1. Uninstall existing Longhorn
    ...    2. Install stable version of Longhorn
    ...    3. Create volumes and backups
    ...    4. Upgrade Longhorn
    ...    5. Upgrade volume engine images
    ...    6. Trigger replica rebuilding
    ...    7. Detach/Re-attach volumes
    ...    8. Restore backups
    ...    9. Uninstall Longhorn
    ...    10. Re-install Longhorn back for subsequent tests
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    # if Longhorn stable version is provided,
    # uninstall the existing Longhorn and upgrade Longhorn from the stable version
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        Given Set setting deleting-confirmation-flag to true
        And Uninstall Longhorn
        And Check Longhorn CRD removed

        And Install Longhorn stable version
        And Set backupstore
        And Set up v2 environment
    END

    And Create volume 0 with    dataEngine=v1
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    # use DATA_ENGINE to control whether to test v2 volumes in the test
    # because v1.8.x v2 volumes aren't compatible with v1.7.x ones
    # we have to manually decide whether to include v2 volumes
    # based on what upgrade path we're testing
    IF    "${DATA_ENGINE}" == "v2"
        And Create volume 1 with    dataEngine=v2
        And Attach volume 1
        And Wait for volume 1 healthy
        And Write data 1 to volume 1
        And Create backup 1 for volume 1
        And Detach volume 1
        And Wait for volume 1 detached
    END

    ${LONGHORN_TRANSIENT_VERSION}=    Get Environment Variable    LONGHORN_TRANSIENT_VERSION    default=''
    IF    '${LONGHORN_TRANSIENT_VERSION}' != ''
        When Upgrade Longhorn to transient version
    END
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        When Upgrade Longhorn to custom version
        ${CUSTOM_LONGHORN_ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default='undefined'
        Then Upgrade volume 0 engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
    END

    When Delete volume 0 replica on node 1
    Then Wait until volume 0 replica rebuilding started on node 1
    And Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

    When Detach volume 0
    And Wait for volume 0 detached
    Then Attach volume 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

    When Create volume 2 from backup 0 of volume 0
    Then Wait for volume 2 restoration from backup 0 of volume 0 start
    And Wait for volume 2 detached
    And Attach volume 2
    And Check volume 2 data is backup 0 of volume 0

    IF    "${DATA_ENGINE}" == "v2"
        When Attach volume 1
        Then Wait for volume 1 healthy
        And Check volume 1 data is intact

        When Delete volume 1 replica on node 1
        Then Wait until volume 1 replica rebuilding started on node 1
        And Wait until volume 1 replica rebuilding completed on node 1
        And Wait for volume 1 healthy
        And Check volume 1 data is intact

        When Create volume 3 from backup 1 of volume 1
        Then Wait for volume 3 restoration from backup 1 of volume 1 start
        And Wait for volume 3 detached
        And Attach volume 3
        And Check volume 3 data is backup 1 of volume 1
    END

    # test uninstalling Longhorn
    Then Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    # install Longhorn back for subsequent tests
    And Install Longhorn
