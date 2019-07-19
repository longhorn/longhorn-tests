import time
import common
import subprocess
import pytest

from common import clients, random_labels, volume_name  # NOQA
from common import core_api, pod   # NOQA
from common import SIZE, DEV_PATH
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


@pytest.mark.coretest   # NOQA
def test_hosts(clients):  # NOQA
    hosts = clients.itervalues().next().list_node()
    for host in hosts:
        assert host["name"] is not None
        assert host["address"] is not None

    host_id = []
    for i in range(0, len(hosts)):
        host_id.append(hosts[i]["name"])

    host0_from_i = {}
    for i in range(0, len(hosts)):
        if len(host0_from_i) == 0:
            host0_from_i = clients[host_id[0]].by_id_node(host_id[0])
        else:
            assert host0_from_i["name"] == \
                clients[host_id[i]].by_id_node(host_id[0])["name"]
            assert host0_from_i["address"] == \
                clients[host_id[i]].by_id_node(host_id[0])["address"]


@pytest.mark.coretest   # NOQA
def test_settings(clients):  # NOQA
    client = get_random_client(clients)

    setting_names = [common.SETTING_BACKUP_TARGET,
                     common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET,
                     common.SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE,
                     common.SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE,
                     common.SETTING_DEFAULT_REPLICA_COUNT]
    settings = client.list_setting()

    settingMap = {}
    for setting in settings:
        settingMap[setting["name"]] = setting

    for name in setting_names:
        assert settingMap[name] is not None
        assert settingMap[name]["definition"]["description"] is not None

    for name in setting_names:
        setting = client.by_id_setting(name)
        assert settingMap[name]["value"] == setting["value"]

        old_value = setting["value"]

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
            assert setting["value"] == "200"
            setting = client.by_id_setting(name)
            assert setting["value"] == "200"
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
            assert setting["value"] == "30"
            setting = client.by_id_setting(name)
            assert setting["value"] == "30"
        elif name == common.SETTING_BACKUP_TARGET:
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue$test")
            assert "with invalid "+name in \
                   str(e.value)
            setting = client.update(setting, value="nfs://test")
            assert setting["value"] == "nfs://test"
            setting = client.by_id_setting(name)
            assert setting["value"] == "nfs://test"
        elif name == common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET:
            setting = client.update(setting, value="testvalue")
            assert setting["value"] == "testvalue"
            setting = client.by_id_setting(name)
            assert setting["value"] == "testvalue"
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
            assert setting["value"] == "2"
            setting = client.by_id_setting(name)
            assert setting["value"] == "2"

        setting = client.update(setting, value=old_value)
        assert setting["value"] == old_value


def volume_rw_test(dev):
    assert volume_valid(dev)
    data = write_device_random_data(dev)
    check_device_data(dev, data)


@pytest.mark.coretest   # NOQA
def test_volume_basic(clients, volume_name):  # NOQA
    volume_basic_test(clients, volume_name)


def volume_basic_test(clients, volume_name, base_image=""):  # NOQA
    num_hosts = len(clients)
    num_replicas = 3

    # get a random client
    for host_id, client in clients.iteritems():
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

    def validate_volume_basic(expected, actual):
        assert actual["name"] == expected["name"]
        assert actual["size"] == expected["size"]
        assert actual["numberOfReplicas"] == expected["numberOfReplicas"]
        assert actual["frontend"] == "blockdev"
        assert actual["baseImage"] == base_image
        assert actual["state"] == expected["state"]
        assert actual["created"] == expected["created"]

    volumes = client.list_volume()
    assert len(volumes) == 1
    validate_volume_basic(volume, volumes[0])

    volumeByName = client.by_id_volume(volume_name)
    validate_volume_basic(volume, volumeByName)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volumeByName = client.by_id_volume(volume_name)
    validate_volume_basic(volume, volumeByName)
    assert get_volume_endpoint(volumeByName) == DEV_PATH + volume_name

    # validate soft anti-affinity
    hosts = {}
    for replica in volume["replicas"]:
        id = replica["hostId"]
        assert id != ""
        hosts[id] = True
    if num_hosts >= num_replicas:
        assert len(hosts) == num_replicas
    else:
        assert len(hosts) == num_hosts

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == volume["size"]
    assert volumes[0]["numberOfReplicas"] == volume["numberOfReplicas"]
    assert volumes[0]["state"] == volume["state"]
    assert volumes[0]["created"] == volume["created"]
    assert get_volume_endpoint(volumes[0]) == DEV_PATH + volume_name

    volume = client.by_id_volume(volume_name)
    assert get_volume_endpoint(volume) == DEV_PATH + volume_name

    volume_rw_test(get_volume_endpoint(volume))

    cleanup_volume(client, volume)


