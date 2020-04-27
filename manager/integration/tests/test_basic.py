import time
import common
import subprocess
import pytest

from common import clients, random_labels, volume_name  # NOQA
from common import core_api, apps_api, pod   # NOQA
from common import SIZE, DEV_PATH, EXPAND_SIZE
from common import check_device_data, write_device_random_data
from common import check_volume_data, write_volume_random_data
from common import get_self_host_id, volume_valid
from common import iscsi_login, iscsi_logout
from common import wait_for_volume_status
from common import wait_for_volume_delete
from common import wait_for_snapshot_purge
from common import generate_volume_name
from common import get_volume_endpoint, get_volume_engine
from common import get_random_client
from common import activate_standby_volume, check_volume_last_backup
from common import create_pv_for_volume, create_pvc_for_volume
from common import create_and_wait_pod, delete_and_wait_pod
from common import delete_and_wait_pvc, delete_and_wait_pv
from common import CONDITION_STATUS_FALSE, CONDITION_STATUS_TRUE
from common import RETRY_COUNTS, RETRY_INTERVAL, RETRY_COMMAND_COUNT
from common import cleanup_volume, create_and_check_volume, create_backup
from common import DEFAULT_VOLUME_SIZE
from common import Gi
from common import wait_for_volume_detached
from common import create_pvc_spec
from common import generate_random_data, write_volume_data
from common import VOLUME_RWTEST_SIZE
from common import write_pod_volume_data
from common import find_backup
from common import wait_for_backup_completion
from common import create_storage_class
from common import wait_for_volume_restoration_completed
from common import read_volume_data
from common import delete_backup
from common import pvc_name # NOQA
from common import storage_class # NOQA
from common import pod_make # NOQA
from common import set_random_backupstore
from common import create_snapshot
from common import expand_attached_volume
from common import wait_for_dr_volume_expansion
from common import check_block_device_size
from common import wait_for_rebuild_complete
from common import wait_for_volume_expansion
from common import fail_replica_expansion, wait_for_expansion_failure
from common import VOLUME_FRONTEND_BLOCKDEV, VOLUME_FRONTEND_ISCSI


@pytest.mark.coretest   # NOQA
def test_hosts(clients):  # NOQA
    """
    Check node name and IP
    """
    hosts = next(iter(clients.values())).list_node()
    for host in hosts:
        assert host.name is not None
        assert host.address is not None

    host_id = []
    for i in range(0, len(hosts)):
        host_id.append(hosts.data[i].name)

    host0_from_i = {}
    for i in range(0, len(hosts)):
        if len(host0_from_i) == 0:
            host0_from_i = clients[host_id[0]].by_id_node(host_id[0])
        else:
            assert host0_from_i.name == \
                clients[host_id[i]].by_id_node(host_id[0]).name
            assert host0_from_i.address == \
                clients[host_id[i]].by_id_node(host_id[0]).address


@pytest.mark.coretest   # NOQA
def test_settings(clients):  # NOQA
    """
    Check input for settings
    """
    client = get_random_client(clients)

    setting_names = [common.SETTING_BACKUP_TARGET,
                     common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET,
                     common.SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE,
                     common.SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE,
                     common.SETTING_DEFAULT_REPLICA_COUNT]
    settings = client.list_setting()

    settingMap = {}
    for setting in settings:
        settingMap[setting.name] = setting

    for name in setting_names:
        assert settingMap[name] is not None
        assert settingMap[name].definition.description is not None

    for name in setting_names:
        setting = client.by_id_setting(name)
        assert settingMap[name].value == setting.value

        old_value = setting.value

        if name == common.SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE:
            with pytest.raises(Exception) as e:
                client.update(setting, value="-100")
            assert "with invalid "+name in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert "with invalid "+name in \
                   str(e.value)
            setting = client.update(setting, value="200")
            assert setting.value == "200"
            setting = client.by_id_setting(name)
            assert setting.value == "200"
        elif name == common.SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE:
            with pytest.raises(Exception) as e:
                client.update(setting, value="300")
            assert "with invalid "+name in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="-30")
            assert "with invalid "+name in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert "with invalid "+name in \
                   str(e.value)
            setting = client.update(setting, value="30")
            assert setting.value == "30"
            setting = client.by_id_setting(name)
            assert setting.value == "30"
        elif name == common.SETTING_BACKUP_TARGET:
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue$test")
            assert "with invalid "+name in \
                   str(e.value)
            setting = client.update(setting, value="nfs://test")
            assert setting.value == "nfs://test"
            setting = client.by_id_setting(name)
            assert setting.value == "nfs://test"
        elif name == common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET:
            setting = client.update(setting, value="testvalue")
            assert setting.value == "testvalue"
            setting = client.by_id_setting(name)
            assert setting.value == "testvalue"
        elif name == common.SETTING_DEFAULT_REPLICA_COUNT:
            with pytest.raises(Exception) as e:
                client.update(setting, value="-1")
            assert "with invalid "+name in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert "with invalid "+name in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="21")
            assert "with invalid "+name in \
                   str(e.value)
            setting = client.update(setting, value="2")
            assert setting.value == "2"
            setting = client.by_id_setting(name)
            assert setting.value == "2"

        setting = client.update(setting, value=old_value)
        assert setting.value == old_value


def volume_rw_test(dev):
    assert volume_valid(dev)
    data = write_device_random_data(dev)
    check_device_data(dev, data)


@pytest.mark.coretest   # NOQA
def test_volume_basic(clients, volume_name):  # NOQA
    """
    Test basic volume operations:

    1. Check volume name and parameter
    2. Create a volume and attach to the current node, then check volume states
    3. Check soft anti-affinity rule
    4. Write then read back to check volume data
    """
    volume_basic_test(clients, volume_name)


def volume_basic_test(clients, volume_name, base_image=""):  # NOQA
    num_hosts = len(clients)
    num_replicas = 3

    # get a random client
    for host_id, client in iter(clients.items()):
        break

    with pytest.raises(Exception):
        volume = client.create_volume(name="wrong_volume-name-1.0", size=SIZE,
                                      numberOfReplicas=2)
        volume = client.create_volume(name="wrong_volume-name", size=SIZE,
                                      numberOfReplicas=2)
        volume = client.create_volume(name="wrong_volume-name", size=SIZE,
                                      numberOfReplicas=2,
                                      frontend="invalid_frontend")

    volume = create_and_check_volume(client, volume_name, num_replicas, SIZE,
                                     base_image)
    assert volume.initialRestorationRequired is False

    def validate_volume_basic(expected, actual):
        assert actual.name == expected.name
        assert actual.size == expected.size
        assert actual.numberOfReplicas == expected.numberOfReplicas
        assert actual.frontend == VOLUME_FRONTEND_BLOCKDEV
        assert actual.baseImage == base_image
        assert actual.state == expected.state
        assert actual.created == expected.created

    volumes = client.list_volume().data
    assert len(volumes) == 1
    validate_volume_basic(volume, volumes[0])

    volumeByName = client.by_id_volume(volume_name)
    validate_volume_basic(volume, volumeByName)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.initialRestorationRequired is False

    volumeByName = client.by_id_volume(volume_name)
    validate_volume_basic(volume, volumeByName)
    assert get_volume_endpoint(volumeByName) == DEV_PATH + volume_name

    # validate soft anti-affinity
    hosts = {}
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        hosts[id] = True
    if num_hosts >= num_replicas:
        assert len(hosts) == num_replicas
    else:
        assert len(hosts) == num_hosts

    volumes = client.list_volume().data
    assert len(volumes) == 1
    assert volumes[0].name == volume.name
    assert volumes[0].size == volume.size
    assert volumes[0].numberOfReplicas == volume.numberOfReplicas
    assert volumes[0].state == volume.state
    assert volumes[0].created == volume.created
    assert get_volume_endpoint(volumes[0]) == DEV_PATH + volume_name

    volume = client.by_id_volume(volume_name)
    assert get_volume_endpoint(volume) == DEV_PATH + volume_name

    volume_rw_test(get_volume_endpoint(volume))

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume.initialRestorationRequired is False

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume().data
    assert len(volumes) == 0


