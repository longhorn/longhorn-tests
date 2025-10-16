*** Settings ***
Documentation    Recurring Job Test Cases

Test Tags    regression    recurring-job

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Recurring Job Assignment Using StorageClass
    Given Create snapshot recurringjob snapshot-job    cron=*/2 * * * *
    And Create backup recurringjob backup-job    groups=["backup-job-group"]    cron=*/2 * * * *

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    recurringJobSelector=[{"name":"snapshot-job", "isGroup":false},{"name":"backup-job-group", "isGroup":true}]
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0

    Then Check volume of deployment 0 has recurringjob snapshot-job
    And Check volume of deployment 0 has recurringjob group backup-job-group
    And Check snapshot recurringjob snapshot-job work for volume of deployment 0
    And Check backup recurringjob backup-job work for volume of deployment 0

Test System Backup Recurring Job When volume-backup-policy is disabled
    [Tags]    system-backup-recurring-job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"disabled"}

    Then Assert recurringjob 0 not created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state
    And Wait for volume 0 attached
    And Wait for volume 1 detached

Test System Backup Recurring Job When volume-backup-policy is if-not-present
    [Tags]    system-backup-recurring-job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1 with    size=2Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    When Create system-backup recurringjob 0    parameters={"volume-backup-policy":"if-not-present"}

    Then Assert recurringjob 0 created backup for volume 0
    And Wait for recurringjob 0 created systembackup to reach Ready state
    And Wait for volume 0 attached
    And Wait for volume 1 detached

Recurring Job Pod Should Not Crash
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
