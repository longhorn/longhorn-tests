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
Resource    ../keywords/backup.resource

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

Test Recurring Job Group Labels Sync From PVC Without Source Label
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13928
    ...    1. Create a StorageClass and a PVC labeled with RecurringJob groups
    ...       (default and rebuildable) but without recurring-job.longhorn.io/source=enabled.
    ...    2. Create a deployment that consumes the PVC.
    ...    3. Verify the Volume CR has both group labels.
    ...    4. Verify Longhorn infers recurring-job.longhorn.io/source=enabled on the PVC.
    ...    5. Add another group label on the bound PVC and verify it syncs to the Volume CR.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test    labels={"recurring-job-group.longhorn.io/default":"enabled","recurring-job-group.longhorn.io/rebuildable":"enabled"}
    And Create deployment 0 with persistentvolumeclaim 0

    Then Check volume of deployment 0 has recurringjob group default
    And Check volume of deployment 0 has recurringjob group rebuildable
    And Check persistentvolumeclaim 0 has label recurring-job.longhorn.io/source enabled

    When Label persistentvolumeclaim 0 with recurring-job-group.longhorn.io/extra enabled
    Then Check volume of deployment 0 has recurringjob group extra
    And Check volume of deployment 0 has recurringjob group default
    And Check volume of deployment 0 has recurringjob group rebuildable

Test Recurring Job Group Labels Sync After PVC Is Bound
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13928
    ...    1. Create a StorageClass and a PVC with no RecurringJob labels.
    ...    2. Create a deployment that consumes the PVC.
    ...    3. Label the already-bound PVC with recurring-job-group.longhorn.io/default=enabled
    ...       without setting recurring-job.longhorn.io/source=enabled.
    ...    4. Verify the Volume CR joins the default group and the source label is inferred.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0

    When Label persistentvolumeclaim 0 with recurring-job-group.longhorn.io/default enabled
    Then Check volume of deployment 0 has recurringjob group default
    And Check persistentvolumeclaim 0 has label recurring-job.longhorn.io/source enabled

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

Test Snapshot Not Deleted While Referenced By An In-Progress Backup During Recurring Cleanup
    [Documentation]
    ...    Verify that a snapshot referenced by a non-terminal (New/Pending/InProgress) Backup CR
    ...    is protected from deletion when the same backup recurring job's cleanup step runs again
    ...    on a later scheduled execution.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/10184
    ...
    ...    A recurring backup creates its Snapshot and Backup CR, but the recurring-job process
    ...    can exit before the asynchronous backup reaches a terminal state (the Backup CR can
    ...    remain New, Pending, or InProgress). A later scheduled run of the *same* recurring job
    ...    then generates a new job.snapshotName and calls doSnapshotCleanup(false) before creating
    ...    its new snapshot. Since filterExpiredSnapshotsOfCurrentRecurringJob() only retained the
    ...    newly generated snapshot name and the last completed backup snapshot -- without
    ...    inspecting Backup.Spec.SnapshotName on non-terminal Backup CRs -- the prior active
    ...    backup's source snapshot became eligible for deletion, and the Backup controller could
    ...    then no longer find its source Snapshot CR.
    ...
    ...    Steps:
    ...    1. Create a volume, attach it, and start continuously writing data to it so that every
    ...       backup taken by the recurring job always has fresh data to transfer and therefore
    ...       takes longer than one cron interval to complete
    ...    2. Create a single backup recurring job (retain=10, to keep the unrelated retain-count
    ...       aging mechanism from ever pruning our tracked backup/snapshot) with a short cron
    ...       interval
    ...    3. Wait for the first backup to be created and complete, and record its name
    ...    4. Repeat 5 times:
    ...       4.1 Wait for the recurring job's next pod to be created (or a new backup to be
    ...           in progress), confirming a new scheduled run has started while the previously
    ...           recorded backup may still be settling
    ...       4.2 Check that the snapshot for the previously recorded backup still exists, i.e.
    ...           it was not removed by the new run's cleanup
    ...       4.3 Wait for the new backup to complete and update the recorded backup name
    Given Setting auto-cleanup-recurring-job-backup-snapshot is set to false
    Given Create volume vol-0 with    size=5Gi    dataEngine=${DATA_ENGINE}
    And Attach volume vol-0
    And Wait for volume vol-0 healthy
    And Keep writing data to volume vol-0    size=3Gi

    When Create backup recurringjob 0    groups=["default"]    cron=* * * * *    retain=10

    # wait for the first backup to be created and record it
    Then Wait for backup recurringjob 0 started
    And Wait for backup recurringjob 0 complete
    ${backup_name} =    Run command
    ...    kubectl get backups -n longhorn-system -l backup-volume\=vol-0 --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}'

    FOR    ${i}    IN RANGE    5
        And Wait for backup recurringjob 0 started
        And Check snapshot for backup ${backup_name} of volume vol-0 exists
        And Verify backup list contains no error for volume vol-0

        And Wait for backup recurringjob 0 complete
        And Check snapshot for backup ${backup_name} of volume vol-0 exists
        And Verify backup list contains no error for volume vol-0

        ${backup_name} =    Run command
        ...    kubectl get backups -n longhorn-system -l backup-volume\=vol-0 --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}'
    END
