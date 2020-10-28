import pytest
import time
import json

from datetime import datetime

import common
from common import client, clients, core_api, random_labels, volume_name  # NOQA
from common import storage_class, statefulset  # NOQA
from common import cleanup_volume, wait_for_volume_delete
from common import create_pv_for_volume, create_storage_class, \
    create_and_wait_statefulset, delete_and_wait_pv
from common import update_statefulset_manifests, get_self_host_id, \
    get_statefulset_pod_info, wait_volume_kubernetes_status
from common import set_random_backupstore
from common import write_volume_random_data
from common import write_pod_volume_random_data
from common import BASE_IMAGE_LABEL, KUBERNETES_STATUS_LABEL, SIZE


RECURRING_JOB_LABEL = "RecurringJob"
RECURRING_JOB_NAME = "backup"
MAX_BACKUP_STATUS_SIZE = 5


def create_jobs1():
    # snapshot every one minute
    job_snap = {"name": "snap", "cron": "* * * * *",
                "task": "snapshot", "retain": 2}
    # backup every two minutes
    job_backup = {"name": "backup", "cron": "*/2 * * * *",
                  "task": "backup", "retain": 1}
    return [job_snap, job_backup]


def check_jobs1_result(volume):
    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot.removed is False:
            count += 1
    # 2 snapshots, 1 backup, 1 volume-head
    assert count == 4


def wait_until_begin_of_an_even_minute():
    while True:
        current_time = datetime.utcnow()
        if current_time.second == 0 and current_time.minute % 2 == 0:
            break
        time.sleep(1)

@pytest.mark.recurring_job  # NOQA
def test_recurring_job(client, volume_name):  # NOQA
    """
    Test recurring job

    1. Setup a random backupstore
    2. Create a volume.
    3. Create two jobs
        1 job 1: snapshot every one minute, retain 2
        1 job 2: backup every two minutes, retain 1
    4. Attach the volume.
       Wait until the 10th second since the beginning of an even minute
    5. Write some data. Sleep 2.5 minutes.
       Write some data. Sleep 2.5 minutes
    6. Verify we have 4 snapshots total
        1. 2 snapshots, 1 backup, 1 volume-head
    7. Update jobs to replace the backup job
        1. New backup job run every one minute, retain 2
    8. Write some data. Sleep 2.5 minutes.
       Write some data. Sleep 2.5 minutes
    9. We should have 6 snapshots
        1. 2 from job_snap, 1 from job_backup, 2 from job_backup2, 1
        volume-head
    10. Make sure there are exactly 4 completed backups.
        1. old backup job completed 2 backups
        2. new backup job completed 2 backups
    11. Make sure we have no backup in progress
    """

    '''
    The timeline looks like this:
    0   1   2   3   4   5   6   7   8   9   10     (minute)
    |W  |   | W |   |   |W  |   | W |   |   |      (write data)
    |   S   |   S   |   |   S   |   S   |   |      (job_snap)
    |   |   B   |   B   |   |   |   |   |   |      (job_backup1)
    |   |   |   |   |   |   B   |   B   |   |      (job_backup2)
    '''

    host_id = get_self_host_id()

    set_random_backupstore(client)

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

    jobs = create_jobs1()
    volume.recurringUpdate(jobs=jobs)

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # wait until the beginning of an even minute
    wait_until_begin_of_an_even_minute()
    # wait until the 10th second of an even minute
    # make sure that snapshot job happens before the backup job
    time.sleep(10)

    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes
    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes

    check_jobs1_result(volume)

    job_backup2 = {"name": "backup2", "cron": "* * * * *",
                   "task": "backup", "retain": 2}
    volume.recurringUpdate(jobs=[jobs[0], job_backup2])

    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes
    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes

    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot.removed is False:
            count += 1
    # 2 from job_snap, 1 from job_backup, 2 from job_backup2, 1 volume-head
    assert count == 6

    complete_backup_number = 0
    in_progress_backup_number = 0
    volume = client.by_id_volume(volume_name)
    for b in volume.backupStatus:
        assert b.error == ""
        if b.state == "complete":
            complete_backup_number += 1
        elif b.state == "in_progress":
            in_progress_backup_number += 1

    # 2 completed backups from job_backup
    # 2 completed backups from job_backup2
    assert complete_backup_number == 4

    assert in_progress_backup_number == 0

    volume = volume.detach()

    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_volume_creation(client, volume_name):  # NOQA
    """
    Test create volume with recurring jobs

    1. Create volume with recurring jobs though Longhorn API
    2. Verify the recurring jobs run correctly
    """
    host_id = get_self_host_id()

    set_random_backupstore(client)

    # error when creating volume with duplicate jobs
    with pytest.raises(Exception) as e:
        client.create_volume(name=volume_name, size=SIZE,
                             numberOfReplicas=2,
                             recurringJobs=create_jobs1() + create_jobs1())
    assert "duplicate job" in str(e.value)

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2, recurringJobs=create_jobs1())
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # wait until the beginning of an even minute
    wait_until_begin_of_an_even_minute()
    # wait until the 10th second of an even minute
    # to avoid writing data at the same time backup is taking
    time.sleep(10)

    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes
    write_volume_random_data(volume)
    time.sleep(150)  # 2.5 minutes

    check_jobs1_result(volume)

    volume = volume.detach()
    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_storageclass(client, core_api, storage_class, statefulset):  # NOQA
    """
    Test create volume with StorageClass contains recurring jobs

    1. Create a StorageClass with recurring jobs
    2. Create a StatefulSet with PVC template and StorageClass
    3. Verify the recurring jobs run correctly.
    """
    set_random_backupstore(client)
    statefulset_name = 'recurring-job-in-storageclass-test'
    update_statefulset_manifests(statefulset, storage_class, statefulset_name)
    storage_class["parameters"]["recurringJobs"] = json.dumps(create_jobs1())

    create_storage_class(storage_class)

    # wait until the beginning of an even minute
    wait_until_begin_of_an_even_minute()

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
        check_jobs1_result(volume)