def test_volume_iscsi_basic(clients, volume_name):  # NOQA
    volume_iscsi_basic_test(clients, volume_name)


def volume_iscsi_basic_test(clients, volume_name, base_image=""):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = create_and_check_volume(client, volume_name, 3, SIZE, base_image,
                                     "iscsi")
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == volume["size"]
    assert volumes[0]["numberOfReplicas"] == volume["numberOfReplicas"]
    assert volumes[0]["state"] == volume["state"]
    assert volumes[0]["created"] == volume["created"]
    assert volumes[0]["frontend"] == "iscsi"
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
    snapshot_test(clients, volume_name, base_image)


def snapshot_test(clients, volume_name, base_image):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = create_and_check_volume(client, volume_name,
                                     base_image=base_image)

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    positions = {}

    snap1 = volume.snapshotCreate()

    snap2_data = write_volume_random_data(volume, positions)
    snap2 = volume.snapshotCreate()

    snap3_data = write_volume_random_data(volume, positions)
    snap3 = volume.snapshotCreate()

    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap["name"]] = snap

    assert snapMap[snap1["name"]]["name"] == snap1["name"]
    assert snapMap[snap1["name"]]["removed"] is False
    assert snapMap[snap2["name"]]["name"] == snap2["name"]
    assert snapMap[snap2["name"]]["parent"] == snap1["name"]
    assert snapMap[snap2["name"]]["removed"] is False
    assert snapMap[snap3["name"]]["name"] == snap3["name"]
    assert snapMap[snap3["name"]]["parent"] == snap2["name"]
    assert snapMap[snap3["name"]]["removed"] is False

    volume.snapshotDelete(name=snap3["name"])
    check_volume_data(volume, snap3_data)

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap["name"]] = snap

    assert snapMap[snap1["name"]]["name"] == snap1["name"]
    assert snapMap[snap1["name"]]["removed"] is False
    assert snapMap[snap2["name"]]["name"] == snap2["name"]
    assert snapMap[snap2["name"]]["parent"] == snap1["name"]
    assert snapMap[snap2["name"]]["removed"] is False
    assert snapMap[snap3["name"]]["name"] == snap3["name"]
    assert snapMap[snap3["name"]]["parent"] == snap2["name"]
    assert len(snapMap[snap3["name"]]["children"]) == 1
    assert "volume-head" in snapMap[snap3["name"]]["children"]
    assert snapMap[snap3["name"]]["removed"] is True

    snap = volume.snapshotGet(name=snap3["name"])
    assert snap["name"] == snap3["name"]
    assert snap["parent"] == snap3["parent"]
    assert len(snap3["children"]) == 1
    assert len(snap["children"]) == 1
    assert "volume-head" in snap3["children"]
    assert "volume-head" in snap["children"]
    assert snap["removed"] is True

    volume.snapshotRevert(name=snap2["name"])
    check_volume_data(volume, snap2_data)

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap["name"]] = snap

    assert snapMap[snap1["name"]]["name"] == snap1["name"]
    assert snapMap[snap1["name"]]["removed"] is False
    assert snapMap[snap2["name"]]["name"] == snap2["name"]
    assert snapMap[snap2["name"]]["parent"] == snap1["name"]
    assert "volume-head" in snapMap[snap2["name"]]["children"]
    assert snap3["name"] in snapMap[snap2["name"]]["children"]
    assert snapMap[snap2["name"]]["removed"] is False
    assert snapMap[snap3["name"]]["name"] == snap3["name"]
    assert snapMap[snap3["name"]]["parent"] == snap2["name"]
    assert len(snapMap[snap3["name"]]["children"]) == 0
    assert snapMap[snap3["name"]]["removed"] is True

    volume.snapshotDelete(name=snap1["name"])
    volume.snapshotDelete(name=snap2["name"])

    volume.snapshotPurge()
    wait_for_snapshot_purge(volume, snap1["name"], snap3["name"])

    snapshots = volume.snapshotList(volume=volume_name)
    snapMap = {}
    for snap in snapshots:
        snapMap[snap["name"]] = snap
    assert snap1["name"] not in snapMap
    assert snap3["name"] not in snapMap

    # it's the parent of volume-head, so it cannot be purged at this time
    assert snapMap[snap2["name"]]["name"] == snap2["name"]
    assert snapMap[snap2["name"]]["parent"] == ""
    assert "volume-head" in snapMap[snap2["name"]]["children"]
    assert snapMap[snap2["name"]]["removed"] is True
    check_volume_data(volume, snap2_data)

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_backup(clients, volume_name):  # NOQA
    backup_test(clients, volume_name, SIZE)