def test_volume_iscsi_basic(clients, volume_name):  # NOQA
    """
    Test basic volume operations with iscsi frontend

    1. Create and attach a volume with iscsi frontend
    2. Check the volume endpoint and connect it using the iscsi
    initator on the node.
    3. Write then read back volume data for validation

    """
    volume_iscsi_basic_test(clients, volume_name)


def volume_iscsi_basic_test(clients, volume_name, base_image=""):  # NOQA
    # get a random client
    for host_id, client in iter(clients.items()):
        break

    volume = create_and_check_volume(client, volume_name, 3, SIZE, base_image,
                                     VOLUME_FRONTEND_ISCSI)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volumes = client.list_volume().data
    assert len(volumes) == 1
    assert volumes[0].name == volume.name
    assert volumes[0].size == volume.size
    assert volumes[0].numberOfReplicas == volume.numberOfReplicas
    assert volumes[0].state == volume.state
    assert volumes[0].created == volume.created
    assert volumes[0].frontend == VOLUME_FRONTEND_ISCSI
    endpoint = get_volume_endpoint(volumes[0])
    assert endpoint.startswith("iscsi://")

    try:
        dev = iscsi_login(endpoint)
        volume_rw_test(dev)
    finally:
        iscsi_logout(endpoint)

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_snapshot(clients, volume_name, base_image=""):  # NOQA
    """
    Test snapshot operations

    1. Create a volume and attach to the node
    2. Create the empty snapshot `snap1`
    3. Generate and write data `snap2_data`, then create `snap2`
    4. Generate and write data `snap3_data`, then create `snap3`
    5. List snapshot. Validate the snapshot chain relationship
    6. Mark `snap3` as removed. Make sure volume's data didn't change
    7. List snapshot. Make sure `snap3` is marked as removed
    8. Detach and reattach the volume in maintenance mode.
    9. Make sure the volume frontend is still `blockdev` but disabled
    10. Revert to `snap2`
    11. Detach and reattach the volume with frontend enabled
    12. Make sure volume's data is `snap2_data`
    13. List snapshot. Make sure `volume-head` is now `snap2`'s child
    14. Delete `snap1` and `snap2`
    15. Purge the snapshot.
    16. List the snapshot, make sure `snap1` and `snap3`
    are gone. `snap2` is marked as removed.
    17. Check volume data, make sure it's still `snap2_data`.
    """
    snapshot_test(clients, volume_name, base_image)


def snapshot_test(clients, volume_name, base_image):  # NOQA
    for host_id, client in iter(clients.items()):
        break

    volume = create_and_check_volume(client, volume_name,
                                     base_image=base_image)

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    positions = {}

    snap1 = create_snapshot(client, volume_name)

    snap2_data = write_volume_random_data(volume, positions)
    snap2 = create_snapshot(client, volume_name)

    snap3_data = write_volume_random_data(volume, positions)
    snap3 = create_snapshot(client, volume_name)

    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap1.name].name == snap1.name
    assert snapMap[snap1.name].removed is False
    assert snapMap[snap2.name].name == snap2.name
    assert snapMap[snap2.name].parent == snap1.name
    assert snapMap[snap2.name].removed is False
    assert snapMap[snap3.name].name == snap3.name
    assert snapMap[snap3.name].parent == snap2.name
    assert snapMap[snap3.name].removed is False

    volume.snapshotDelete(name=snap3.name)
    check_volume_data(volume, snap3_data)

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap1.name].name == snap1.name
    assert snapMap[snap1.name].removed is False
    assert snapMap[snap2.name].name == snap2.name
    assert snapMap[snap2.name].parent == snap1.name
    assert snapMap[snap2.name].removed is False
    assert snapMap[snap3.name].name == snap3.name
    assert snapMap[snap3.name].parent == snap2.name
    assert len(snapMap[snap3.name].children) == 1
    assert "volume-head" in snapMap[snap3.name].children.keys()
    assert snapMap[snap3.name].removed is True

    snap = volume.snapshotGet(name=snap3.name)
    assert snap.name == snap3.name
    assert snap.parent == snap3.parent
    assert len(snap3.children) == 1
    assert len(snap.children) == 1
    assert "volume-head" in snap3.children.keys()
    assert "volume-head" in snap.children.keys()
    assert snap.removed is True

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=True)
    common.wait_for_volume_healthy_no_frontend(client, volume_name)

    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    assert engine.endpoint == ""

    volume.snapshotRevert(name=snap2.name)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    check_volume_data(volume, snap2_data)

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap1.name].name == snap1.name
    assert snapMap[snap1.name].removed is False
    assert snapMap[snap2.name].name == snap2.name
    assert snapMap[snap2.name].parent == snap1.name
    assert "volume-head" in snapMap[snap2.name].children.keys()
    assert snap3.name in snapMap[snap2.name].children.keys()
    assert snapMap[snap2.name].removed is False
    assert snapMap[snap3.name].name == snap3.name
    assert snapMap[snap3.name].parent == snap2.name
    assert len(snapMap[snap3.name].children) == 0
    assert snapMap[snap3.name].removed is True

    volume.snapshotDelete(name=snap1.name)
    volume.snapshotDelete(name=snap2.name)

    volume.snapshotPurge()
    volume = wait_for_snapshot_purge(client, volume_name, snap1.name,
                                     snap3.name)

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap
    assert snap1.name not in snapMap
    assert snap3.name not in snapMap

    # it's the parent of volume-head, so it cannot be purged at this time
    assert snapMap[snap2.name].name == snap2.name
    assert snapMap[snap2.name].parent == ""
    assert "volume-head" in snapMap[snap2.name].children.keys()
    assert snapMap[snap2.name].removed is True
    check_volume_data(volume, snap2_data)

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_backup(clients, volume_name):  # NOQA
    """
    Test basic backup

    Setup:

    1. Create a volume and attach to the current node
    2. Run the test for all the available backupstores.

    Steps:

    1. Create a backup of volume
    2. Restore the backup to a new volume
    3. Attach the new volume and make sure the data is the same as the old one
    4. Detach the volume and delete the backup.
    5. Wait for the restored volume's `lastBackup` to be cleaned (due to remove
    the backup)
    6. Delete the volume
    """
    backup_test(clients, volume_name, SIZE)


