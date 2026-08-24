*** Settings ***
Documentation    Recurring Job Test Cases

Test Tags    regression    recurring-job

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/host.resource

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
    ...    kubectl logs -l recurring-job.longhorn.io=snapshot-cleanup-job -n longhorn-system --follow
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

Test Snapshot Cleanup Recurring Job Cleans System Generated Snapshots During Replica Rebuild
    [Tags]    snapshot-cleanup
    [Documentation]    https://github.com/longhorn/longhorn/issues/13784
    ...    Verify snapshot-cleanup recurring job cleans system-generated snapshots on
    ...    an idle volume while another volume's replica is still rebuilding.
    ...
    ...    1. Set auto-cleanup-system-generated-snapshot to false.
    ...    2. Create volume 0 (2Gi) and volume 1 (15Gi), attach both and wait until healthy.
    ...       Write 14 GB of data to volume 1 to ensure its rebuild takes enough time
    ...       for the recurring job to run concurrently.
    ...    3. Delete one replica on volume 0 and wait for rebuild to complete.
    ...       Verify 1 system-generated snapshot now exists on volume 0.
    ...    4. Delete one replica on volume 0 again and wait for rebuild to complete.
    ...       Verify 2 system-generated snapshots now exist on volume 0.
    ...    5. Delete one replica on volume 1 (node 1) and wait for the rebuild to
    ...       start on node 0, so the recurring job runs while a rebuild is in progress.
    ...    6. Create a snapshot-cleanup recurring job targeting the default group
    ...       and wait for it to complete.
    ...    7. Verify volume 0 has 1 system-generated snapshot remaining (v1: the
    ...       snapshot immediately before volume-head cannot be deleted) or 0 (v2).
    ...    8. Wait for volume 1 to return to healthy.
    Given Setting auto-cleanup-system-generated-snapshot is set to false
    And Create volume 0 with    size=2Gi    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1 with    size=15Gi    dataEngine=${DATA_ENGINE}
    And Attach volume 1
    And Wait for volume 1 healthy
    And Write 14 GB data to volume 1

    # Rebuild volume 0 twice to accumulate 2 system-generated snapshots on v1
    When Delete volume 0 replica on node 0
    Then Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Wait for volume 0 to have 1 system generated snapshots
    When Delete volume 0 replica on node 0
    Then Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Wait for volume 0 to have 2 system generated snapshots

    When Delete volume 1 replica on node 1
    And Wait until volume 1 replica rebuilding started on node 0
    And Create snapshot-cleanup recurringjob snapshot-cleanup-job
    ...    groups=["default"]
    ...    cron=1 minutes from now
    And Wait for snapshot-cleanup recurringjob snapshot-cleanup-job complete

    # v1: 1 snapshot remains (direct parent of volume-head is undeletable)
    # v2: all cleaned up
    IF    '${DATA_ENGINE}' == 'v1'
        Then Wait for volume 0 to have 1 system generated snapshots
    ELSE
        Then Wait for volume 0 to have 0 system generated snapshots
    END

Verify Large Volume Data Integrity During Replica Rebuilding with Recurring Jobs
    [Documentation]
    ...    Issue: https://github.com/longhorn/longhorn/issues/10711
    ...    1. Enable the setting `Snapshot Data Integrity` and `Immediate Snapshot Data Integrity Check After Creating a Snapshot`
    ...    2. Create a 50 Gi volume. write around 30 Gi data into it.
    ...    3. Create a recurring job of snapshot & backup.
    ...    4. Delete a replica and wait for the replica rebuilding.
    ...    5. Check volume data is intact
    Given Setting snapshot-data-integrity is set to enabled
    And Setting snapshot-data-integrity-immediate-check-after-snapshot-creation is set to true
    And Create volume 0 with    size=50Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write 30 GB data to volume 0
    And Create recurringjob for volume 0 with    task=backup    cron=*/3 * * * *
    And Create recurringjob for volume 0 with    task=snapshot    cron=*/3 * * * *
    When Delete volume 0 replica on node 0
    Then Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