def backup_test(clients, volume_name, size, base_image=""):  # NOQA
    for host_id, client in clients.iteritems():
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
            assert setting["value"] == backupsettings[0]

            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential["value"] == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting["value"] == backupstore
            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential["value"] == ""

        backupstore_test(client, lht_hostId, volume_name, size)

    cleanup_volume(client, volume)


@pytest.mark.coretest
def test_backup_labels(clients, random_labels, volume_name):  # NOQA
    """
    Test that the proper Labels are applied when creating a Backup manually.
    """
    backup_labels_test(clients, random_labels, volume_name)


def backup_labels_test(clients, random_labels, volume_name, size=SIZE, base_image=""):  # NOQA
    for _, client in clients.iteritems():
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
            assert setting["value"] == backupsettings[0]

            credential = client.by_id_setting(
                common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential["value"] == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting["value"] == backupstore
            credential = client.by_id_setting(
                common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential["value"] == ""

        bv, b, _, _ = create_backup(client, volume_name, labels=random_labels)
        # If we're running the test with a BaseImage, check that this Label is
        # set properly.
        backup = bv.backupGet(name=b["name"])
        if base_image:
            assert backup["labels"].get(common.BASE_IMAGE_LABEL) == base_image
            # One extra Label from the BaseImage being set.
            assert len(backup["labels"]) == len(random_labels) + 1
        else:
            assert len(backup["labels"]) == len(random_labels)

    cleanup_volume(client, volume)


# test normally created volume's "InitialRestorationRequired" field
def test_restoration_required_field(clients):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volname = generate_volume_name()
    volume = client.create_volume(name=volname, size=SIZE, numberOfReplicas=3)
    volume = common.wait_for_volume_detached(client, volname)
    assert volume["initialRestorationRequired"] is False

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volname)
    assert volume["initialRestorationRequired"] is False

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volname)
    assert volume["initialRestorationRequired"] is False

    client.delete(volume)
    volume = wait_for_volume_delete(client, volname)

    volumes = client.list_volume()
    assert len(volumes) == 0


def backupstore_test(client, host_id, volname, size):
    bv, b, snap2, data = create_backup(client, volname)

    # test restore
    restoreName = generate_volume_name()
    volume = client.create_volume(name=restoreName, size=size,
                                  numberOfReplicas=2,
                                  fromBackup=b["url"])

    volume = common.wait_for_volume_restoration_completed(client, restoreName)
    volume = common.wait_for_volume_detached(client, restoreName)
    assert volume["name"] == restoreName
    assert volume["size"] == size
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["initialRestorationRequired"] is False

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, restoreName)
    check_volume_data(volume, data)
    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, restoreName)

    bv.backupDelete(name=b["name"])

    backups = bv.backupList()
    found = False
    for b in backups:
        if b["snapshotName"] == snap2["name"]:
            found = True
            break
    assert not found

    volume = wait_for_volume_status(client, volume["name"],
                                    "lastBackup", "")
    assert volume["lastBackupAt"] == ""

    client.delete(volume)

    volume = wait_for_volume_delete(client, restoreName)