def backup_test(clients, volume_name, size, base_image=""):  # NOQA
    for host_id, client in iter(clients.items()):
        break

    volume = create_and_check_volume(client, volume_name, 2, size, base_image)

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
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

        backupstore_test(client, lht_hostId, volume_name, size)

    cleanup_volume(client, volume)


def backupstore_test(client, host_id, volname, size):
    bv, b, snap2, data = create_backup(client, volname)

    # test restore
    restoreName = generate_volume_name()
    volume = client.create_volume(name=restoreName, size=size,
                                  numberOfReplicas=2,
                                  fromBackup=b.url)

    volume = common.wait_for_volume_restoration_completed(client, restoreName)
    volume = common.wait_for_volume_detached(client, restoreName)
    assert volume.name == restoreName
    assert volume.size == size
    assert volume.numberOfReplicas == 2
    assert volume.state == "detached"
    assert volume.initialRestorationRequired is False

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, restoreName)
    check_volume_data(volume, data)
    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, restoreName)

    delete_backup(bv, b.name)

    volume = wait_for_volume_status(client, volume.name,
                                    "lastBackup", "")
    assert volume.lastBackupAt == ""

    client.delete(volume)

    volume = wait_for_volume_delete(client, restoreName)


@pytest.mark.coretest
def test_backup_labels(clients, random_labels, volume_name):  # NOQA
    """
    Test that the proper Labels are applied when creating a Backup manually.

    1. Create a volume
    2. Run the following steps on all backupstores
    3. Create a backup with some random labels
    4. Get backup from backupstore, verify the labels are set on the backups
    """
    backup_labels_test(clients, random_labels, volume_name)


def backup_labels_test(clients, random_labels, volume_name, size=SIZE, base_image=""):  # NOQA
    for _, client in iter(clients.items()):
        break
    host_id = get_self_host_id()

    volume = create_and_check_volume(client, volume_name, 2, size, base_image)

    volume.attach(hostId=host_id)
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

        bv, b, _, _ = create_backup(client, volume_name, labels=random_labels)
        # If we're running the test with a BaseImage, check that this Label is
        # set properly.
        backup = bv.backupGet(name=b.name)
        if base_image:
            assert backup.labels.get(common.BASE_IMAGE_LABEL) == base_image
            # One extra Label from the BaseImage being set.
            assert len(backup.labels) == len(random_labels) + 1
        else:
            assert len(backup.labels) == len(random_labels)

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_restore_inc(clients, core_api, volume_name, pod):  # NOQA
    """
    Test restore from disaster recovery volume (incremental restore)

    Run test against all the backupstores

    1. Create a volume and attach to the current node
    2. Generate `data0`, write to the volume, make a backup `backup0`
    3. Create three DR(standby) volumes from the backup: `sb_volume0/1/2`
    4. Wait for all three DR volumes to finish the initial restoration
    5. Verify DR volumes's `lastBackup` is `backup0`
    6. Verify snapshot/pv/pvc/change backup target are not allowed as long
    as the DR volume exists
    7. Activate standby `sb_volume0` and attach it to check the volume data
    8. Generate `data1` and write to the original volume and create `backup1`
    9. Make sure `sb_volume1`'s `lastBackup` field has been updated to
    `backup1`
    10. Wait for `sb_volume1` to finish incremental restoration then activate
    11. Attach and check `sb_volume1`'s data
    12. Generate `data2` and write to the original volume and create `backup2`
    13. Make sure `sb_volume2`'s `lastBackup` field has been updated to
    `backup1`
    14. Wait for `sb_volume2` to finish incremental restoration then activate
    15. Attach and check `sb_volume2`'s data
    16. Create PV, PVC and Pod to use `sb_volume2`, check PV/PVC/POD are good

    FIXME: Step 16 works because the disk will be treated as a unformatted disk
    """
    for _, client in iter(clients.items()):
        break

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

        restore_inc_test(client, core_api, volume_name, pod)


