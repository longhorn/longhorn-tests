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
Resource    ../keywords/snapshot.resource

Library    random

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

Test Volume Deletion During Recurring Job Execution
    [Tags]    snapshot-purge
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11925
    ...    1. Create multiple volumes, write data, create a system-created snapshot (via rebuilding) then create a regular snapshot.
    ...    2. Launch a snapshot-cleanup recurring job for all volumes. Make sure the concurrency is 1. (So that the job will be executed for a long time and we have a chance to remove a volume.)
    ...    3. Wait for the recurring job to trigger and monitor its log.
    ...    4. When log Found %v volumes with recurring job %v is printed, remove one volume that has not been purged by the job immediately.
    FOR   ${i}    IN RANGE    10
        Given Create volume ${i} with    size=64Mi    dataEngine=${DATA_ENGINE}
        And Attach volume ${i}
        And Wait for volume ${i} healthy
        And Write 32 Mi data to volume ${i}
        # create system-created snapshots by triggering replica rebuilding
        # for further snapshot-cleanup recurring job
        And Delete volume ${i} replica on node 0
    END
    FOR   ${i}    IN RANGE    10
        And Wait for volume ${i} healthy
        And Create snapshot ${i} of volume ${i}
    END
    When Create snapshot-cleanup recurringjob snapshot-cleanup-job    groups=["default"]    cron=2 minutes from now
    And Run command and wait for output
    ...    kubectl logs -l recurring-job.longhorn.io=snapshot-cleanup-job -n longhorn-system
    ...    volumes with recurring job
    # we have a total of 10 volumes
    # randomly delete 4 of them
    ${randoms}=    Evaluate    random.sample(range(0, 10), 4)    random
    FOR   ${i}    IN    @{randoms}
        Then Delete volume ${i}    wait=False
    END
    And Run command and not expect output
    ...    kubectl logs -l recurring-job.longhorn.io=snapshot-cleanup-job -n longhorn-system -f
    ...    panic

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

Test Recurring Job Concurrency
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/467
    ...    1. Create snapshot recurring job with concurrency set to 2 and include snapshot recurring job default in groups
    ...    2. Create and attach more than 5 volumes to test the recurring job concurrency
    ...    3. Monitor the cron job pod log. There should be 2 jobs created concurrently
    ...    4. Update the snapshot recurring job concurrency to 3
    ...    5. Monitor the cron job pod log. There should be 3 jobs created concurrently
    Given Create snapshot recurringjob 0
    ...    groups=["default"]
    ...    cron=* * * * *
    ...    concurrency=2

    FOR   ${i}    IN RANGE    10
        When Create volume ${i} with    size=128Mi    dataEngine=${DATA_ENGINE}
        And Attach volume ${i}
        And Wait for volume ${i} healthy
    END

    Then There should be 2 jobs created concurrently for snapshot recurringjob 0

    When Update snapshot recurringjob 0    concurrency=3
    Then There should be 3 jobs created concurrently for snapshot recurringjob 0