@pytest.mark.coretest   # NOQA
def test_restore_inc(clients, core_api, volume_name, pod):  # NOQA
    for _, client in clients.iteritems():
        break

    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    # test backupTarget for multiple settings
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        if common.is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            setting = client.update(setting, value=backupsettings[0])
            assert setting["value"] == backupsettings[0]

            credential = client.by_id_setting(
                common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential["value"] == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting["value"] == backupstore
            credential = client.by_id_setting(
                common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential["value"] == ""

        restore_inc_test(client, core_api, volume_name, pod)


def restore_inc_test(client, core_api, volume_name, pod):  # NOQA
    std_volume = create_and_check_volume(client, volume_name, 2, SIZE)
    lht_host_id = get_self_host_id()
    std_volume.attach(hostId=lht_host_id)
    std_volume = common.wait_for_volume_healthy(client, volume_name)

    with pytest.raises(Exception) as e:
        std_volume.activate(frontend="blockdev")
        assert "already in active mode" in str(e.value)

    data0 = {'len': 4 * 1024, 'pos': 0}
    data0['content'] = common.generate_random_data(data0['len'])
    bv, backup0, _, data0 = create_backup(
        client, volume_name, data0)

    sb_volume0_name = "sb-0-" + volume_name
    sb_volume1_name = "sb-1-" + volume_name
    sb_volume2_name = "sb-2-" + volume_name
    client.create_volume(name=sb_volume0_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0['url'],
                         frontend="", standby=True)
    client.create_volume(name=sb_volume1_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0['url'],
                         frontend="", standby=True)
    client.create_volume(name=sb_volume2_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0['url'],
                         frontend="", standby=True)

    sb_volume0 = common.wait_for_volume_healthy(client, sb_volume0_name)
    sb_volume1 = common.wait_for_volume_healthy(client, sb_volume1_name)
    sb_volume2 = common.wait_for_volume_healthy(client, sb_volume2_name)

    for i in range(RETRY_COUNTS):
        sb_volume0 = client.by_id_volume(sb_volume0_name)
        sb_volume1 = client.by_id_volume(sb_volume1_name)
        sb_volume2 = client.by_id_volume(sb_volume2_name)
        sb_engine0 = get_volume_engine(sb_volume0)
        sb_engine1 = get_volume_engine(sb_volume1)
        sb_engine2 = get_volume_engine(sb_volume2)
        if sb_volume0["lastBackup"] != backup0["name"] or \
                sb_volume1["lastBackup"] != backup0["name"] or \
                sb_volume2["lastBackup"] != backup0["name"] or \
                sb_engine0["lastRestoredBackup"] != backup0["name"] or \
                sb_engine1["lastRestoredBackup"] != backup0["name"] or \
                sb_engine2["lastRestoredBackup"] != backup0["name"]:
            time.sleep(RETRY_INTERVAL)
        else:
            break
    assert sb_volume0["standby"] is True
    assert sb_volume0["lastBackup"] == backup0["name"]
    assert sb_volume0["frontend"] == ""
    assert sb_volume0["initialRestorationRequired"] is False
    sb_engine0 = get_volume_engine(sb_volume0)
    assert sb_engine0["lastRestoredBackup"] == backup0["name"]
    assert sb_engine0["requestedBackupRestore"] == backup0["name"]
    assert sb_volume1["standby"] is True
    assert sb_volume1["lastBackup"] == backup0["name"]
    assert sb_volume1["frontend"] == ""
    assert sb_volume1["initialRestorationRequired"] is False
    sb_engine1 = get_volume_engine(sb_volume1)
    assert sb_engine1["lastRestoredBackup"] == backup0["name"]
    assert sb_engine1["requestedBackupRestore"] == backup0["name"]
    assert sb_volume2["standby"] is True
    assert sb_volume2["lastBackup"] == backup0["name"]
    assert sb_volume2["frontend"] == ""
    assert sb_volume2["initialRestorationRequired"] is False
    sb_engine2 = get_volume_engine(sb_volume2)
    assert sb_engine2["lastRestoredBackup"] == backup0["name"]
    assert sb_engine2["requestedBackupRestore"] == backup0["name"]

    sb0_snaps = sb_volume0.snapshotList()
    assert len(sb0_snaps) == 2
    for s in sb0_snaps:
        if s['name'] != "volume-head":
            sb0_snap = s
    assert sb0_snaps
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotCreate()
        assert "cannot create snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotRevert(name=sb0_snap["name"])
        assert "cannot revert snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotDelete(name=sb0_snap["name"])
        assert "cannot delete snapshot for standby volume" in str(e.value)
    with pytest.raises(Exception) as e:
        sb_volume0.snapshotBackup(name=sb0_snap["name"])
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
    check_volume_last_backup(client, sb_volume1_name, backup1['name'])
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
    check_volume_last_backup(client, sb_volume2_name, backup2['name'])
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
    k_status = sb_volume2["kubernetesStatus"]
    workloads = k_status['workloadsStatus']
    assert k_status['pvName'] == sb_volume2_name
    assert k_status['pvStatus'] == 'Bound'
    assert len(workloads) == 1
    for i in range(RETRY_COUNTS):
        if workloads[0]['podStatus'] == 'Running':
            break
        time.sleep(RETRY_INTERVAL)
        sb_volume2 = client.by_id_volume(sb_volume2_name)
        k_status = sb_volume2["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert len(workloads) == 1
    assert workloads[0]['podName'] == sb_volume2_pod_name
    assert workloads[0]['podStatus'] == 'Running'
    assert not workloads[0]['workloadName']
    assert not workloads[0]['workloadType']
    assert k_status['namespace'] == 'default'
    assert k_status['pvcName'] == sb_volume2_name
    assert not k_status['lastPVCRefAt']
    assert not k_status['lastPodRefAt']

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

    bv.backupDelete(name=backup2["name"])
    bv.backupDelete(name=backup1["name"])
    bv.backupDelete(name=backup0["name"])

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
    for host_id, client in clients.iteritems():
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
    for host_id, client in clients.iteritems():
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
                assert setting["value"] == backupstore
                setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
                if "nfs" in setting["value"]:
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
    volume1_backup_volume_path = subprocess.check_output(cmd).strip()

    cmd = ["find", volume1_backup_volume_path, "-name", "volume.cfg"]
    volume1_backup_volume_cfg_path = subprocess.check_output(cmd).strip()
    cmd = ["mv", volume1_backup_volume_cfg_path,
           volume1_backup_volume_cfg_path + ".tmp"]
    subprocess.check_output(cmd)
    subprocess.check_output(["sync"])

    found1 = found2 = found3 = False
    for i in range(RETRY_COUNTS):
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv["name"] == volume1_name:
                if "error" in bv.messages:
                    assert "volume.cfg" in bv.messages["error"].lower()
                    found1 = True
            elif bv["name"] == volume2_name:
                assert not bv.messages
                found2 = True
            elif bv["name"] == volume3_name:
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
            bv1, b1 = common.find_backup(client, volume1_name, snap1["name"])
            found = True
            break
        except Exception:
            time.sleep(1)
    assert found
    bv1.backupDelete(name=b1["name"])
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups1 = bv1.backupList()
        for b in backups1:
            if b["snapshotName"] == snap1["name"]:
                found = True
                break
    assert not found

    bv2, b2 = common.find_backup(client, volume2_name, snap2["name"])
    bv2.backupDelete(name=b2["name"])
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups2 = bv2.backupList()
        for b in backups2:
            if b["snapshotName"] == snap2["name"]:
                found = True
                break
    assert not found

    bv3, b3 = common.find_backup(client, volume3_name, snap3["name"])
    bv3.backupDelete(name=b3["name"])
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        backups3 = bv3.backupList()
        for b in backups3:
            if b["snapshotName"] == snap3["name"]:
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
        assert engine["hostId"] == host_id
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
    '''
    client = get_random_client(clients)
    nodes = client.list_node()
    assert len(nodes) > 0

    for node in nodes:
        node = client.update(node, allowScheduling=False)
        node = common.wait_for_node_update(client, node["id"],
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
        node = common.wait_for_node_update(client, node["id"],
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
    client = get_random_client(clients)
    setting = client.by_id_setting(common.SETTING_DEFAULT_REPLICA_COUNT)
    old_value = setting["value"]
    setting = client.update(setting, value="5")

    volume = client.create_volume(name=volume_name, size=SIZE)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == int(setting.value)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    setting = client.update(setting, value=old_value)


@pytest.mark.coretest   # NOQA
def test_volume_update_replica_count(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    replica_count = 3
    volume = create_and_check_volume(client, volume_name, replica_count)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    replica_count = 5
    volume = volume.updateReplicaCount(replicaCount=replica_count)
    volume = common.wait_for_volume_degraded(client, volume_name)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == replica_count

    old_replica_count = replica_count
    replica_count = 2
    volume = volume.updateReplicaCount(replicaCount=replica_count)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == old_replica_count

    volume.replicaRemove(name=volume["replicas"][0]["name"])
    volume.replicaRemove(name=volume["replicas"][1]["name"])
    volume.replicaRemove(name=volume["replicas"][2]["name"])

    volume = common.wait_for_volume_replica_count(client,
                                                  volume_name, replica_count)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == replica_count

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)