def restore_inc_test(client, core_api, volume_name, pod):  # NOQA
    std_volume = create_and_check_volume(client, volume_name, 2, SIZE)
    lht_host_id = get_self_host_id()
    std_volume.attach(hostId=lht_host_id)
    std_volume = common.wait_for_volume_healthy(client, volume_name)

    with pytest.raises(Exception) as e:
        std_volume.activate(frontend=VOLUME_FRONTEND_BLOCKDEV)
        assert "already in active mode" in str(e.value)

    data0 = {'len': 4 * 1024, 'pos': 0}
    data0['content'] = common.generate_random_data(data0['len'])
    bv, backup0, _, data0 = create_backup(
        client, volume_name, data0)

    sb_volume0_name = "sb-0-" + volume_name
    sb_volume1_name = "sb-1-" + volume_name
    sb_volume2_name = "sb-2-" + volume_name
    client.create_volume(name=sb_volume0_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    client.create_volume(name=sb_volume1_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    client.create_volume(name=sb_volume2_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    common.wait_for_volume_restoration_completed(client, sb_volume0_name)
    common.wait_for_volume_restoration_completed(client, sb_volume1_name)
    common.wait_for_volume_restoration_completed(client, sb_volume2_name)

    sb_volume0 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume0_name)
    sb_volume1 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume1_name)
    sb_volume2 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume2_name)

    for i in range(RETRY_COUNTS):
        sb_volume0 = client.by_id_volume(sb_volume0_name)
        sb_volume1 = client.by_id_volume(sb_volume1_name)
        sb_volume2 = client.by_id_volume(sb_volume2_name)
        sb_engine0 = get_volume_engine(sb_volume0)
        sb_engine1 = get_volume_engine(sb_volume1)
        sb_engine2 = get_volume_engine(sb_volume2)
        if sb_volume0.initialRestorationRequired is True or \
           sb_volume1.initialRestorationRequired is True or \
           sb_volume2.initialRestorationRequired is True:
            time.sleep(RETRY_INTERVAL)
        else:
            break
    assert sb_volume0.standby is True
    assert sb_volume0.lastBackup == backup0.name
    assert sb_volume0.frontend == ""
    assert sb_volume0.initialRestorationRequired is False
    sb_engine0 = get_volume_engine(sb_volume0)
    assert sb_engine0.lastRestoredBackup == backup0.name
    assert sb_engine0.requestedBackupRestore == backup0.name
    assert sb_volume1.standby is True
    assert sb_volume1.lastBackup == backup0.name
    assert sb_volume1.frontend == ""
    assert sb_volume1.initialRestorationRequired is False
    sb_engine1 = get_volume_engine(sb_volume1)
    assert sb_engine1.lastRestoredBackup == backup0.name
    assert sb_engine1.requestedBackupRestore == backup0.name
    assert sb_volume2.standby is True
    assert sb_volume2.lastBackup == backup0.name
    assert sb_volume2.frontend == ""
    assert sb_volume2.initialRestorationRequired is False
    sb_engine2 = get_volume_engine(sb_volume2)
    assert sb_engine2.lastRestoredBackup == backup0.name
    assert sb_engine2.requestedBackupRestore == backup0.name

    sb0_snaps = sb_volume0.snapshotList()
    assert len(sb0_snaps) == 2
    for s in sb0_snaps:
        if s.name != "volume-head":
            sb0_snap = s
    assert sb0_snaps
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotCreate()
        assert "cannot create snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotRevert(name=sb0_snap.name)
        assert "cannot revert snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotDelete(name=sb0_snap.name)
        assert "cannot delete snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotBackup(name=sb0_snap.name)
        assert "cannot create backup for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.pvCreate(pvName=sb_volume0_name)
        assert "cannot create PV for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.pvcCreate(pvcName=sb_volume0_name)
        assert "cannot create PVC for standby volume" in str(e.value)
    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    with pytest.raises(Exception) as e:
        client.update(setting, value="random.backup.target")
        assert "cannot modify BackupTarget " \
               "since there are existing standby volumes" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.activate(frontend="wrong_frontend")
        assert "invalid frontend" in str(e.value)

    activate_standby_volume(client, sb_volume0_name)
    sb_volume0 = client.by_id_volume(sb_volume0_name)
    sb_volume0.attach(hostId=lht_host_id)
    sb_volume0 = common.wait_for_volume_healthy(client, sb_volume0_name)
    check_volume_data(sb_volume0, data0, False)

    zero_string = b'\x00'.decode('utf-8')
    _, backup1, _, data1 = create_backup(
        client, volume_name,
        {'len': 2 * 1024, 'pos': 0, 'content': zero_string * 2 * 1024})
    # use this api to update field `last backup`
    client.list_backupVolume()
    check_volume_last_backup(client, sb_volume1_name, backup1.name)
    activate_standby_volume(client, sb_volume1_name)
    sb_volume1 = client.by_id_volume(sb_volume1_name)
    sb_volume1.attach(hostId=lht_host_id)
    sb_volume1 = common.wait_for_volume_healthy(client, sb_volume1_name)
    data0_modified = {
        'len': data0['len'] - data1['len'],
        'pos': data1['len'],
        'content': data0['content'][data1['len']:],
    }
    check_volume_data(sb_volume1, data0_modified, False)
    check_volume_data(sb_volume1, data1)

    data2 = {'len': 1 * 1024 * 1024, 'pos': 0}
    data2['content'] = common.generate_random_data(data2['len'])
    _, backup2, _, data2 = create_backup(client, volume_name, data2)
    client.list_backupVolume()
    check_volume_last_backup(client, sb_volume2_name, backup2.name)
    activate_standby_volume(client, sb_volume2_name)
    sb_volume2 = client.by_id_volume(sb_volume2_name)
    sb_volume2.attach(hostId=lht_host_id)
    sb_volume2 = common.wait_for_volume_healthy(client, sb_volume2_name)
    check_volume_data(sb_volume2, data2)

    # allocated this active volume to a pod
    sb_volume2.detach()
    sb_volume2 = common.wait_for_volume_detached(client, sb_volume2_name)

    create_pv_for_volume(client, core_api, sb_volume2, sb_volume2_name)
    create_pvc_for_volume(client, core_api, sb_volume2, sb_volume2_name)

    sb_volume2_pod_name = "pod-" + sb_volume2_name
    pod['metadata']['name'] = sb_volume2_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': sb_volume2_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    sb_volume2 = client.by_id_volume(sb_volume2_name)
    k_status = sb_volume2.kubernetesStatus
    workloads = k_status.workloadsStatus
    assert k_status.pvName == sb_volume2_name
    assert k_status.pvStatus == 'Bound'
    assert len(workloads) == 1
    for i in range(RETRY_COUNTS):
        if workloads[0].podStatus == 'Running':
            break
        time.sleep(RETRY_INTERVAL)
        sb_volume2 = client.by_id_volume(sb_volume2_name)
        k_status = sb_volume2.kubernetesStatus
        workloads = k_status.workloadsStatus
        assert len(workloads) == 1
    assert workloads[0].podName == sb_volume2_pod_name
    assert workloads[0].podStatus == 'Running'
    assert not workloads[0].workloadName
    assert not workloads[0].workloadType
    assert k_status.namespace == 'default'
    assert k_status.pvcName == sb_volume2_name
    assert not k_status.lastPVCRefAt
    assert not k_status.lastPodRefAt

    delete_and_wait_pod(core_api, sb_volume2_pod_name)
    delete_and_wait_pvc(core_api, sb_volume2_name)
    delete_and_wait_pv(core_api, sb_volume2_name)

    # cleanup
    std_volume.detach()
    sb_volume0.detach()
    sb_volume1.detach()
    std_volume = common.wait_for_volume_detached(client, volume_name)
    sb_volume0 = common.wait_for_volume_detached(client, sb_volume0_name)
    sb_volume1 = common.wait_for_volume_detached(client, sb_volume1_name)
    sb_volume2 = common.wait_for_volume_detached(client, sb_volume2_name)

    bv.backupDelete(name=backup2.name)
    bv.backupDelete(name=backup1.name)
    bv.backupDelete(name=backup0.name)

    client.delete(std_volume)
    client.delete(sb_volume0)
    client.delete(sb_volume1)
    client.delete(sb_volume2)

    wait_for_volume_delete(client, volume_name)
    wait_for_volume_delete(client, sb_volume0_name)
    wait_for_volume_delete(client, sb_volume1_name)
    wait_for_volume_delete(client, sb_volume2_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_deleting_backup_volume(clients):  # NOQA
    """
    Test deleting backup volumes

    1. Create volume and create backup
    2. Delete the backup and make sure it's gone in the backupstore
    """
    for host_id, client in iter(clients.items()):
        break
    lht_hostId = get_self_host_id()

    volName = generate_volume_name()
    volume = create_and_check_volume(client, volName)

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volName)

    bv, _, snap1, _ = create_backup(client, volName)
    _, _, snap2, _ = create_backup(client, volName)

    bv = client.by_id_backupVolume(volName)
    client.delete(bv)
    common.wait_for_backup_volume_delete(client, volName)
    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_listing_backup_volume(clients, base_image=""):   # NOQA
    """
    Test listing backup volumes

    1. Create three volumes: `volume1/2/3`
    2. Setup NFS backupstore since we can manipulate the content easily
    3. Create snapshots for all three volumes
    4. Rename `volume1`'s `volume.cfg` to `volume.cfg.tmp` in backupstore
    5. List backup volumes. Make sure `volume1` errors out but found other two
    6. Restore `volume1`'s `volume.cfg`.
    7. Make sure now backup volume `volume1` can be found and deleted
    8. Delete backups for `volume2/3`, make sure they cannot be found later
    """
    for host_id, client in iter(clients.items()):
        break
    lht_hostId = get_self_host_id()

    # create 3 volumes.
    volume1_name = generate_volume_name()
    volume2_name = generate_volume_name()
    volume3_name = generate_volume_name()

    volume1 = create_and_check_volume(client, volume1_name)
    volume2 = create_and_check_volume(client, volume2_name)
    volume3 = create_and_check_volume(client, volume3_name)

    volume1.attach(hostId=lht_hostId)
    volume1 = common.wait_for_volume_healthy(client, volume1_name)
    volume2.attach(hostId=lht_hostId)
    volume2 = common.wait_for_volume_healthy(client, volume2_name)
    volume3.attach(hostId=lht_hostId)
    volume3 = common.wait_for_volume_healthy(client, volume3_name)

    # we only test NFS here.
    # Since it is difficult to directly remove volume.cfg from s3 buckets
    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        if common.is_backupTarget_nfs(backupstore):
            updated = False
            for i in range(RETRY_COMMAND_COUNT):
                nfs_url = backupstore.strip("nfs://")
                setting = client.update(setting, value=backupstore)
                assert setting.value == backupstore
                setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
                if "nfs" in setting.value:
                    updated = True
                    break
            assert updated

    _, _, snap1, _ = create_backup(client, volume1_name)
    _, _, snap2, _ = create_backup(client, volume2_name)
    _, _, snap3, _ = create_backup(client, volume3_name)

    # invalidate backup volume 1 by renaming volume.cfg to volume.cfg.tmp
    cmd = ["mkdir", "-p", "/mnt/nfs"]
    subprocess.check_output(cmd)
    cmd = ["mount", "-t", "nfs4", nfs_url, "/mnt/nfs"]
    subprocess.check_output(cmd)
    cmd = ["find", "/mnt/nfs", "-type", "d", "-name", volume1_name]
    volume1_backup_volume_path = \
        subprocess.check_output(cmd).strip().decode('utf-8')

    cmd = ["find", volume1_backup_volume_path, "-name", "volume.cfg"]
    volume1_backup_volume_cfg_path = \
        subprocess.check_output(cmd).strip().decode('utf-8')
    cmd = ["mv", volume1_backup_volume_cfg_path,
           volume1_backup_volume_cfg_path + ".tmp"]
    subprocess.check_output(cmd)
    subprocess.check_output(["sync"])

    found1 = found2 = found3 = False
    for i in range(RETRY_COUNTS):
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv.name == volume1_name:
                if "error" in bv.messages:
                    assert "volume.cfg" in bv.messages.error.lower()
                    found1 = True
            elif bv.name == volume2_name:
                assert not bv.messages
                found2 = True
            elif bv.name == volume3_name:
                assert not bv.messages
                found3 = True
        if found1 & found2 & found3:
            break
        time.sleep(RETRY_INTERVAL)
    assert found1 & found2 & found3

    cmd = ["mv", volume1_backup_volume_cfg_path + ".tmp",
           volume1_backup_volume_cfg_path]
    subprocess.check_output(cmd)
    subprocess.check_output(["sync"])

    found = False
    for i in range(RETRY_COMMAND_COUNT):
        try:
            bv1, b1 = common.find_backup(client, volume1_name, snap1.name)
            found = True
            break
        except Exception:
            time.sleep(1)
    assert found
    bv1.backupDelete(name=b1.name)
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups1 = bv1.backupList().data
        for b in backups1:
            if b.snapshotName == snap1.name:
                found = True
                break
    assert not found

    bv2, b2 = common.find_backup(client, volume2_name, snap2.name)
    bv2.backupDelete(name=b2.name)
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups2 = bv2.backupList().data
        for b in backups2:
            if b.snapshotName == snap2.name:
                found = True
                break
    assert not found

    bv3, b3 = common.find_backup(client, volume3_name, snap3.name)
    bv3.backupDelete(name=b3.name)
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups3 = bv3.backupList().data
        for b in backups3:
            if b.snapshotName == snap3.name:
                found = True
                break
    assert not found

    volume1.detach()
    volume1 = common.wait_for_volume_detached(client, volume1_name)
    client.delete(volume1)
    wait_for_volume_delete(client, volume1_name)

    volume2.detach()
    volume2 = common.wait_for_volume_detached(client, volume2_name)
    client.delete(volume2)
    wait_for_volume_delete(client, volume2_name)

    volume3.detach()
    volume3 = common.wait_for_volume_detached(client, volume3_name)
    client.delete(volume3)
    wait_for_volume_delete(client, volume3_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.coretest   # NOQA
def test_volume_multinode(clients, volume_name):  # NOQA
    """
    Test the volume can be attached on multiple nodes

    1. Create one volume
    2. Attach it on every node once, verify the state, then detach it
    """
    hosts = clients.keys()

    volume = get_random_client(clients).create_volume(name=volume_name,
                                                      size=SIZE,
                                                      numberOfReplicas=2)
    volume = common.wait_for_volume_detached(get_random_client(clients),
                                             volume_name)

    for host_id in hosts:
        volume = volume.attach(hostId=host_id)
        volume = common.wait_for_volume_healthy(get_random_client(clients),
                                                volume_name)
        engine = get_volume_engine(volume)
        assert engine.hostId == host_id
        volume = volume.detach()
        volume = common.wait_for_volume_detached(get_random_client(clients),
                                                 volume_name)

    get_random_client(clients).delete(volume)
    wait_for_volume_delete(get_random_client(clients), volume_name)

    volumes = get_random_client(clients).list_volume()
    assert len(volumes) == 0


@pytest.mark.coretest  # NOQA
def test_volume_scheduling_failure(clients, volume_name):  # NOQA
    '''
    Test fail to schedule by disable scheduling for all the nodes

    Also test cannot attach a scheduling failed volume

    1. Disable `allowScheduling` for all nodes
    2. Create a volume.
    3. Verify the volume condition `Scheduled` is false
    4. Verify attaching the volume will result in error
    5. Enable `allowScheduling` for all nodes
    6. Volume should be automatically scheduled (condition become true)
    7. Volume can be attached now
    '''
    client = get_random_client(clients)
    nodes = client.list_node()
    assert len(nodes) > 0

    for node in nodes:
        node = client.update(node, allowScheduling=False)
        node = common.wait_for_node_update(client, node.id,
                                           "allowScheduling", False)

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3)

    volume = common.wait_for_volume_condition_scheduled(client, volume_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)
    volume = common.wait_for_volume_detached(client, volume_name)
    self_node = get_self_host_id()
    with pytest.raises(Exception) as e:
        volume.attach(hostId=self_node)
    assert "not scheduled" in str(e.value)

    for node in nodes:
        node = client.update(node, allowScheduling=True)
        node = common.wait_for_node_update(client, node.id,
                                           "allowScheduling", True)

    volume = common.wait_for_volume_condition_scheduled(client, volume_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, volume_name)
    volume = volume.attach(hostId=self_node)
    volume = common.wait_for_volume_healthy(client, volume_name)
    endpoint = get_volume_endpoint(volume)
    assert endpoint != ""
    volume_rw_test(endpoint)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_setting_default_replica_count(clients, volume_name):  # NOQA
    """
    Test `Default Replica Count` setting

    1. Set default replica count in the global settings to 5
    2. Create a volume without specify the replica count
    3. The volume should have 5 replicas (instead of the previous default 3)
    """
    client = get_random_client(clients)
    setting = client.by_id_setting(common.SETTING_DEFAULT_REPLICA_COUNT)
    old_value = setting.value
    setting = client.update(setting, value="5")

    volume = client.create_volume(name=volume_name, size=SIZE)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == int(setting.value)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    setting = client.update(setting, value=old_value)


