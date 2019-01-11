import pytest
import time

import common
from common import clients, volume_name  # NOQA
from common import wait_for_volume_delete
from common import SIZE

@pytest.mark.recurring_job  # NOQA
def test_recurring_job(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)

    # snapshot every one minute
    job_snap = {"name": "snap", "cron": "* * * * *",
                "task": "snapshot", "retain": 2}
    # backup every two minutes
    job_backup = {"name": "backup", "cron": "*/2 * * * *",
                  "task": "backup", "retain": 1}
    volume.recurringUpdate(jobs=[job_snap, job_backup])

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # 5 minutes
    time.sleep(300)

    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    # 2 snapshots, 1 backup, 1 volume-head
    assert count == 4

    job_backup2 = {"name": "backup2", "cron": "* * * * *",
                   "task": "backup", "retain": 2}
    volume.recurringUpdate(jobs=[job_snap, job_backup2])

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
