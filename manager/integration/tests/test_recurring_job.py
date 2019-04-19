import pytest
import time
import json

import common
from common import client, clients, core_api, volume_name  # NOQA
from common import storage_class, statefulset  # NOQA
from common import wait_for_volume_delete
from common import create_storage_class, create_and_wait_statefulset
from common import update_statefulset_manifests, get_statefulset_pod_info
from common import SIZE


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