@pytest.mark.coretest   # NOQA
def test_volume_update_replica_count(clients, volume_name):  # NOQA
    """
    Test updating volume's replica count

    1. Create a volume with 3 replicas
    2. Attach the volume
    3. Increase the replica to 5.
    4. Volume will become degraded and start rebuilding
    5. Wait for rebuilding to complete
    6. Update the replica count to 2. Volume should remain healthy
    7. Remove 3 replicas, so there will be 2 replicas in the volume
    8. Verify the volume is still healthy

    FIXME: Don't need to wait for volume to rebuild and healthy before step 8.
    Volume should always be healthy even only with 2 replicas.
    """
    for host_id, client in iter(clients.items()):
        break

    replica_count = 3
    volume = create_and_check_volume(client, volume_name, replica_count)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    replica_count = 5
    volume = volume.updateReplicaCount(replicaCount=replica_count)
    volume = common.wait_for_volume_degraded(client, volume_name)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == replica_count

    old_replica_count = replica_count
    replica_count = 2
    volume = volume.updateReplicaCount(replicaCount=replica_count)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == old_replica_count

    volume.replicaRemove(name=volume.replicas[0].name)
    volume.replicaRemove(name=volume.replicas[1].name)
    volume.replicaRemove(name=volume.replicas[2].name)

    volume = common.wait_for_volume_replica_count(client,
                                                  volume_name, replica_count)
    wait_for_rebuild_complete(client, volume_name)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == replica_count

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_attach_without_frontend(clients, volume_name):  # NOQA
    """
    Test attach in maintenance mode (without frontend)

    1. Create a volume and attach to the current node with enabled frontend
    2. Check volume has `blockdev`
    3. Write `snap1_data` into volume and create snapshot `snap1`
    4. Write more random data into volume and create another anspshot
    5. Detach the volume and reattach with disabled frontend
    6. Check volume still has `blockdev` as frontend but no endpoint
    7. Revert back to `snap1`
    8. Detach and reattach the volume with enabled frontend
    9. Check volume contains data `snap1_data`
    """
    for host_id, client in iter(clients.items()):
        break

    volume = create_and_check_volume(client, volume_name)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    snap1_data = write_volume_random_data(volume)
    snap1 = create_snapshot(client, volume_name)

    write_volume_random_data(volume)
    create_snapshot(client, volume_name)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=True)
    common.wait_for_volume_healthy_no_frontend(client, volume_name)

    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    assert engine.endpoint == ""

    volume.snapshotRevert(name=snap1.name)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    check_volume_data(volume, snap1_data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest
def test_storage_class_from_backup(volume_name, pvc_name, storage_class, clients, core_api, pod_make): # NOQA
    """
    Test restore backup using StorageClass

    1. Create volume and PV/PVC/POD
    2. Write `test_data` into pod
    3. Create a snapshot and back it up. Get the backup URL
    4. Create a new StorageClass `longhorn-from-backup` and set backup URL.
    5. Use `longhorn-from-backup` to create a new PVC
    6. Wait for the volume to be created and complete the restoration.
    7. Create the pod using the PVC. Verify the data
    """
    VOLUME_SIZE = str(DEFAULT_VOLUME_SIZE * Gi)

    for _, client in iter(clients.items()):
        break

    set_random_backupstore(client)

    pv_name = pvc_name

    volume = create_and_check_volume(
        client,
        volume_name,
        size=VOLUME_SIZE
    )

    wait_for_volume_detached(client, volume_name)

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    pod_manifest = pod_make()
    pod_manifest['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    pod_name = pod_manifest['metadata']['name']
    create_and_wait_pod(core_api, pod_manifest)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data)

    volume_id = client.by_id_volume(volume_name)
    snapshot = volume_id.snapshotCreate()

    volume_id.snapshotBackup(name=snapshot.name)

    bv, b = find_backup(client, volume_name, snapshot.name)

    wait_for_backup_completion(client, volume_name, snapshot.name)

    backup_url = b.url

    storage_class['metadata']['name'] = "longhorn-from-backup"
    storage_class['parameters']['fromBackup'] = backup_url

    create_storage_class(storage_class)

    backup_pvc_name = generate_volume_name()

    backup_pvc_spec = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
                "name": backup_pvc_name,
        },
        "spec": {
                "accessModes": [
                        "ReadWriteOnce"
                ],
                "storageClassName": storage_class['metadata']['name'],
                "resources": {
                        "requests": {
                                "storage": VOLUME_SIZE
                        }
                }
        }
    }

    volume_count = len(client.list_volume())

    core_api.create_namespaced_persistent_volume_claim(
        'default',
        backup_pvc_spec
    )

    backup_volume_created = False

    for i in range(RETRY_COUNTS):
        if len(client.list_volume()) == volume_count + 1:
            backup_volume_created = True
            break
        time.sleep(RETRY_INTERVAL)

    assert backup_volume_created

    for i in range(RETRY_COUNTS):
        pvc_status = core_api.read_namespaced_persistent_volume_claim_status(
            name=backup_pvc_name,
            namespace='default'
        )

        if pvc_status.status.phase == 'Bound':
            break
        time.sleep(RETRY_INTERVAL)

    found = False
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        for volume in volumes:
            if volume.kubernetesStatus.pvcName == backup_pvc_name:
                backup_volume_name = volume.name
                found = True
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found

    wait_for_volume_restoration_completed(client, backup_volume_name)
    wait_for_volume_detached(client, backup_volume_name)

    backup_pod_manifest = pod_make(name="backup-pod")
    backup_pod_manifest['spec']['volumes'] = \
        [create_pvc_spec(backup_pvc_name)]
    backup_pod_name = backup_pod_manifest['metadata']['name']
    create_and_wait_pod(core_api, backup_pod_manifest)

    restored_data = read_volume_data(core_api, backup_pod_name)
    assert test_data == restored_data


