*** Settings ***
Documentation    Negative Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/volume.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test System Backup Recurring Job When volume-backup-policy is disabled
    [Tags]    recurring_job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"disabled"}

    Then Assert recurringjob not created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state

Test System Backup Recurring Job When volume-backup-policy is if-not-present
    [Tags]    recurring_job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"if-not-present"}

    Then Assert recurringjob created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state
