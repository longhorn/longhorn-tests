*** Settings ***
Documentation    Negative Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/volume.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test System Backup Recurring Job When volume-backup-policy is disabled
    [Tags]    recurring-job    system-backup-recurring-job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"disabled"}

    Then Assert recurringjob 0 not created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state

Test System Backup Recurring Job When volume-backup-policy is if-not-present
    [Tags]    recurring-job    system-backup-recurring-job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"if-not-present"}

    Then Assert recurringjob 0 created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state

Recurring Job Pod Should Not Crash
    [Tags]    regression    recurring-job
    [Documentation]
    ...    Ensures that the recurring job pod executes successfully without crashing
    ...    or restarting.
    ...
    ...    This test validates the stability of the recurring job pod by verifying
    ...    that the pod does not enter error state (e.g., CrashLoopBackOff) or experience
    ...    unexpected restarts during its lifecycle.
    ...
    ...    Related Issue:
    ...    - https://github.com/longhorn/longhorn/issues/11016 (Approximate reproduction rate: 1/10)

    ${NUM_VOLUMES} =    Set Variable    20

    FOR   ${i}    IN RANGE    ${NUM_VOLUMES}
        Given Create volume ${i} with    size=50Mi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
        And Attach volume ${i}
        And Wait for volume ${i} healthy
    END

    When Create snapshot recurringjob 0
    ...    groups=["default"]
    ...    cron=*/1 * * * *
    ...    concurrency=5
    ...    labels={"test":"recurringjob"}

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Then Sleep    1m     # Wait for the next scheduled run
        And Log To Console    "Waiting for snapshot recurringjob 0 to complete... (${i+1}/${LOOP_COUNT})"
        And Wait for snapshot recurringjob 0 to complete without error
    END