@pytest.mark.coretest   # NOQA
def test_expansion_basic(clients, volume_name):  # NOQA
    """
    Test volume expansion using Longhorn API

    1. Create volume and attach to the current node
    2. Generate data `snap1_data` and write it to the volume
    3. Create snapshot `snap1`
    4. Expand the volume (volume will be detached, expanded, then attached)
    5. Verify the volume has been expanded
    6. Generate data `snap2_data` and write it to the volume
    7. Create snapshot `snap2`
    8. Gerneate data `snap3_data` and write it after the original size
    9. Create snapshot `snap3` and verify the `snap3_data` with location
    10. Detach and reattach the volume.
    11. Verify the volume is still expanded, and `snap3_data` remain valid
    12. Detach the volume.
    13. Reattach the volume in maintence mode
    14. Revert to `snap2` and detach.
    15. Attach the volume and check data `snap2_data`
    16. Generate `snap4_data` and write it after the original size
    17. Create snapshot `snap4` and verify `snap4_data`.
    18. Detach the volume and revert to `snap1`
    19. Validate `snap1_data`
    """
    for host_id, client in iter(clients.items()):
        break

    volume = create_and_check_volume(client, volume_name)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    snap1_data = write_volume_random_data(volume)
    snap1 = create_snapshot(client, volume_name)

    expand_attached_volume(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_block_device_size(volume, int(EXPAND_SIZE))

    snap2_data = write_volume_random_data(volume)
    snap2 = create_snapshot(client, volume_name)

    snap3_data = {
        'pos': int(SIZE),
        'content': generate_random_data(VOLUME_RWTEST_SIZE),
    }
    snap3_data = write_volume_data(volume, snap3_data)
    create_snapshot(client, volume_name)
    check_volume_data(volume, snap3_data)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_block_device_size(volume, int(EXPAND_SIZE))
    check_volume_data(volume, snap3_data)
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=True)
    volume = common.wait_for_volume_healthy_no_frontend(client, volume_name)
    engine = get_volume_engine(volume)
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    assert engine.endpoint == ""
    volume.snapshotRevert(name=snap2.name)
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_volume_data(volume, snap2_data, False)
    snap4_data = {
        'pos': int(SIZE),
        'content': generate_random_data(VOLUME_RWTEST_SIZE),
    }
    snap4_data = write_volume_data(volume, snap4_data)
    create_snapshot(client, volume_name)
    check_volume_data(volume, snap4_data)
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=lht_hostId, disableFrontend=True)
    volume = common.wait_for_volume_healthy_no_frontend(client, volume_name)
    volume.snapshotRevert(name=snap1.name)
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_volume_data(volume, snap1_data, False)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_restore_inc_with_expansion(clients, core_api, volume_name, pod):  # NOQA
    """
    Test restore from disaster recovery volume with volume expansion

    Run test against a random backupstores

    1. Create a volume and attach to the current node
    2. Generate `data0`, write to the volume, make a backup `backup0`
    3. Create three DR(standby) volumes from the backup: `dr_volume0/1/2`
    4. Wait for all three DR volumes to finish the initial restoration
    5. Verify DR volumes's `lastBackup` is `backup0`
    6. Verify snapshot/pv/pvc/change backup target are not allowed as long
    as the DR volume exists
    7. Activate standby `dr_volume0` and attach it to check the volume data
    8. Expand the original volume. Make sure the expansion is successful.
    8. Generate `data1` and write to the original volume and create `backup1`
    9. Make sure `dr_volume1`'s `lastBackup` field has been updated to
    `backup1`
    10. Activate `dr_volume1` and check data `data0` and `data1`
    11. Generate `data2` and write to the original volume after original SIZE
    12. Create `backup2`
    13. Wait for `dr_volume2` to finish expansion, show `backup2` as latest
    14. Activate `dr_volume2` and verify `data2`
    15. Detach `dr_volume2`
    16. Create PV, PVC and Pod to use `sb_volume2`, check PV/PVC/POD are good

    FIXME: Step 16 works because the disk will be treated as a unformatted disk
    """
    client = get_random_client(clients)
    lht_host_id = get_self_host_id()

    set_random_backupstore(client)

    std_volume = create_and_check_volume(client, volume_name, 2, SIZE)
    std_volume.attach(hostId=lht_host_id)
    std_volume = common.wait_for_volume_healthy(client, volume_name)

    with pytest.raises(Exception) as e:
        std_volume.activate(frontend=VOLUME_FRONTEND_BLOCKDEV)
        assert "already in active mode" in str(e.value)

    data0 = {'pos': 0, 'len': VOLUME_RWTEST_SIZE,
             'content': common.generate_random_data(VOLUME_RWTEST_SIZE)}
    bv, backup0, _, data0 = create_backup(
        client, volume_name, data0)

    dr_volume0_name = "dr-expand-0-" + volume_name
    dr_volume1_name = "dr-expand-1-" + volume_name
    dr_volume2_name = "dr-expand-2-" + volume_name
    client.create_volume(name=dr_volume0_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    client.create_volume(name=dr_volume1_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    client.create_volume(name=dr_volume2_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    common.wait_for_volume_restoration_completed(client, dr_volume0_name)
    common.wait_for_volume_restoration_completed(client, dr_volume1_name)
    common.wait_for_volume_restoration_completed(client, dr_volume2_name)

    dr_volume0 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume0_name)
    dr_volume1 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume1_name)
    dr_volume2 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume2_name)

    for i in range(RETRY_COUNTS):
        dr_volume0 = client.by_id_volume(dr_volume0_name)
        dr_volume1 = client.by_id_volume(dr_volume1_name)
        dr_volume2 = client.by_id_volume(dr_volume2_name)
        get_volume_engine(dr_volume0)
        get_volume_engine(dr_volume1)
        get_volume_engine(dr_volume2)
        if dr_volume0.initialRestorationRequired is True or \
                dr_volume1.initialRestorationRequired is True or \
                dr_volume2.initialRestorationRequired is True:
            time.sleep(RETRY_INTERVAL)
        else:
            break
    assert dr_volume0.standby is True
    assert dr_volume0.lastBackup == backup0.name
    assert dr_volume0.frontend == ""
    assert dr_volume0.initialRestorationRequired is False
    dr_engine0 = get_volume_engine(dr_volume0)
    assert dr_engine0.lastRestoredBackup == backup0.name
    assert dr_engine0.requestedBackupRestore == backup0.name
    assert dr_volume1.standby is True
    assert dr_volume1.lastBackup == backup0.name
    assert dr_volume1.frontend == ""
    assert dr_volume1.initialRestorationRequired is False
    dr_engine1 = get_volume_engine(dr_volume1)
    assert dr_engine1.lastRestoredBackup == backup0.name
    assert dr_engine1.requestedBackupRestore == backup0.name
    assert dr_volume2.standby is True
    assert dr_volume2.lastBackup == backup0.name
    assert dr_volume2.frontend == ""
    assert dr_volume2.initialRestorationRequired is False
    dr_engine2 = get_volume_engine(dr_volume2)
    assert dr_engine2.lastRestoredBackup == backup0.name
    assert dr_engine2.requestedBackupRestore == backup0.name

    dr0_snaps = dr_volume0.snapshotList()
    assert len(dr0_snaps) == 2

    activate_standby_volume(client, dr_volume0_name)
    dr_volume0 = client.by_id_volume(dr_volume0_name)
    dr_volume0.attach(hostId=lht_host_id)
    dr_volume0 = common.wait_for_volume_healthy(client, dr_volume0_name)
    check_volume_data(dr_volume0, data0, False)

    expand_attached_volume(client, volume_name)
    std_volume = client.by_id_volume(volume_name)
    check_block_device_size(std_volume, int(EXPAND_SIZE))

    data1 = {'pos': VOLUME_RWTEST_SIZE, 'len': VOLUME_RWTEST_SIZE,
             'content': common.generate_random_data(VOLUME_RWTEST_SIZE)}
    bv, backup1, _, data1 = create_backup(
        client, volume_name, data1)

    client.list_backupVolume()
    check_volume_last_backup(client, dr_volume1_name, backup1.name)
    activate_standby_volume(client, dr_volume1_name)
    dr_volume1 = client.by_id_volume(dr_volume1_name)
    dr_volume1.attach(hostId=lht_host_id)
    dr_volume1 = common.wait_for_volume_healthy(client, dr_volume1_name)
    check_volume_data(dr_volume1, data0, False)
    check_volume_data(dr_volume1, data1, False)

    data2 = {'pos': int(SIZE), 'len': VOLUME_RWTEST_SIZE,
             'content': common.generate_random_data(VOLUME_RWTEST_SIZE)}
    bv, backup2, _, data2 = create_backup(
        client, volume_name, data2)
    assert backup2.volumeSize == EXPAND_SIZE

    client.list_backupVolume()
    wait_for_dr_volume_expansion(client, dr_volume2_name, EXPAND_SIZE)
    check_volume_last_backup(client, dr_volume2_name, backup2.name)
    activate_standby_volume(client, dr_volume2_name)
    dr_volume2 = client.by_id_volume(dr_volume2_name)
    dr_volume2.attach(hostId=lht_host_id)
    dr_volume2 = common.wait_for_volume_healthy(client, dr_volume2_name)
    check_volume_data(dr_volume2, data2)

    # allocated this active volume to a pod
    dr_volume2.detach()
    dr_volume2 = common.wait_for_volume_detached(client, dr_volume2_name)

    create_pv_for_volume(client, core_api, dr_volume2, dr_volume2_name)
    create_pvc_for_volume(client, core_api, dr_volume2, dr_volume2_name)

    dr_volume2_pod_name = "pod-" + dr_volume2_name
    pod['metadata']['name'] = dr_volume2_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': dr_volume2_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    dr_volume2 = client.by_id_volume(dr_volume2_name)
    k_status = dr_volume2.kubernetesStatus
    workloads = k_status.workloadsStatus
    assert k_status.pvName == dr_volume2_name
    assert k_status.pvStatus == 'Bound'
    assert len(workloads) == 1
    for i in range(RETRY_COUNTS):
        if workloads[0].podStatus == 'Running':
            break
        time.sleep(RETRY_INTERVAL)
        dr_volume2 = client.by_id_volume(dr_volume2_name)
        k_status = dr_volume2.kubernetesStatus
        workloads = k_status.workloadsStatus
        assert len(workloads) == 1
    assert workloads[0].podName == dr_volume2_pod_name
    assert workloads[0].podStatus == 'Running'
    assert not workloads[0].workloadName
    assert not workloads[0].workloadType
    assert k_status.namespace == 'default'
    assert k_status.pvcName == dr_volume2_name
    assert not k_status.lastPVCRefAt
    assert not k_status.lastPodRefAt

    delete_and_wait_pod(core_api, dr_volume2_pod_name)
    delete_and_wait_pvc(core_api, dr_volume2_name)
    delete_and_wait_pv(core_api, dr_volume2_name)

    # cleanup
    std_volume.detach()
    dr_volume0.detach()
    dr_volume1.detach()
    std_volume = common.wait_for_volume_detached(client, volume_name)
    dr_volume0 = common.wait_for_volume_detached(client, dr_volume0_name)
    dr_volume1 = common.wait_for_volume_detached(client, dr_volume1_name)
    dr_volume2 = common.wait_for_volume_detached(client, dr_volume2_name)

    bv.backupDelete(name=backup2.name)
    bv.backupDelete(name=backup1.name)
    bv.backupDelete(name=backup0.name)

    client.delete(std_volume)
    client.delete(dr_volume0)
    client.delete(dr_volume1)
    client.delete(dr_volume2)

    wait_for_volume_delete(client, volume_name)
    wait_for_volume_delete(client, dr_volume0_name)
    wait_for_volume_delete(client, dr_volume1_name)
    wait_for_volume_delete(client, dr_volume2_name)

    volumes = client.list_volume().data
    assert len(volumes) == 0


