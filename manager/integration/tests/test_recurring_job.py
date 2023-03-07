import pytest
import time
import json

from datetime import datetime

from kubernetes.client.rest import ApiException

import backupstore
from backupstore import set_random_backupstore  # NOQA

import common
from common import client, core_api, apps_api, batch_v1_api  # NOQA
from common import csi_pv  # NOQA
from common import pod_make  # NOQA
from common import pvc  # NOQA
from common import random_labels, volume_name  # NOQA
from common import storage_class, statefulset, pvc  # NOQA
from common import make_deployment_with_pvc  # NOQA

from common import get_self_host_id

from common import create_storage_class

from common import create_pv_for_volume

from common import create_pvc_for_volume

from common import create_and_check_volume
from common import read_volume_data
from common import wait_for_volume_detached
from common import wait_for_volume_expansion
from common import wait_for_volume_healthy
from common import wait_for_volume_healthy_no_frontend
from common import wait_for_volume_recurring_job_update
from common import wait_volume_kubernetes_status
from common import write_pod_volume_random_data
from common import write_volume_random_data

from common import create_and_wait_deployment
from common import wait_deployment_replica_ready

from common import create_and_wait_statefulset
from common import get_statefulset_pod_info
from common import update_statefulset_manifests

from common import check_pod_existence
from common import exec_command_in_pod
from common import prepare_pod_with_data_in_mb

from common import crash_engine_process_with_sigkill

from common import find_backup
from common import wait_for_backup_volume
from common import wait_for_backup_completion
from common import wait_for_backup_count
from common import wait_for_backup_to_start

from common import create_snapshot
from common import wait_for_snapshot_count

from common import check_recurring_jobs
from common import cleanup_all_recurring_jobs
from common import create_recurring_jobs
from common import update_recurring_job

from common import wait_for_cron_job_count
from common import wait_for_cron_job_create
from common import wait_for_cron_job_delete

from common import JOB_LABEL
from common import KUBERNETES_STATUS_LABEL
from common import LONGHORN_NAMESPACE
from common import RETRY_BACKUP_COUNTS
from common import RETRY_BACKUP_INTERVAL
from common import SETTING_RECURRING_JOB_WHILE_VOLUME_DETACHED
from common import SIZE, Mi, Gi
from common import SETTING_RESTORE_RECURRING_JOBS
from common import VOLUME_HEAD_NAME


RECURRING_JOB_LABEL = "RecurringJob"
RECURRING_JOB_NAME = "recurring-test"

NAME = "name"
ISGROUP = "isGroup"
TASK = "task"
GROUPS = "groups"
CRON = "cron"
RETAIN = "retain"
SNAPSHOT = "snapshot"
SNAPSHOT_DELETE = "snapshot-delete"
SNAPSHOT_CLEANUP = "snapshot-cleanup"
BACKUP = "backup"
FILESYSTEM_TRIM = "filesystem-trim"
CONCURRENCY = "concurrency"
LABELS = "labels"
DEFAULT = "default"
SCHEDULE_1MIN = "* * * * *"

WRITE_DATA_INTERVAL = 10


def wait_until_begin_of_a_minute():
    while True:
        current_time = datetime.utcnow()
        if current_time.second == 0:
            break
        time.sleep(1)


def wait_until_begin_of_an_even_minute():
    while True:
        current_time = datetime.utcnow()
        if current_time.second == 0 and current_time.minute % 2 == 0:
            break
        time.sleep(1)


# wait for backup progress created by recurring job to
# exceed the minimum_progress percentage.
def wait_for_recurring_backup_to_start(client, core_api, volume_name, expected_snapshot_count, minimum_progress=0):  # NOQA
    job_pod_name = volume_name + '-backup-c'
    snapshot_name = ''
    snapshots = []
    check_pod_existence(core_api, job_pod_name, namespace=LONGHORN_NAMESPACE)

    # Find the snapshot which is being backed up
    for _ in range(RETRY_BACKUP_COUNTS):
        volume = client.by_id_volume(volume_name)
        try:
            snapshots = volume.snapshotList()

            assert len(snapshots) == expected_snapshot_count + 1
            for snapshot in snapshots:
                if snapshot.children['volume-head']:
                    snapshot_name = snapshot.name
                    break
            if len(snapshot_name) != 0:
                break
        except (AttributeError, ApiException, AssertionError):
            time.sleep(RETRY_BACKUP_INTERVAL)
    assert len(snapshot_name) != 0

    # To ensure the progress of backup
    wait_for_backup_to_start(client, volume_name,
                             snapshot_name=snapshot_name,
                             chk_progress=minimum_progress)

    return snapshot_name


