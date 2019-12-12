import pytest
import common
import time

from common import client, core_api, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import check_volume_data, cleanup_volume, create_and_check_volume
from common import delete_replica_processes, crash_replica_processes
from common import get_self_host_id, get_volume_endpoint
from common import wait_for_snapshot_purge, write_volume_random_data
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import create_snapshot


@pytest.mark.coretest   # NOQA
def test_ha_simple_recovery(client, volume_name):  # NOQA
    ha_simple_recovery_test(client, volume_name, SIZE)


def ha_simple_recovery_test(client, volume_name, size, base_image=""):  # NOQA
    volume = create_and_check_volume(client, volume_name, 2, size, base_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    ha_rebuild_replica_test(client, volume_name)

    cleanup_volume(client, volume)


def ha_rebuild_replica_test(client, volname):   # NOQA
    volume = client.by_id_volume(volname)
    assert get_volume_endpoint(volume) == DEV_PATH + volname

    assert len(volume.replicas) == 2
    replica0 = volume.replicas[0]
    assert replica0.name != ""

    replica1 = volume.replicas[1]
    assert replica1.name != ""

    data = write_volume_random_data(volume)

    volume = volume.replicaRemove(name=replica0.name)

    # wait until we saw a replica starts rebuilding
    new_replica_found = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volname)
        for r in v.replicas:
            if r.name != replica0.name and \
                    r.name != replica1.name:
                new_replica_found = True
                break
        if new_replica_found:
            break
        time.sleep(RETRY_INTERVAL)
    assert new_replica_found

    volume = common.wait_for_volume_healthy(client, volname)

    volume = client.by_id_volume(volname)
    assert volume.state == common.VOLUME_STATE_ATTACHED
    assert volume.robustness == common.VOLUME_ROBUSTNESS_HEALTHY
    assert len(volume.replicas) >= 2

    found = False
    for replica in volume.replicas:
        if replica.name == replica1.name:
            found = True
            break
    assert found

    check_volume_data(volume, data)


@pytest.mark.coretest   # NOQA
def test_ha_salvage(client, core_api, volume_name):  # NOQA
    ha_salvage_test(client, core_api, volume_name)


def ha_salvage_test(client, core_api,  # NOQA
                    volume_name, base_image=""):  # NOQA
    # case: replica processes are wrongly removed
    volume = create_and_check_volume(client, volume_name, 2,
                                     base_image=base_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    delete_replica_processes(client, core_api, volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)

    # case: replica processes get crashed
    volume = create_and_check_volume(client, volume_name, 2,
                                     base_image=base_image)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    crash_replica_processes(client, core_api, volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)


# https://github.com/rancher/longhorn/issues/253
def test_ha_backup_deletion_recovery(client, volume_name):  # NOQA
    ha_backup_deletion_recovery_test(client, volume_name, SIZE)


def ha_backup_deletion_recovery_test(client, volume_name, size, base_image=""):  # NOQA
    volume = client.create_volume(name=volume_name, size=size,
                                  numberOfReplicas=2, baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    # test backupTarget for multiple settings
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        if common.is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            setting = client.update(setting, value=backupsettings[0])
            assert setting.value == backupsettings[0]

            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential.value == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting.value == backupstore
            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential.value == ""

        data = write_volume_random_data(volume)
        snap2 = create_snapshot(client, volume_name)
        create_snapshot(client, volume_name)

        volume.snapshotBackup(name=snap2.name)

        _, b = common.find_backup(client, volume_name, snap2.name)

        res_name = common.generate_volume_name()
        res_volume = client.create_volume(name=res_name, size=size,
                                          numberOfReplicas=2,
                                          fromBackup=b.url)
        res_volume = common.wait_for_volume_restoration_completed(
            client, res_name)
        res_volume = common.wait_for_volume_detached(client, res_name)
        res_volume = res_volume.attach(hostId=host_id)
        res_volume = common.wait_for_volume_healthy(client, res_name)
        check_volume_data(res_volume, data)

        snapshots = res_volume.snapshotList()
        # only the backup snapshot + volume-head
        assert len(snapshots) == 2
        backup_snapshot = ""
        for snap in snapshots:
            if snap.name != "volume-head":
                backup_snapshot = snap.name
        assert backup_snapshot != ""

        create_snapshot(client, res_name)
        snapshots = res_volume.snapshotList()
        assert len(snapshots) == 3

        res_volume.snapshotDelete(name=backup_snapshot)
        res_volume.snapshotPurge()
        res_volume = wait_for_snapshot_purge(client, res_name,
                                             backup_snapshot)

        snapshots = res_volume.snapshotList()
        assert len(snapshots) == 2

        ha_rebuild_replica_test(client, res_name)

        res_volume = res_volume.detach()
        res_volume = common.wait_for_volume_detached(client, res_name)

        client.delete(res_volume)
        common.wait_for_volume_delete(client, res_name)

    cleanup_volume(client, volume)


# https://github.com/rancher/longhorn/issues/415
def test_ha_prohibit_deleting_last_replica(client, volume_name):  # NOQA
    volume = create_and_check_volume(client, volume_name, 1)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 1
    replica0 = volume.replicas[0]

    with pytest.raises(Exception) as e:
        volume.replicaRemove(name=replica0.name)
    assert "no other healthy replica available" in str(e.value)

    cleanup_volume(client, volume)