def test_engine_image_daemonset_restart(clients, apps_api, volume_name):  # NOQA
    """
    Test restarting engine image daemonset

    1. Get the default engine image
    2. Create a volume and attach to the current node
    3. Write random data to the volume and create a snapshot
    4. Delete the engine image daemonset
    5. Engine image daemonset should be recreated
    6. In the meantime, validate the volume data to prove it's still functional
    7. Wait for the engine image to become `ready` again
    8. Check the volume data again.
    9. Write some data and create a new snapshot.
        1. Since create snapshot will use engine image binary.
    10. Check the volume data again
    """
    client = get_random_client(clients)
    default_img = common.get_default_engine_image(client)
    ds_name = "engine-image-" + default_img.name

    volume = create_and_check_volume(client, volume_name)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    volume = common.wait_for_volume_healthy(client, volume_name)
    snap1_data = write_volume_random_data(volume)
    create_snapshot(client, volume_name)

    # The engine image DaemonSet will be recreated/restarted automatically
    apps_api.delete_namespaced_daemon_set(ds_name, common.LONGHORN_NAMESPACE)

    # The Longhorn volume is still available
    # during the engine image DaemonSet restarting
    check_volume_data(volume, snap1_data)

    # Wait for the restart complete
    common.wait_for_engine_image_state(client, default_img.name, "ready")

    # Longhorn is still able to use the corresponding engine binary to
    # operate snapshot
    check_volume_data(volume, snap1_data)
    snap2_data = write_volume_random_data(volume)
    create_snapshot(client, volume_name)
    check_volume_data(volume, snap2_data)


