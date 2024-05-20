*** Settings ***
Documentation    Backup Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***
Test Backup Volume List
    [Documentation]    Test Backup Volume List
    ...    We want to make sure that an error when listing a single backup volume
    ...    does not stop us from listing all the other backup volumes. Otherwise a
    ...    single faulty backup can block the retrieval of all known backup volumes.
    Given Create volume 0
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1
    And Attach volume 1
    And Wait for volume 1 healthy

    When Create backup 0 for volume 0
    And Create backup 1 for volume 1
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains no error for volume 1
    And Verify backup list contains backup 0 of volume 0
    And Verify backup list contains backup 1 of volume 1

    When Place file backup_1234@failure.cfg into the backups folder of volume 0
    Then Verify backup list contains no error for volume 0
    And Verify backup list contains no error for volume 1
    And Verify backup list contains backup 0 of volume 0
    And Verify backup list contains backup 1 of volume 1

    And Delete backup volume 0
    And Delete backup volume 1