@pytest.mark.recurring_job  # NOQA
def test_recurring_job(set_random_backupstore, client, volume_name):  # NOQA
    """
    Scenario : test recurring job (S3/NFS)

    Given `snapshot1` recurring job created and cron at 1 min and retain 2.
          `backup1`   recurring job created and cron at 2 min and retain 1.
          `backup2`   recurring job created and cron at 1 min and retain 2.
    And a volume created and attached.

    When label volume with recurring job `snapshot1`.
         label volume with recurring job `backup1`.
    And wait until the 20th second since the beginning of an even minute.
    And write data to volume.
        wait for 2 minutes.
    And write data to volume.
        wait for 2 minutes.
    Then volume have 4 snapshots.
         (2 from `snapshot1`, 1 from `backup1`, 1 from `volume-head`)

    When label volume with recurring job `backup2`
    And write data to volume.
        wait for 2 minutes.
    And write data to volume.
        wait for 2 minutes.
    Then volume have 5 snapshots.
         (2 from `snapshot1`, 1 from `backup1`, 1 from `backup2`,
          1 from `volume-head`)

    When wait until backups complete.
    Then `backup1` completed 2 backups.
         `backup2` completed 3 backups.
    """

    '''
    The timeline looks like this:
    0   1   2   3   4   5   6   7   8   9   10     (minute)
    |W  |   | W |   |   |W  |   | W |   |   |      (write data)
    |   S   |   S   |   |   S   |   S   |   |      (snapshot1)
    |   |   B   |   B   |   |   |   |   |   |      (backup1)
    |   |   |   |   |   |   B   B   B   |   |      (backup2)
    '''

    snap1 = SNAPSHOT + "1"
    back1 = BACKUP + "1"
    back2 = BACKUP + "2"
    recurring_jobs = {
        snap1: {
            TASK: SNAPSHOT,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
        back1: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
        back2: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)
    volume = volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)
    volume.recurringJobAdd(name=snap1, isGroup=False)
    volume.recurringJobAdd(name=back1, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[snap1, back1],
                                         groups=[DEFAULT])

    wait_until_begin_of_an_even_minute()
    # wait until the 20th second of an even minute
    # make sure that snapshot job happens before the backup job
    time.sleep(20)

    write_volume_random_data(volume)
    time.sleep(60 * 2)
    write_volume_random_data(volume)
    time.sleep(60 * 2)

    wait_for_snapshot_count(volume, 4)

    volume.recurringJobAdd(name=back2, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[snap1, back1, back2],
                                         groups=[DEFAULT])

    write_volume_random_data(volume)
    time.sleep(60 * 2)
    write_volume_random_data(volume)
    time.sleep(60 * 2)

    # 2 from job_snap, 1 from job_backup, 1 from job_backup2, 1 volume-head
    wait_for_snapshot_count(volume, 5)

    complete_backup_1_count = 0
    complete_backup_2_count = 0
    volume = client.by_id_volume(volume_name)
    wait_for_backup_completion(client, volume_name)
    for b in volume.backupStatus:
        if "backup1-" in b.snapshot:
            complete_backup_1_count += 1
        elif "backup2-" in b.snapshot:
            complete_backup_2_count += 1

    # 1 completed backups from backup1
    # 2 completed backups from backup2
    # NOTE: NFS backup can be slow sometimes and error prone
    assert complete_backup_1_count == 1
    assert complete_backup_2_count == 2


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_volume_creation(client, volume_name):  # NOQA
    """
    Scenario: test create volume with recurring jobs

    Given 2 recurring jobs created.
    And volume create and a attached.

    When label recurring job to volume.
    And write data to volume.
        wait 2.5 minutes.
    And write data to volume.
        wait 2.5 minutes.

    Then volume have 4 snapshots.
    """
    recurring_jobs = {
        SNAPSHOT: {
            TASK: SNAPSHOT,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
        BACKUP: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    volume.recurringJobAdd(name=SNAPSHOT, isGroup=False)
    volume.recurringJobAdd(name=BACKUP, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[SNAPSHOT, BACKUP],
                                         groups=[DEFAULT])

    wait_until_begin_of_an_even_minute()
    # wait until the 10th second of an even minute
    # to avoid writing data at the same time backup is taking
    time.sleep(10)

    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes
    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes

    wait_for_snapshot_count(volume, 4)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_duplicated(client):  # NOQA
    """
    Scenario: test create duplicated recurring jobs

    Given recurring job created.
    When create same recurring job again.
    Then should fail.
    """
    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    with pytest.raises(Exception) as e:
        create_recurring_jobs(client, recurring_jobs)
    assert "already exists" in str(e.value)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_storageclass(set_random_backupstore, client, core_api, storage_class, statefulset):  # NOQA
    """
    Test create volume with StorageClass contains recurring jobs

    1. Create a StorageClass with recurring jobs
    2. Create a StatefulSet with PVC template and StorageClass
    3. Verify the recurring jobs run correctly.
    """
    recurring_jobs = {
        SNAPSHOT: {
            TASK: SNAPSHOT,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
        BACKUP: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    recurring_job_selector = [
        {
            NAME: SNAPSHOT,
            ISGROUP: False,
        },
        {
            NAME: BACKUP,
            ISGROUP: False,
        },
    ]
    storage_class["parameters"]["recurringJobSelector"] = \
        json.dumps(recurring_job_selector)
    create_storage_class(storage_class)

    # wait until the beginning of an even minute
    wait_until_begin_of_an_even_minute()

    statefulset_name = 'recurring-job-in-storageclass-test'
    update_statefulset_manifests(statefulset, storage_class, statefulset_name)
    start_time = datetime.utcnow()
    create_and_wait_statefulset(statefulset)
    statefulset_creating_duration = datetime.utcnow() - start_time

    assert 150 > statefulset_creating_duration.seconds

    # We want to write data exactly at the 150th second since the start_time
    time.sleep(150 - statefulset_creating_duration.seconds)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volume_info = [p['pv_name'] for p in pod_info]
    pod_names = [p['pod_name'] for p in pod_info]

    # write random data to volume to trigger recurring snapshot and backup job
    volume_data_path = "/data/test"
    for pod_name in pod_names:
        write_pod_volume_random_data(core_api, pod_name, volume_data_path, 2)

    time.sleep(150)  # 2.5 minutes

    for volume_name in volume_info:  # NOQA
        volume = client.by_id_volume(volume_name)
        wait_for_snapshot_count(volume, 4)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_labels(set_random_backupstore, client, random_labels, volume_name):  # NOQA
    """
    Scenario: test a recurring job with labels (S3/NFS)

    Given a recurring job created,
            with `default` in groups,
            with random labels.
    And volume created and attached.
    And write data to volume.

    When add another label to the recurring job.
    And write data to volume.
    And wait after scheduled time.

    Then should have 2 snapshots.
    And backup should have correct labels.
    """
    recurring_job_labels_test(client, random_labels, volume_name)  # NOQA


def recurring_job_labels_test(client, labels, volume_name, size=SIZE, backing_image=""):  # NOQA
    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: labels,
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    client.create_volume(name=volume_name, size=size,
                         numberOfReplicas=2, backingImage=backing_image)
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    write_volume_random_data(volume)

    time.sleep(75 - WRITE_DATA_INTERVAL)  # 1 minute 15 second
    labels["we-added-this-label"] = "definitely"
    update_recurring_job(client, RECURRING_JOB_NAME,
                         recurring_jobs[RECURRING_JOB_NAME][GROUPS],
                         labels)
    write_volume_random_data(volume)

    time.sleep(135)  # 2 minute 15 second
    # 1 from Backup, 1 from Volume Head.
    wait_for_snapshot_count(volume, 2)

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    wait_for_backup_count(bv, 1)

    backups = bv.backupList().data
    b = bv.backupGet(name=backups[0].name)
    for key, val in iter(labels.items()):
        assert b.labels.get(key) == val
    assert b.labels.get(RECURRING_JOB_LABEL) == RECURRING_JOB_NAME
    # One extra Label from RecurringJob and another one below
    # Longhorn will automatically add a label `longhorn.io/volume-access-mode`
    # to a newly created backup
    assert len(b.labels) == len(labels) + 2
    wait_for_backup_volume(client, volume_name, backing_image)


@pytest.mark.csi  # NOQA
@pytest.mark.recurring_job
def test_recurring_job_kubernetes_status(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Scenario: test recurringJob properly backs up the KubernetesStatus (S3/NFS)

    Given volume created and detached.
    And PV from volume created and verified.

    When create backup recurring job to run every 2 minutes.
    And attach volume.
    And write some data to volume.
    And wait 5 minutes.

    Then volume have 2 snapshots.
         volume have 1 backup.
    And backup have the Kubernetes Status labels.
    """
    client.create_volume(name=volume_name, size=SIZE, numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pv_name = "pv-" + volume_name
    create_pv_for_volume(client, core_api, volume, pv_name)
    ks = {
        'pvName': pv_name,
        'pvStatus': 'Available',
        'namespace': '',
        'pvcName': '',
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    write_volume_random_data(volume)

    time.sleep(60 * 5)
    # 1 from Backup, 1 from Volume Head.
    wait_for_snapshot_count(volume, 2)

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    backups = bv.backupList().data
    wait_for_backup_count(bv, 1)

    b = bv.backupGet(name=backups[0].name)
    status = json.loads(b.labels.get(KUBERNETES_STATUS_LABEL))
    assert b.labels.get(RECURRING_JOB_LABEL) == RECURRING_JOB_NAME
    assert status == {
        'lastPodRefAt': '',
        'lastPVCRefAt': '',
        'namespace': '',
        'pvcName': '',
        'pvName': pv_name,
        'pvStatus': 'Available',
        'workloadsStatus': None
    }
    # Two Labels: KubernetesStatus and RecurringJob additional 1
    # Longhorn will automatically add a label `longhorn.io/volume-access-mode`
    # to a newly created backup
    assert len(b.labels) == 3


def test_recurring_jobs_maximum_retain(client, core_api, volume_name): # NOQA
    """
    Scenario: test recurring jobs' maximum retain

    Given set a recurring job retain to 101.

    When create recurring job.
    Then should fail.

    When set recurring job retain to 100.
    And create recurring job.
    Then recurring job created with retain equals to 100.

    When update recurring job retain to 101.
    Then should fail.
    """
    # set max total number of retain to exceed 100
    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 101,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }

    validator_error = "retain value should be less than or equal to 100"

    with pytest.raises(Exception) as e:
        create_recurring_jobs(client, recurring_jobs)
    assert validator_error.upper() in str(e.value).upper()

    recurring_jobs[RECURRING_JOB_NAME][RETAIN] = 100
    create_recurring_jobs(client, recurring_jobs)
    recurring_job = client.by_id_recurring_job(RECURRING_JOB_NAME)
    assert recurring_job.retain == 100

    with pytest.raises(Exception) as e:
        update_recurring_job(client, RECURRING_JOB_NAME,
                             groups=[], labels={}, retain=101)
    assert validator_error.upper() in str(e.value).upper()


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_detached_volume(client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test recurring job while volume is detached

    Given a volume created, and attached.
    And write some data to the volume.
    And detach the volume.

    When create a recurring job running at 1 minute interval,
            and with `default` in groups,
            and with `retain` set to `2`.
    And 1 cron job should be created.
    And wait for 2 minutes.
    And attach volume and wait until healthy

    Then the volume should have 1 snapshot

    When wait for 2 minute.
    Then then volume should have only 2 snapshots.
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)

    self_host = get_self_host_id()
    volume.attach(hostId=self_host)
    volume = wait_for_volume_healthy(client, volume_name)
    write_volume_random_data(volume)
    volume.detach()

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    time.sleep(60 * 2)
    volume.attach(hostId=self_host)
    volume = wait_for_volume_healthy(client, volume_name)

    wait_for_snapshot_count(volume, 1)

    time.sleep(60 * 2)
    wait_for_snapshot_count(volume, 2)


def test_recurring_jobs_allow_detached_volume(set_random_backupstore, client, core_api, apps_api, volume_name, make_deployment_with_pvc):  # NOQA
    """
    Scenario: test recurring jobs for detached volume with
    `allow-recurring-job-while-volume-detached` set to true

    Context: In the current Longhorn implementation, users cannot do recurring
             backup when volumes are detached.
             This feature gives the users an option to do recurring backup
             even when volumes are detached.
             longhorn/longhorn#1509

    Given `allow-recurring-job-while-volume-detached` set to `true`.
    And volume created and attached.
    And 50MB data written to volume.
    And volume detached.

    When a recurring job created runs every minute.
    And wait for backup to complete.

    Then volume have 1 backup in 2 minutes retry loop.

    When delete the recurring job.
    And create a PV from volume.
    And create a PVC from volume.
    And create a deployment from PVC.
    And write 400MB data to the volume from the pod.
    And scale deployment replicas to 0.
        wait until the volume is detached.
    And create a recurring job runs every 2 minutes.
    And wait for backup to start.
    And scale deployment replicas to 1.
    Then volume's frontend is disabled.
    And pod cannot start.

    When wait until backup complete.
    And delete the recurring job.
    Then pod can start in 10 minutes retry loop.
    """
    common.update_setting(client,
                          SETTING_RECURRING_JOB_WHILE_VOLUME_DETACHED, "true")

    volume = create_and_check_volume(client, volume_name, size=str(1 * Gi))
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume.name)

    data = {
        'pos': 0,
        'content': common.generate_random_data(50 * Mi),
    }
    common.write_volume_data(volume, data)

    # Give sometimes for data to flush to disk
    time.sleep(15)

    volume.detach(hostId="")
    volume = wait_for_volume_detached(client, volume.name)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    wait_for_backup_completion(client, volume.name)
    for _ in range(4):
        bv = client.by_id_backupVolume(volume.name)
        wait_for_backup_count(bv, 1)
        time.sleep(30)

    cleanup_all_recurring_jobs(client)

    pv_name = volume_name + "-pv"
    create_pv_for_volume(client, core_api, volume, pv_name)

    pvc_name = volume_name + "-pvc"
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    deployment_name = volume_name + "-dep"
    deployment = make_deployment_with_pvc(deployment_name, pvc_name)
    create_and_wait_deployment(apps_api, deployment)

    size_mb = 400
    pod_names = common.get_deployment_pod_names(core_api, deployment)
    write_pod_volume_random_data(core_api, pod_names[0], "/data/test",
                                 size_mb)

    deployment['spec']['replicas'] = 0
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])

    volume = wait_for_volume_detached(client, volume.name)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    wait_for_backup_to_start(client, volume.name)

    deployment['spec']['replicas'] = 1
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])

    deployment_label_name = deployment["metadata"]["labels"]["name"]
    common.wait_pod_attach_after_first_backup_completion(
        client, core_api, volume.name, deployment_label_name)

    cleanup_all_recurring_jobs(client)

    pod_names = common.get_deployment_pod_names(core_api, deployment)
    common.wait_for_pod_phase(core_api, pod_names[0], pod_phase="Running")


def test_recurring_jobs_when_volume_detached_unexpectedly(set_random_backupstore, client, core_api, apps_api, volume_name, make_deployment_with_pvc):  # NOQA
    """
    Scenario: test recurring jobs when volume detached unexpectedly

    Context: If the volume is automatically attached by the recurring backup
             job, make sure that workload pod eventually is able to use the
             volume when volume is detached unexpectedly during the backup
             process.

    Given `allow-recurring-job-while-volume-detached` set to `true`.
    And volume created and detached.
    And PV created from volume.
    And PVC created from volume.
    And deployment created from PVC.
    And 500MB data written to the volume.
    And deployment replica scaled to 0.
    And volume detached.

    When create a backup recurring job runs every 2 minutes.
    And wait for backup to start.
        wait for backup progress > 50%.
    And kill the engine process of the volume.
    Then volume is attached and healthy.

    When backup completed.
    Then volume is detached with `frontendDisabled=false`.

    When deployment replica scaled to 1.
    Then the data exist in the deployment pod.
    """
    common.update_setting(client,
                          SETTING_RECURRING_JOB_WHILE_VOLUME_DETACHED, "true")

    volume = create_and_check_volume(client, volume_name, size=str(2 * Gi))
    volume = wait_for_volume_detached(client, volume.name)

    pv_name = volume_name + "-pv"
    create_pv_for_volume(client, core_api, volume, pv_name)

    pvc_name = volume_name + "-pvc"
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    deployment_name = volume_name + "-dep"
    deployment = make_deployment_with_pvc(deployment_name, pvc_name)
    create_and_wait_deployment(apps_api, deployment)

    size_mb = 1000
    pod_names = common.get_deployment_pod_names(core_api, deployment)
    write_pod_volume_random_data(core_api, pod_names[0], "/data/test",
                                 size_mb)
    data = read_volume_data(core_api, pod_names[0], 'default')

    deployment['spec']['replicas'] = 0
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])
    volume = wait_for_volume_detached(client, volume_name)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume.recurringJobAdd(name=RECURRING_JOB_NAME, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[RECURRING_JOB_NAME],
                                         groups=[DEFAULT])

    time.sleep(60)
    wait_for_recurring_backup_to_start(client, core_api, volume_name,
                                       expected_snapshot_count=1,
                                       minimum_progress=50)

    crash_engine_process_with_sigkill(client, core_api, volume_name)
    time.sleep(10)
    wait_for_volume_healthy_no_frontend(client, volume_name)

    # Since the backup state is removed after the backup complete and it
    # could happen quickly. Checking for the both in-progress and complete
    # state could be hard to catch, thus we only check the complete state
    wait_for_backup_completion(client, volume_name)

    wait_for_volume_detached(client, volume_name)

    deployment['spec']['replicas'] = 1
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])
    wait_deployment_replica_ready(apps_api, deployment["metadata"]["name"], 1)
    pod_names = common.get_deployment_pod_names(core_api, deployment)
    assert read_volume_data(core_api, pod_names[0], 'default') == data

    # Use fixture to cleanup the backupstore and since we
    # crashed the engine replica initiated the backup, it's
    # backupstore lock will still be present, so we need
    # to wait till the lock is expired, before we can delete
    # the backups
    volume.recurringJobDelete(name=RECURRING_JOB_NAME, isGroup=False)
    backupstore.backupstore_wait_for_lock_expiration()


@pytest.mark.skip(reason="TODO")
def test_recurring_jobs_on_nodes_with_taints():  # NOQA
    """
    Test recurring jobs on nodes with taints

    Context:

    Test the prevention of creation of multiple pods due to
    recurring job's pod being rejected by Taint controller
    on nodes with taints

    Steps:

    1. Set taint toleration for Longhorn components
       `persistence=true:NoExecute`
    2. Taint `node-1` with `persistence=true:NoExecute`
    3. Create a volume, vol-1.
       Attach vol-1 to node-1
       Write some data to vol-1
    4. Create a recurring backup job which:
       Has retain count 10
       Runs every minute
    5. Wait for 3 minutes.
       Verify that the there is 1 backup created
       Verify that the total number of pod in longhorn-system namespace < 50
       Verify that the number of pods of the cronjob is <= 2

    6. Taint all nodes with `persistence=true:NoExecute`
    7. Write some data to vol-1
    8. Wait for 3 minutes.
       Verify that the there are 2 backups created in total
       Verify that the total number of pod in longhorn-system namespace < 50
       Verify that the number of pods of the cronjob is <= 2

    9. Remove `persistence=true:NoExecute` from all nodes and Longhorn setting
       Clean up backups, volumes
    """
    pass


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_groups(set_random_backupstore, client, batch_v1_api):  # NOQA
    """
    Scenario: test recurring job groups (S3/NFS)

    Given volume `test-job-1` created, attached, and healthy.
          volume `test-job-2` created, attached, and healthy.
    And create `snapshot` recurring job with `group-1, group-2` in groups.
            set cron job to run every 2 minutes.
            set retain to 1.
        create `backup`   recurring job with `group-1`          in groups.
            set cron job to run every 3 minutes.
            set retain to 1

    When set `group1` recurring job in volume `test-job-1` label.
         set `group2` recurring job in volume `test-job-2` label.
    And write some data to volume `test-job-1`.
        write some data to volume `test-job-2`.
    And wait for 2 minutes.
    And write some data to volume `test-job-1`.
        write some data to volume `test-job-2`.
    And wait for 1 minute.

    Then volume `test-job-1` should have 3 snapshots after scheduled time.
         volume `test-job-2` should have 2 snapshots after scheduled time.
     And volume `test-job-1` should have 1 backup after scheduled time.
         volume `test-job-2` should have 0 backup after scheduled time.
    """
    volume1_name = "test-job-1"
    volume2_name = "test-job-2"
    client.create_volume(name=volume1_name, size=SIZE)
    client.create_volume(name=volume2_name, size=SIZE)
    volume1 = wait_for_volume_detached(client, volume1_name)
    volume2 = wait_for_volume_detached(client, volume2_name)

    self_id = get_self_host_id()
    volume1.attach(hostId=self_id)
    volume2.attach(hostId=self_id)
    volume1 = wait_for_volume_healthy(client, volume1_name)
    volume2 = wait_for_volume_healthy(client, volume2_name)

    group1 = "group-1"
    group2 = "group-2"
    recurring_jobs = {
        SNAPSHOT: {
            TASK: SNAPSHOT,
            GROUPS: [group1, group2],
            CRON: "*/2 * * * *",
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        BACKUP: {
            TASK: BACKUP,
            GROUPS: [group1],
            CRON: "*/3 * * * *",
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume1.recurringJobAdd(name=group1, isGroup=True)
    volume2.recurringJobAdd(name=group2, isGroup=True)

    wait_for_cron_job_count(batch_v1_api, 2)

    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60 * 2 - WRITE_DATA_INTERVAL)
    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60)
    wait_for_snapshot_count(volume1, 3)  # volume-head,snapshot,backup-snapshot
    wait_for_snapshot_count(volume2, 2)  # volume-head,snapshot

    wait_for_backup_count(client.by_id_backupVolume(volume1_name), 1)
    backup_created = True
    try:
        wait_for_backup_count(client.by_id_backupVolume(volume2_name), 1,
                              retry_counts=60)
    except AssertionError:
        backup_created = False
    assert not backup_created


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_default(client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test recurring job set with default in groups

    Given 1 volume created, attached, and healthy.

    # Setting recurring job in volume label should not remove the defaults.
    When set `snapshot` recurring job in volume label.
    Then should contain `default`  job-group in volume labels.
         should contain `snapshot` job       in volume labels.

    # Should be able to remove the default label.
    When delete recurring job-group `default` in volume label.
    Then volume should have     `snapshot`  job   in job label.
         volume should not have `default`   group in job label.

    # Remove all volume recurring job labels should bring in default
    When delete all recurring jobs in volume label.
    Then volume should not have `snapshot`  job   in job label.
         volume should     have `default`   group in job label.
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    # Setting recurring job in volume label should not remove the defaults.
    volume.recurringJobAdd(name=SNAPSHOT, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[SNAPSHOT], groups=[DEFAULT])

    # Should be able to remove the default label.
    volume.recurringJobDelete(name=DEFAULT, isGroup=True)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[SNAPSHOT], groups=[])

    # Remove all volume recurring job labels should bring in default
    volume.recurringJobDelete(name=SNAPSHOT, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[DEFAULT])


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_delete(client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test delete recurring job

    Given 1 volume created, attached, and healthy.

    When create `snapshot1` recurring job with `default, group-1` in groups.
         create `snapshot2` recurring job with `default`          in groups..
         create `snapshot3` recurring job with ``                 in groups.
         create `backup1`   recurring job with `default, group-1` in groups.
         create `backup2`   recurring job with `default`          in groups.
         create `backup3`   recurring job with ``                 in groups.
    Then default `snapshot1` cron job should exist.
         default `snapshot2` cron job should exist.
                 `snapshot3` cron job should exist.
         default `backup1`   cron job should exist.
         default `backup2`   cron job should exist.
                 `backup3`   cron job should exist.

    # Delete `snapshot2` recurring job should delete the cron job
    When delete `snapshot-2` recurring job.
    Then default `snapshot1` cron job should     exist.
         default `snapshot2` cron job should not exist.
                 `snapshot3` cron job should     exist.
         default `backup1`   cron job should     exist.
         default `backup2`   cron job should     exist.
                 `backup3`   cron job should     exist.

    # Delete multiple recurring jobs should reflect on the cron jobs.
    When delete `backup-1` recurring job.
         delete `backup-2` recurring job.
         delete `backup-3` recurring job.
    Then default `snapshot1` cron job should     exist.
         default `snapshot2` cron job should not exist.
                 `snapshot3` cron job should     exist.
         default `backup1`   cron job should not exist.
         default `backup2`   cron job should not exist.
                 `backup3`   cron job should not exist.
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    snap1 = SNAPSHOT + "1"
    snap2 = SNAPSHOT + "2"
    snap3 = SNAPSHOT + "3"
    back1 = BACKUP + "1"
    back2 = BACKUP + "2"
    back3 = BACKUP + "3"
    group1 = "group-1"
    recurring_jobs = {
        snap1: {
            TASK: SNAPSHOT,
            GROUPS: [DEFAULT, group1],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        snap2: {
            TASK: SNAPSHOT,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        snap3: {
            TASK: SNAPSHOT,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        back1: {
            TASK: BACKUP,
            GROUPS: [DEFAULT, group1],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        back2: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        back3: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 6)

    # snapshot
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap1)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap3)
    # backup
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back1)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back3)

    # Delete `snapshot2` recurring job should delete the cron job
    snap2_recurring_job = client.by_id_recurring_job(snap2)
    client.delete(snap2_recurring_job)
    wait_for_cron_job_count(batch_v1_api, 5)
    # snapshot
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap1)
    wait_for_cron_job_delete(batch_v1_api, JOB_LABEL+"="+snap2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap3)
    # backup
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back1)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back3)

    # Delete multiple recurring jobs should reflect on the cron jobs.
    back1_recurring_job = client.by_id_recurring_job(back1)
    back2_recurring_job = client.by_id_recurring_job(back2)
    back3_recurring_job = client.by_id_recurring_job(back3)
    client.delete(back1_recurring_job)
    client.delete(back2_recurring_job)
    client.delete(back3_recurring_job)
    wait_for_cron_job_count(batch_v1_api, 2)
    # snapshot
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap1)
    wait_for_cron_job_delete(batch_v1_api, JOB_LABEL+"="+snap2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+snap3)
    # backup
    wait_for_cron_job_delete(batch_v1_api, JOB_LABEL+"="+back1)
    wait_for_cron_job_delete(batch_v1_api, JOB_LABEL+"="+back2)
    wait_for_cron_job_delete(batch_v1_api, JOB_LABEL+"="+back3)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_delete_should_remove_volume_label(client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test delete recurring job should remove volume labels

    Given 1 volume created.
    And  create `snapshot1` recurring job.
         create `backup1`   recurring job.
    And  `snapshot1` job applied to the volume.
         `backup1`   job applied to the volume.
    And  `snapshot1` job exist in volume recurring job label.
         `backup1`   job exist in volume recurring job label.

    When delete `snapshot1` recurring job.
    Then `snapshot1` job not exist in volume recurring job label.
         `backup1`   job     exist in volume recurring job label.

    When delete `backup1` recurring job.
    Then `snapshot1` job not exist in volume recurring job label.
         `backup1`   job not exist in volume recurring job label.

    Given create `snapshot1` recurring job with `group-1` in groups.
    And   create `snapshot2` recurring job with `group-1` in groups.
    And   create `backup1`   recurring job with `group-1` in groups.
    And   create `backup2`   recurring job with `default` in groups.
    // The default job-group automatically applies to the volumes
    // with no recurring job. We want to keep the test focused on the
    // behavior so removing the default job-group assignment first.
    And   remove volume recurring job label `default` job-group.
    And  `group-1` job-group applied to the volume.
    And  `group-1` job-group     exist in volume recurring job label.
         `default` job-group not exist in volume recurring job label.

    When delete `snapshot1` recurring job.
    Then `group-1` job-group exist in volume recurring job label.

    When delete `snapshot2` recurring job.
    Then `group-1` job-group exist in volume recurring job label.

    When delete `back1` recurring job.
    Then `group-1` job-group not exist in volume recurring job label.
    And  `default` job-group     exist in volume recurring job label.

    When delete `back2` recurring job.
    Then should not remove `default` job-group in volume.
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)

    snap1 = SNAPSHOT + "1"
    snap2 = SNAPSHOT + "2"
    back1 = BACKUP + "1"
    back2 = BACKUP + "2"
    group1 = "group-1"
    snap_job = {
        TASK: SNAPSHOT,
        GROUPS: [group1],
        CRON: SCHEDULE_1MIN,
        RETAIN: 1,
        CONCURRENCY: 2,
        LABELS: {},
    }
    back_job = {
        TASK: BACKUP,
        GROUPS: [group1],
        CRON: SCHEDULE_1MIN,
        RETAIN: 1,
        CONCURRENCY: 2,
        LABELS: {},
    }
    recurring_jobs = {
        snap1: snap_job,
        back1: back_job,
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    # Delete recurring job should remove volume label
    volume.recurringJobAdd(name=snap1, isGroup=False)
    volume.recurringJobAdd(name=back1, isGroup=False)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[snap1, back1], groups=[DEFAULT])

    snap1_recurring_job = client.by_id_recurring_job(snap1)
    back1_recurring_job = client.by_id_recurring_job(back1)
    client.delete(snap1_recurring_job)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[back1], groups=[DEFAULT])
    client.delete(back1_recurring_job)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[DEFAULT])

    # Delete recurring job-group in-use by other recurring-job
    # should not remove the volume label
    recurring_jobs = {
        snap1: snap_job,
        snap2: snap_job,
        back1: back_job,
        back2: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume.recurringJobAdd(name=group1, isGroup=True)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[group1, DEFAULT])
    volume.recurringJobDelete(name=DEFAULT, isGroup=True)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[group1])

    snap1_recurring_job = client.by_id_recurring_job(snap1)
    client.delete(snap1_recurring_job)
    time.sleep(5)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[group1])

    snap2_recurring_job = client.by_id_recurring_job(snap2)
    client.delete(snap2_recurring_job)
    time.sleep(5)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[group1])

    # Delete last recurring job of the group would clean up that job-group
    # for all volumes.
    back1_recurring_job = client.by_id_recurring_job(back1)
    client.delete(back1_recurring_job)
    time.sleep(5)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[DEFAULT])

    # Delete recurring job in default job-group should not effect on the
    # default job-group auto-assignment
    back2_recurring_job = client.by_id_recurring_job(back2)
    client.delete(back2_recurring_job)
    time.sleep(5)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[], groups=[DEFAULT])


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_volume_label_when_job_and_group_use_same_name(client, volume_name):  # NOQA
    """
    Scenario: test volume label recurring job when recurring job and
              job-group uses the same name.

    Given volume-1 created.
          volume-2 created.
          volume-3 created.
    And  create `snapshot1` recurring job with `snapshot-1` in groups.
         create `snapshot2` recurring job with `snapshot-1` in groups.
    And  `snapshot1` job-group applied to volume-1.
         `snapshot1` job       applied to volume-2.
         `snapshot2` job       applied to volume-3.
    And  `snapshot1` job-group exist in volume-1 recurring job label.
         `snapshot1` job       exist in volume-2 recurring job label.
         `snapshot2` job       exist in volume-3 recurring job label.

    When delete `snapshot1` recurring job.
    Then `snapshot1` job-group     exist in volume-1 recurring job label.
         `snapshot1` job       not exist in volume-2 recurring job label.
         `snapshot2` job           exist in volume-3 recurring job label.

    When delete `snapshot2` recurring job.
    Then `snapshot1` job-group not exist in volume-1 recurring job label.
         `snapshot2` job       not exist in volume-3 recurring job label.
    """
    volume1_name = volume_name + "-1"
    volume2_name = volume_name + "-2"
    volume3_name = volume_name + "-3"
    client.create_volume(name=volume1_name, size=SIZE)
    client.create_volume(name=volume2_name, size=SIZE)
    client.create_volume(name=volume3_name, size=SIZE)
    volume1 = wait_for_volume_detached(client, volume1_name)
    volume2 = wait_for_volume_detached(client, volume2_name)
    volume3 = wait_for_volume_detached(client, volume3_name)

    snap1 = SNAPSHOT + "1"
    snap2 = SNAPSHOT + "2"
    snapshot = {
        TASK: SNAPSHOT,
        GROUPS: [snap1],
        CRON: SCHEDULE_1MIN,
        RETAIN: 1,
        CONCURRENCY: 2,
        LABELS: {},
    }
    recurring_jobs = {
        snap1: snapshot,
        snap2: snapshot,
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    # Delete recurring job should correctly remove volume label
    volume1.recurringJobAdd(name=snap1, isGroup=True)
    volume2.recurringJobAdd(name=snap1, isGroup=False)
    volume3.recurringJobAdd(name=snap2, isGroup=False)
    wait_for_volume_recurring_job_update(volume1,
                                         jobs=[], groups=[snap1, DEFAULT])
    wait_for_volume_recurring_job_update(volume2,
                                         jobs=[snap1], groups=[DEFAULT])
    wait_for_volume_recurring_job_update(volume3,
                                         jobs=[snap2], groups=[DEFAULT])

    snap1_recurring_job = client.by_id_recurring_job(snap1)
    snap2_recurring_job = client.by_id_recurring_job(snap2)
    client.delete(snap1_recurring_job)
    wait_for_volume_recurring_job_update(volume2,
                                         jobs=[], groups=[DEFAULT])
    wait_for_volume_recurring_job_update(volume1,
                                         jobs=[], groups=[snap1, DEFAULT])
    wait_for_volume_recurring_job_update(volume3,
                                         jobs=[snap2], groups=[DEFAULT])
    client.delete(snap2_recurring_job)
    wait_for_volume_recurring_job_update(volume1,
                                         jobs=[], groups=[DEFAULT])
    wait_for_volume_recurring_job_update(volume3,
                                         jobs=[], groups=[DEFAULT])


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_multiple_volumes(set_random_backupstore, client, batch_v1_api):  # NOQA
    """
    Scenario: test recurring job with multiple volumes

    Given volume `test-job-1` created, attached and healthy.
    And create `backup1`   recurring job with `default` in groups.
        create `backup2`   recurring job with ``        in groups.
    And `default` group exist in `test-job-1` volume recurring job label.
    And `backup1` cron job exist.
        `backup2` cron job exist.
    And write data to  `test-job-1` volume.
    And 2 snapshot exist in `test-job-1` volume.
    And 1 backup   exist in `test-job-1` volume.

    When create and attach volume `test-job-2`.
         wait for volume `test-job-2` to be healthy.
    And `default` group exist in `test-job-2` volume recurring job label.
    And write data to  `test-job-1` volume.
    Then 2 snapshot exist in `test-job-2` volume.
         1 backup   exist in `test-job-2` volume.

    When add `backup2` in `test-job-2` volume label.
    And `default` group exist in `test-job-1` volume recurring job label.
        `default` group exist in `test-job-2` volume recurring job label.
        `backup2` group exist in `test-job-2` volume recurring job label.
    And write data to `test-job-1`.
        write data to `test-job-2`.
    Then wait for schedule time.
    And 2 backup exist in `test-job-2` volume.
        1 backup exist in `test-job-1` volume.
    """
    volume1_name = "test-job-1"
    client.create_volume(name=volume1_name, size=SIZE)
    volume1 = wait_for_volume_detached(client, volume1_name)
    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1_name)

    back1 = BACKUP + "1"
    back2 = BACKUP + "2"
    recurring_jobs = {
        back1: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
        back2: {
            TASK: BACKUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_volume_recurring_job_update(volume1, jobs=[], groups=[DEFAULT])
    wait_for_cron_job_count(batch_v1_api, 2)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back1)
    wait_for_cron_job_create(batch_v1_api, JOB_LABEL+"="+back2)

    write_volume_random_data(volume1)
    wait_for_snapshot_count(volume1, 2)
    wait_for_backup_count(client.by_id_backupVolume(volume1_name), 1)

    volume2_name = "test-job-2"
    client.create_volume(name=volume2_name, size=SIZE)
    volume2 = wait_for_volume_detached(client, volume2_name)
    volume2.attach(hostId=get_self_host_id())
    volume2 = wait_for_volume_healthy(client, volume2_name)
    wait_for_volume_recurring_job_update(volume2, jobs=[], groups=[DEFAULT])

    write_volume_random_data(volume2)
    wait_for_snapshot_count(volume2, 2)
    wait_for_backup_count(client.by_id_backupVolume(volume2_name), 1)

    volume2.recurringJobAdd(name=back2, isGroup=False)
    wait_for_volume_recurring_job_update(volume1,
                                         jobs=[], groups=[DEFAULT])
    wait_for_volume_recurring_job_update(volume2,
                                         jobs=[back2], groups=[DEFAULT])

    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(70 - WRITE_DATA_INTERVAL)
    wait_for_backup_count(client.by_id_backupVolume(volume2_name), 2)
    wait_for_backup_count(client.by_id_backupVolume(volume1_name), 1)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_snapshot(client, batch_v1_api):  # NOQA
    """
    Scenario: test recurring job snapshot

    Given volume `test-job-1` created, attached, and healthy.
          volume `test-job-2` created, attached, and healthy.

    When create a recurring job with `default` in groups.
    Then should have 1 cron job.
    And volume `test-job-1` should have volume-head 1 snapshot.
        volume `test-job-2` should have volume-head 1 snapshot.

    When write some data to volume `test-job-1`.
         write some data to volume `test-job-2`.
    And wait for cron job scheduled time.
    Then volume `test-job-1` should have 2 snapshots after scheduled time.
         volume `test-job-2` should have 2 snapshots after scheduled time.

    When write some data to volume `test-job-1`.
         write some data to volume `test-job-2`.
    And wait for cron job scheduled time.
    Then volume `test-job-1` should have 3 snapshots after scheduled time.
         volume `test-job-2` should have 3 snapshots after scheduled time.
    """
    volume1_name = "test-job-1"
    volume2_name = "test-job-2"
    client.create_volume(name=volume1_name, size=SIZE)
    client.create_volume(name=volume2_name, size=SIZE)
    volume1 = wait_for_volume_detached(client, volume1_name)
    volume2 = wait_for_volume_detached(client, volume2_name)

    self_host = get_self_host_id()

    volume1.attach(hostId=self_host)
    volume2.attach(hostId=self_host)
    volume1 = wait_for_volume_healthy(client, volume1_name)
    volume2 = wait_for_volume_healthy(client, volume2_name)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: SNAPSHOT,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    # volume-head
    wait_for_snapshot_count(volume1, 1)
    wait_for_snapshot_count(volume2, 1)

    # 1st job
    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60)
    wait_for_snapshot_count(volume1, 2)
    wait_for_snapshot_count(volume2, 2)

    # 2nd job
    # wait_until_begin_of_a_minute()
    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60)
    wait_for_snapshot_count(volume1, 3)
    wait_for_snapshot_count(volume2, 3)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_snapshot_delete(set_random_backupstore, client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test recurring job snapshot-delete

    Given volume created, attached, and healthy.
    And 3 snapshots were created.
    And volume has 4 snapshots.
        - 3 user-created
        - 1 volume-head

    When create a recurring job with:
         - task: snapshot-delete
         - retain: 1
    And assign the recurring job to volume.
    And wait for the cron job scheduled time.

    Then volume should have 2 snapshots.
         - 1 snapshot retained
         - 1 volume-head

    When recurring job unassigned to volume.
    And create 5 snapshots.
    And volume has 7 snapshots.
        - 5 new snapshots
        - 1 old snapshot
        - 1 volume-head
    And update recurring job retain to 3.
    And assign the recurring job to volume.
    And wait for the cron job scheduled time.

    Then volume should have 4 snapshots
         - 3 snapshots retained
         - 1 volume-head
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)

    self_host = get_self_host_id()
    volume.attach(hostId=self_host)

    volume = wait_for_volume_healthy(client, volume_name)

    num_snapshots = 3
    for _ in range(num_snapshots):
        create_snapshot(client, volume_name)

    # - 3 new snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 4)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: SNAPSHOT_DELETE,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    volume = client.by_id_volume(volume_name)
    volume.recurringJobAdd(name=RECURRING_JOB_NAME, isGroup=False)

    time.sleep(60)

    # - 1 snapshot retained
    # - 1 volume-head
    try:
        wait_for_snapshot_count(volume, 2)
    except Exception:
        wait_for_snapshot_count(volume, 2, count_removed=True)

    volume.recurringJobDelete(name=RECURRING_JOB_NAME, isGroup=False)

    num_snapshots = 5

    for _ in range(num_snapshots):
        create_snapshot(client, volume_name)
    volume = client.by_id_volume(volume_name)

    # - 5 new snapshot
    # - 1 old snapshot
    # - 1 volume-head
    try:
        wait_for_snapshot_count(volume, 7)
    except Exception:
        wait_for_snapshot_count(volume, 7, count_removed=True)

    update_recurring_job(client, RECURRING_JOB_NAME,
                         groups=[], labels={}, retain=3)

    volume.recurringJobAdd(name=RECURRING_JOB_NAME, isGroup=False)
    time.sleep(60)

    # - 3 snapshot retained
    # - 1 volume-head
    try:
        wait_for_snapshot_count(volume, 4)
    except Exception:
        wait_for_snapshot_count(volume, 4, count_removed=True)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_snapshot_delete_retain_0(set_random_backupstore, client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test recurring job snapshot-delete with retain value 0

    Given volume created, attached, and healthy.
    And 1 snapshots were created.
    And volume has 2 snapshots.
        - 1 user-created
        - 1 volume-head

    When create a recurring job with:
         - task: snapshot-delete
         - retain: 0
    And assign the recurring job to volume.
    And wait for the cron job scheduled time.

    Then volume should have 1 snapshot.
         - 0 snapshot retained
         - 1 volume-head
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)

    self_host = get_self_host_id()
    volume.attach(hostId=self_host)

    volume = wait_for_volume_healthy(client, volume_name)

    num_snapshots = 1
    for _ in range(num_snapshots):
        create_snapshot(client, volume_name)

    # - 1 new snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 2)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: SNAPSHOT_DELETE,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 0,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    volume = client.by_id_volume(volume_name)
    volume.recurringJobAdd(name=RECURRING_JOB_NAME, isGroup=False)

    time.sleep(60)

    # - 0 snapshot retained
    # - 1 volume-head
    try:
        wait_for_snapshot_count(volume, 1)
    except Exception:
        wait_for_snapshot_count(volume, 1, count_removed=True)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_snapshot_cleanup(set_random_backupstore, client, batch_v1_api, volume_name):  # NOQA
    """
    Scenario: test recurring job snapshot-cleanup

    Given volume created, attached, and healthy.
    And 2 snapshot were created by system.
    And 1 snapshot were created by user.
    And volume has 4 snapshots.
        - 2 system-created
        - 1 user-created
        - 1 volume-head

    When create a recurring job with:
         - task: system-snapshot-delete
         - retain: 1
    Then recurring job retain mutated to 0.

    When assign the recurring job to volume.
    And wait for the cron job scheduled time.
    Then volume should have 2 snapshots.
         - 0 system-created
         - 1 user-created
         - 1 volume-head
    """
    client.create_volume(name=volume_name, size=SIZE)
    volume = wait_for_volume_detached(client, volume_name)

    self_host = get_self_host_id()
    volume.attach(hostId=self_host)

    volume = wait_for_volume_healthy(client, volume_name)

    expand_size = str(32 * Mi)
    volume.expand(size=expand_size)
    wait_for_volume_expansion(client, volume_name)
    # - 1 new system-created snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 2)

    expand_size = str(64 * Mi)
    volume.expand(size=expand_size)
    wait_for_volume_expansion(client, volume_name)
    # - 1 new system-created snapshot
    # - 1 system-created snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 3)

    create_snapshot(client, volume_name)

    # - 1 new system-created snapshot
    # - 1 system-created snapshot
    # - 1 user-created snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 4)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: SNAPSHOT_CLEANUP,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    volume = client.by_id_volume(volume_name)
    volume.recurringJobAdd(name=RECURRING_JOB_NAME, isGroup=False)

    time.sleep(60)

    # - 0 system-creatd snapshot
    # - 1 user-created snapshot
    # - 1 volume-head
    wait_for_snapshot_count(volume, 2)

    system_created_count = 0
    for snapshot in volume.snapshotList():
        if not snapshot.usercreated and snapshot.name != VOLUME_HEAD_NAME:
            system_created_count += 1
    assert system_created_count == 0


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_backup(set_random_backupstore, client, batch_v1_api):  # NOQA
    """
    Scenario: test recurring job backup (S3/NFS)

    Given volume `test-job-1` created, attached, and healthy.
          volume `test-job-2` created, attached, and healthy.

    When create a recurring job with `default` in groups.
    Then should have 1 cron job.

    When write some data to volume `test-job-1`.
         write some data to volume `test-job-2`.
    And wait for `backup1` cron job scheduled time.
    Then volume `test-job-1` should have 1 backups.
         volume `test-job-2` should have 1 backups.

    When write some data to volume `test-job-1`.
         write some data to volume `test-job-2`.
    And wait for `backup1` cron job scheduled time.
    Then volume `test-job-1` should have 2 backups.
         volume `test-job-2` should have 2 backups.
    """
    volume1_name = "test-job-1"
    volume2_name = "test-job-2"
    client.create_volume(name=volume1_name, size=SIZE)
    client.create_volume(name=volume2_name, size=SIZE)
    volume1 = wait_for_volume_detached(client, volume1_name)
    volume2 = wait_for_volume_detached(client, volume2_name)

    self_host = get_self_host_id()
    volume1.attach(hostId=self_host)
    volume2.attach(hostId=self_host)
    volume1 = wait_for_volume_healthy(client, volume1_name)
    volume2 = wait_for_volume_healthy(client, volume2_name)

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 2,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    # 1st job
    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60 - WRITE_DATA_INTERVAL)
    wait_for_backup_count(client.by_id_backupVolume(volume1_name), 1)
    wait_for_backup_count(client.by_id_backupVolume(volume2_name), 1)

    # 2nd job
    write_volume_random_data(volume1)
    write_volume_random_data(volume2)
    time.sleep(60 - WRITE_DATA_INTERVAL)
    wait_for_backup_count(client.by_id_backupVolume(volume1_name), 2)
    wait_for_backup_count(client.by_id_backupVolume(volume2_name), 2)


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_restored_from_backup_target(set_random_backupstore, client, batch_v1_api):  # NOQA
    """
    Scenario: test recurring job backup (S3/NFS)

    1. Create a volume and attach it to a node or a workload.
    2. Create some recurring jobs (some are in groups)
    3. Label the volume with created recurring jobs (some are in groups)
    4. Create a backup or wait for a recurring job starting
    5. Wait for backup creation completed.
    6. Check if recurring jobs/groups information is stored in
       the backup volume configuration on the backup target

    7. Create a volume from the backup just created.
    8. Check the volume if it has labels of recurring jobs and groups.

    9. Delete recurring jobs that are already stored in the backup volume
       on the backup.
    10. Create a volume from the backup just created.
    11. Check if recurring jobs have been created.
    12. Check if restoring volume has labels of recurring jobs and groups.
    """
    SCHEDULE_1WEEK = "0 0 * * 0"
    SCHEDULE_2MIN = "*/2 * * * *"
    snap1 = SNAPSHOT + "1"
    back1 = BACKUP + "1"
    back2 = BACKUP + "2"
    group1 = "group01"
    volume_name1 = "record-recurring-job"
    rvolume_name1 = "restore-record-recurring-job-01"
    rvolume_name2 = "restore-record-recurring-job-02"

    recurring_jobs = {
        back1: {
            TASK: BACKUP,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_2MIN,
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
        snap1: {
            TASK: SNAPSHOT,
            GROUPS: [],
            CRON: SCHEDULE_1MIN,
            RETAIN: 2,
            CONCURRENCY: 1,
            LABELS: {},
        },
        back2: {
            TASK: BACKUP,
            GROUPS: [group1],
            CRON: SCHEDULE_1WEEK,
            RETAIN: 3,
            CONCURRENCY: 3,
            LABELS: {},
        },
    }

    common.update_setting(client,
                          SETTING_RESTORE_RECURRING_JOBS, "true")

    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)

    volume = client.create_volume(name=volume_name1, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name1)
    volume = volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name1)
    volume.recurringJobAdd(name=snap1, isGroup=False)
    volume.recurringJobAdd(name=back1, isGroup=False)
    volume.recurringJobAdd(name=group1, isGroup=True)
    wait_for_volume_recurring_job_update(volume,
                                         jobs=[snap1, back1],
                                         groups=[DEFAULT, group1])

    write_volume_random_data(volume)
    time.sleep(120)

    # 2 from job_snap, 1 from job_backup, 1 volume-head
    wait_for_snapshot_count(volume, 4)

    complete_backup_1_count = 0
    restore_snapshot_name = ""
    volume = client.by_id_volume(volume_name1)
    wait_for_backup_completion(client, volume_name1)
    for b in volume.backupStatus:
        if back1+"-" in b.snapshot:
            complete_backup_1_count += 1
            restore_snapshot_name = b.snapshot

    assert complete_backup_1_count == 1

    volume.detach()

    # create a volume from the backup with recurring jobs exist
    _, backup = find_backup(client, volume_name1, restore_snapshot_name)
    client.create_volume(name=rvolume_name1,
                         size=SIZE,
                         fromBackup=backup.url)
    rvolume1 = wait_for_volume_detached(client, rvolume_name1)
    wait_for_volume_recurring_job_update(rvolume1,
                                         jobs=[snap1, back1],
                                         groups=[DEFAULT, group1])

    # create a volume from the backup with recurring jobs do not exist
    cleanup_all_recurring_jobs(client)
    client.create_volume(name=rvolume_name2,
                         size=SIZE,
                         fromBackup=backup.url)
    rvolume2 = wait_for_volume_detached(client, rvolume_name2)
    wait_for_volume_recurring_job_update(rvolume2,
                                         jobs=[snap1, back1],
                                         groups=[DEFAULT, group1])


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_filesystem_trim(client, core_api, batch_v1_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Scenario: test recurring job filesystem-trim

    Given a workload (volume, pv, pvc, pod).
    And create 50mb file in volume.
    And actual size of the volume should increase.
    And delete the 50mb file in volume.
    And actual size of the volume should not decrease.

    When create a recurring job with:
         - task: filesystem-trim
         - retain: 1
    Then recurring job retain mutated to 0.

    When assign the recurring job to volume.
    And wait for the cron job scheduled time.
    Then volume actual size should decrease 50mb.
    """
    pod_name, _, _, _ = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc, pod_make,
                                    volume_name, data_size_in_mb=10)

    volume = client.by_id_volume(volume_name)

    # Do the first trim to ensure that the final trim size only includes the
    # created file.
    volume.trimFilesystem(volume=volume_name)
    initial_size = wait_for_actual_size_change_mb(client, volume_name, 0)

    file_delete = "/data/trim.test"
    test_size = 50
    write_pod_volume_random_data(core_api, pod_name,
                                 file_delete, test_size)

    size_after_file_created = \
        wait_for_actual_size_change_mb(client, volume_name, initial_size)
    assert size_after_file_created - initial_size == test_size

    command = f'rm {file_delete}'
    exec_command_in_pod(core_api, command, pod_name, 'default')

    try:
        wait_for_actual_size_change_mb(
            client, volume_name, size_after_file_created,
            retry_counts=10,
            wait_stablize=True
        )
        assert False, \
            f'expecting no change in actual size: {size_after_file_created}'
    except Exception:
        pass

    recurring_jobs = {
        RECURRING_JOB_NAME: {
            TASK: FILESYSTEM_TRIM,
            GROUPS: [DEFAULT],
            CRON: SCHEDULE_1MIN,
            RETAIN: 1,
            CONCURRENCY: 1,
            LABELS: {},
        },
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    wait_for_cron_job_count(batch_v1_api, 1)

    size_after_file_deleted = \
        wait_for_actual_size_change_mb(client, volume_name,
                                       size_after_file_created)
    size_trimmed = size_after_file_created - size_after_file_deleted
    assert size_trimmed == test_size


def wait_for_actual_size_change_mb(client, vol_name, old_size,  # NOQA
                                   retry_counts=60, wait_stablize=True):
    size_change = 0
    for _ in range(retry_counts):
        time.sleep(5)

        volume = client.by_id_volume(vol_name)
        new_size = int(int(volume.controllers[0].actualSize) / Mi)

        if wait_stablize and new_size != size_change:
            size_change = new_size
            continue

        if new_size != old_size:
            return new_size
    assert False, f'expecting actual size change: {old_size} -> {new_size}'