@pytest.mark.coretest  # NOQA
def test_expansion_canceling(clients, core_api, volume_name, pod):  # NOQA
    """
    Test expansion canceling

    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Generate `test_data` and write to the pod
    3. Create an empty directory with expansion snapshot tmp meta file path
       so that the following expansion will fail
    4. Delete the pod and wait for volume detachment
    5. Try to expand the volume using Longhorn API
    6. Wait for expansion failure then use Longhorn API to cancel it
    7. Create a new pod and validate the volume content,
       then re-write random data to the pod
    8. Delete the pod and wait for volume detachment
    9. Retry expansion then verify the expansion done using Longhorn API
    10. Create a new pod
    11. Validate the volume content, then check if data writing looks fine
    12. Clean up pod, PVC, and PV
    """
    client = get_random_client(clients)

    expansion_pvc_name = "pvc-" + volume_name
    expansion_pv_name = "pv-" + volume_name
    pod_name = "pod-" + volume_name
    volume = create_and_check_volume(client, volume_name, 2, SIZE)
    create_pv_for_volume(client, core_api, volume, expansion_pv_name)
    create_pvc_for_volume(client, core_api, volume, expansion_pvc_name)
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': expansion_pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    volume = client.by_id_volume(volume_name)
    replicas = volume.replicas
    fail_replica_expansion(client, core_api,
                           volume_name, EXPAND_SIZE, replicas)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data)

    delete_and_wait_pod(core_api, pod_name)
    volume = wait_for_volume_detached(client, volume_name)

    volume.expand(size=EXPAND_SIZE)
    wait_for_expansion_failure(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.cancelExpansion()
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.state == "detached"
    assert volume.size == SIZE

    # check if the volume still works fine
    create_and_wait_pod(core_api, pod)
    resp = read_volume_data(core_api, pod_name)
    assert resp == test_data
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data)

    # retry expansion
    delete_and_wait_pod(core_api, pod_name)
    volume = wait_for_volume_detached(client, volume_name)
    volume.expand(size=EXPAND_SIZE)
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.state == "detached"
    assert volume.size == str(EXPAND_SIZE)

    create_and_wait_pod(core_api, pod)
    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert volume.size == EXPAND_SIZE
    assert volume.size == engine.size
    resp = read_volume_data(core_api, pod_name)
    assert resp == test_data
    write_pod_volume_data(core_api, pod_name, test_data)
    resp = read_volume_data(core_api, pod_name)
    assert resp == test_data

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, expansion_pvc_name)
    delete_and_wait_pv(core_api, expansion_pv_name)