@pytest.mark.recurring_job
def test_recurring_job_labels(client, random_labels, volume_name):  # NOQA
    """
    Test a RecurringJob with labels

    1. Set a random backupstore
    2. Create a backup recurring job with labels
    3. Wait for job to create a backup
    4. Add a label to the job
    5. Verify the recurring jobs run correctly.
    6. Verify the labels on the backup are correct.
    """
    recurring_job_labels_test(client, random_labels, volume_name)


def recurring_job_labels_test(client, labels, volume_name, size=SIZE, base_image=""):  # NOQA
    set_random_backupstore(client)
    host_id = get_self_host_id()
    client.create_volume(name=volume_name, size=size,
                         numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

    # Simple Backup Job that runs every 1 minute, retains 1.
    jobs = [
        {
            "name": RECURRING_JOB_NAME,
            "cron": "*/1 * * * *",
            "task": "backup",
            "retain": 1,
            "labels": labels
        }
    ]
    volume.recurringUpdate(jobs=jobs)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
    write_volume_random_data(volume)

    # 1 minutes 15s
    time.sleep(75)
    labels["we-added-this-label"] = "definitely"
    jobs[0]["labels"] = labels
    volume = volume.recurringUpdate(jobs=jobs)
    volume = common.wait_for_volume_healthy(client, volume_name)
    write_volume_random_data(volume)

    # 2 minutes 15s
    time.sleep(135)
    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot.removed is False:
            count += 1
    # 1 from Backup, 1 from Volume Head.
    assert count == 2

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    backups = bv.backupList().data
    assert len(backups) == 1

    b = bv.backupGet(name=backups[0].name)
    for key, val in iter(labels.items()):
        assert b.labels.get(key) == val
    assert b.labels.get(RECURRING_JOB_LABEL) == RECURRING_JOB_NAME
    if base_image:
        assert b.labels.get(BASE_IMAGE_LABEL) == base_image
        # One extra Label from the BaseImage being set.
        assert len(b.labels) == len(labels) + 2
    else:
        # At least one extra Label from RecurringJob.
        assert len(b.labels) == len(labels) + 1

    cleanup_volume(client, volume)


@pytest.mark.csi
@pytest.mark.recurring_job
def test_recurring_job_kubernetes_status(client, core_api, volume_name):  # NOQA
    """
    Test RecurringJob properly backs up the KubernetesStatus

    1. Setup a random backupstore.
    2. Create a volume.
    3. Create a PV from the volume, and verify the PV status.
    4. Create a backup recurring job to run every 2 minutes.
    5. Verify the recurring job runs correctly.
    6. Verify the backup contains the Kubernetes Status labels
    """
    set_random_backupstore(client)
    host_id = get_self_host_id()
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

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

    # Simple Backup Job that runs every 2 minutes, retains 1.
    jobs = [
        {
            "name": RECURRING_JOB_NAME,
            "cron": "*/2 * * * *",
            "task": "backup",
            "retain": 1
        }
    ]
    volume.recurringUpdate(jobs=jobs)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    write_volume_random_data(volume)
    # 5 minutes
    time.sleep(300)
    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot.removed is False:
            count += 1
    # 1 from Backup, 1 from Volume Head.
    assert count == 2

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    backups = bv.backupList().data
    assert len(backups) == 1

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
    # Two Labels: KubernetesStatus and RecurringJob.
    assert len(b.labels) == 2

    cleanup_volume(client, volume)
    delete_and_wait_pv(core_api, pv_name)


def test_recurring_jobs_maximum_retain(client, core_api, volume_name): # NOQA
    """
    Test recurring jobs' maximum retain

    1. Create two jobs, with retain 30 and 21.
    2. Try to apply the jobs to a volume. It should fail.
    3. Reduce retain to 30 and 20.
    4. Now the jobs can be applied the volume.
    """
    volume = client.create_volume(name=volume_name)

    volume = common.wait_for_volume_detached(client, volume_name)

    jobs = create_jobs1()

    # set max total number of retain to exceed 50
    jobs[0]['retain'] = 30
    jobs[1]['retain'] = 21

    host_id = get_self_host_id()

    volume = volume.attach(hostId=host_id)

    volume = common.wait_for_volume_healthy(client, volume_name)

    with pytest.raises(Exception) as e:
        volume.recurringUpdate(jobs=jobs)

    assert "Job Can\\'t retain more than 50 snapshots" in str(e.value)

    jobs[1]['retain'] = 20

    volume = volume.recurringUpdate(jobs=jobs)

    assert len(volume.recurringJobs) == 2
    assert volume.recurringJobs[0]['retain'] == 30
    assert volume.recurringJobs[1]['retain'] == 20


@pytest.mark.skip(reason="TODO")
def test_recurring_jobs_for_detached_volume():  # NOQA
    """
    Test recurring jobs for detached volume

    Context:
    In the current Longhorn implementation, users cannot do recurring
    backup when volumes are detached.
    This feature gives the users an option to do recurring backup even when
    volumes are detached.
    longhorn/longhorn#1509

    Steps:
    1.  Change the setting allow-recurring-job-while-volume-detached to true
    2.  Create a volume-1, attach to node-1, write 50MB data to the volume-1.
    3.  Detach the volume
    4.  Set the recurring backup for the volume on every minute
    5.  In a 4-mintute retry loop, verify that there is exactly 1 new backup
    6.  Delete the recurring backup

    7.  Create a PVC from the volume
    8.  Create a deployment of 1 pod using the PVC
    9.  Write 400MB data to the volume from the pod.
    10. Scale down the deployment. Wait until the volume is detached.
    11. Set the recurring backup for every 2 minutes.
    12. Wait util the recurring backup starts, scale up the deployment to 1
        pod.
    13. Verify that during the recurring backup, the volume's frontend is
        disabled, and pod cannot start.
    14. Wait for the recurring backup finishes.
        Delete the recurring backup
    15. In a 6-mintute retry loop, verify that the pod can eventually start.

    16. Change the setting allow-recurring-job-while-volume-detached to false
    17. cleanup
    """
    pass


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
