*** Settings ***
Documentation    System Backup Test Cases

Test Tags    regression    system_backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/system_backup.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test System Backup And Restore
    [Tags]    coretest
    [Documentation]    Test system backup and restore
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create system backup 0
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0
    And Wait for volume 0 deleted

    When Restore system backup 0

    Then Wait for volume 0 to be created
    And Wait for volume 0 restoration to complete
    And Attach volume 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Uninstallation With System Backup
    [Tags]    uninstall
    [Documentation]    Test uninstall Longhorn with system backup
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    And Create system backup 0

    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    Then Install Longhorn
