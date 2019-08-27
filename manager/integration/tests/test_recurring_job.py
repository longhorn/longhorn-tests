import pytest
import time
import json

import common
from common import client, clients, core_api, random_labels, volume_name  # NOQA
from common import storage_class, statefulset  # NOQA
from common import cleanup_volume, wait_for_volume_delete
from common import create_pv_for_volume, create_storage_class, \
    create_and_wait_statefulset, delete_and_wait_pv
from common import update_statefulset_manifests, get_self_host_id, \
    get_statefulset_pod_info, wait_volume_kubernetes_status
from common import BASE_IMAGE_LABEL, KUBERNETES_STATUS_LABEL, SIZE


RECURRING_JOB_LABEL = "RecurringJob"
RECURRING_JOB_NAME = "backup"


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
        if snapshot["removed"] is False:
            count += 1
    # 2 snapshots, 1 backup, 1 volume-head
    assert count == 4


@pytest.mark.recurring_job  # NOQA
def test_recurring_job(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():  # NOQA
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

    jobs = create_jobs1()
    volume.recurringUpdate(jobs=jobs)

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # 5 minutes
    time.sleep(300)
    check_jobs1_result(volume)

    job_backup2 = {"name": "backup2", "cron": "* * * * *",
                   "task": "backup", "retain": 2}
    volume.recurringUpdate(jobs=[jobs[0], job_backup2])

    # 5 minutes
    time.sleep(300)

    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    # 2 from job_snap, 1 from job_backup, 2 from job_backup2, 1 volume-head
    assert count == 6

    volume = volume.detach()

    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_volume_creation(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():  # NOQA
        break

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

    # 5 minutes
    time.sleep(300)
    check_jobs1_result(volume)

    volume = volume.detach()
    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.recurring_job  # NOQA
def test_recurring_job_in_storageclass(client, core_api, storage_class, statefulset):  # NOQA
    statefulset_name = 'recurring-job-in-storageclass-test'
    update_statefulset_manifests(statefulset, storage_class, statefulset_name)
    storage_class['parameters']['recurringJobs'] = json.dumps(create_jobs1())

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volume_info = [p['pv_name'] for p in pod_info]

    # 5 minutes
    time.sleep(300)
    for volume_name in volume_info:  # NOQA
        volume = client.by_id_volume(volume_name)
        check_jobs1_result(volume)


@pytest.mark.recurring_job
def test_recurring_job_labels(client, random_labels, volume_name):  # NOQA
    """
    Test that a RecurringJob properly applies the correct Labels to the
    produced Backups.
    """
    recurring_job_labels_test(client, random_labels, volume_name)


def recurring_job_labels_test(client, labels, volume_name, size=SIZE, base_image=""):  # NOQA
    host_id = get_self_host_id()
    client.create_volume(name=volume_name, size=size,
                         numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

    # Simple Backup Job that runs every 2 minutes, retains 1.
    jobs = [
        {
            "name": RECURRING_JOB_NAME,
            "cron": "*/2 * * * *",
            "task": "backup",
            "retain": 1,
            "labels": labels
        }
    ]
    volume.recurringUpdate(jobs=jobs)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # 5 minutes
    time.sleep(300)
    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    # 1 from Backup, 1 from Volume Head.
    assert count == 2

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    backups = bv.backupList().data
    assert len(backups) == 1

    b = bv.backupGet(name=backups[0]["name"])
    for key, val in labels.iteritems():
        assert b["labels"].get(key) == val
    assert b["labels"].get(RECURRING_JOB_LABEL) == RECURRING_JOB_NAME
    if base_image:
        assert b["labels"].get(BASE_IMAGE_LABEL) == base_image
        # One extra Label from the BaseImage being set.
        assert len(b["labels"]) == len(labels) + 2
    else:
        # At least one extra Label from RecurringJob.
        assert len(b["labels"]) == len(labels) + 1

    cleanup_volume(client, volume)


@pytest.mark.csi
@pytest.mark.recurring_job
def test_recurring_job_kubernetes_status(client, core_api, volume_name):  # NOQA
    """
    Test that a RecurringJob properly backs up the KubernetesStatus of a
    Volume.
    """
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

    # 5 minutes
    time.sleep(300)
    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    # 1 from Backup, 1 from Volume Head.
    assert count == 2

    # Verify the Labels on the actual Backup.
    bv = client.by_id_backupVolume(volume_name)
    backups = bv.backupList().data
    assert len(backups) == 1

    b = bv.backupGet(name=backups[0]["name"])
    status = json.loads(b["labels"].get(KUBERNETES_STATUS_LABEL))
    assert b["labels"].get(RECURRING_JOB_LABEL) == RECURRING_JOB_NAME
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
    assert len(b["labels"]) == 2

    cleanup_volume(client, volume)
    delete_and_wait_pv(core_api, pv_name)
