import pytest
import time
import common

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH, VOLUME_RWTEST_SIZE
from common import get_self_host_id
from common import volume_read, volume_write
from common import volume_valid
from common import iscsi_login, iscsi_logout
from common import wait_for_volume_delete
from common import wait_for_snapshot_purge
from common import generate_volume_name
from common import generate_random_data
from common import generate_random_pos
from common import SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE
from common import get_volume_endpoint, get_volume_engine

SETTING_BACKUP_TARGET = "backup-target"
SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"

@pytest.mark.coretest   # NOQA
def test_hosts_and_settings(clients):  # NOQA
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

    client = clients[host_id[0]]

    setting_names = [SETTING_BACKUP_TARGET,
                     SETTING_BACKUP_TARGET_CREDENTIAL_SECRET,
                     SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE,
                     SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE]
    settings = client.list_setting()
    # Skip DefaultEngineImage option
    # since they have side affect
    assert len(settings) == len(setting_names) + 1

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

        setting = client.update(setting, value="testvalue")
        assert setting["value"] == "testvalue"
        setting = client.by_id_setting(name)
        assert setting["value"] == "testvalue"

        setting = client.update(setting, value=old_value)
        assert setting["value"] == old_value


def volume_rw_test(dev):
    assert volume_valid(dev)
    w_data = generate_random_data(VOLUME_RWTEST_SIZE)
    l_data = len(w_data)
    spos_data = generate_random_pos(VOLUME_RWTEST_SIZE)
    common.dev_write(dev, spos_data, w_data)
    r_data = common.dev_read(dev, spos_data, l_data)
    assert r_data == w_data


@pytest.mark.coretest   # NOQA
def test_volume_basic(clients, volume_name):  # NOQA
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

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 3
    assert volume["frontend"] == "blockdev"

    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == 3

    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == volume["size"]
    assert volumes[0]["numberOfReplicas"] == volume["numberOfReplicas"]
    assert volumes[0]["state"] == volume["state"]
    assert volumes[0]["created"] == volume["created"]

    volumeByName = client.by_id_volume(volume_name)
    assert volumeByName["name"] == volume["name"]
    assert volumeByName["size"] == volume["size"]
    assert volumeByName["numberOfReplicas"] == volume["numberOfReplicas"]
    assert volumeByName["state"] == volume["state"]
    assert volumeByName["created"] == volume["created"]

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # soft anti-affinity should work, assume we have 3 nodes or more
    hosts = {}
    for replica in volume["replicas"]:
        id = replica["hostId"]
        assert id != ""
        assert id not in hosts
        hosts[id] = True
    assert len(hosts) == 3

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

    volume = volume.detach()

    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_volume_iscsi_basic(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3, frontend="iscsi")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 3
    assert volume["frontend"] == "iscsi"

    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == 3

    assert volume["state"] == "detached"
    assert volume["created"] != ""

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

    volume = volume.detach()

    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.coretest   # NOQA
def test_snapshot(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)

    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    snapshot_test(client, volume_name)
    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def snapshot_test(client, volname):
    volume = client.by_id_volume(volname)
    vol_rwsize = VOLUME_RWTEST_SIZE
    positions = {}

    snap1 = volume.snapshotCreate()

    snap2_pos = generate_random_pos(vol_rwsize, positions)
    snap2_wdata = generate_random_data(vol_rwsize)
    volume_write(volume, snap2_pos, snap2_wdata)
    snap2 = volume.snapshotCreate()

    snap3_pos = generate_random_pos(vol_rwsize, positions)
    snap3_wdata = generate_random_data(vol_rwsize)
    volume_write(volume, snap3_pos, snap3_wdata)
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
    snap3_rdata = volume_read(volume, snap3_pos,
                              len(snap3_wdata))
    assert snap3_rdata == snap3_wdata

    snapshots = volume.snapshotList(volume=volname)
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
    snap2_rdata = volume_read(volume, snap2_pos,
                              len(snap2_wdata))
    assert snap2_rdata == snap2_wdata

    snapshots = volume.snapshotList(volume=volname)
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

    snapshots = volume.snapshotList(volume=volname)
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
    snap2_rdata = volume_read(volume, snap2_pos,
                              len(snap2_wdata))
    assert snap2_rdata == snap2_wdata


@pytest.mark.coretest   # NOQA
def test_backup(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    # test backupTarget for multiple settings
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        if is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            setting = client.update(setting, value=backupsettings[0])
            assert setting["value"] == backupsettings[0]

            credential = client.by_id_setting(
                    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential["value"] == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting["value"] == backupstore
            credential = client.by_id_setting(
                    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential["value"] == ""

        backup_test(client, lht_hostId, volume_name)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def backup_test(client, host_id, volname):
    volume = client.by_id_volume(volname)
    volume.snapshotCreate()
    w_data = generate_random_data(VOLUME_RWTEST_SIZE)
    start_pos = generate_random_pos(VOLUME_RWTEST_SIZE)
    l_data = volume_write(volume, start_pos, w_data)
    snap2 = volume.snapshotCreate()
    volume.snapshotCreate()

    volume.snapshotBackup(name=snap2["name"])

    found = False
    for i in range(100):
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv["name"] == volname:
                found = True
                break
        if found:
            break
        time.sleep(1)
    assert found

    found = False
    for i in range(20):
        backups = bv.backupList()
        for b in backups:
            if b["snapshotName"] == snap2["name"]:
                found = True
                break
        if found:
            break
        time.sleep(1)
    assert found

    new_b = bv.backupGet(name=b["name"])
    assert new_b["name"] == b["name"]
    assert new_b["url"] == b["url"]
    assert new_b["snapshotName"] == b["snapshotName"]
    assert new_b["snapshotCreated"] == b["snapshotCreated"]
    assert new_b["created"] == b["created"]
    assert new_b["volumeName"] == b["volumeName"]
    assert new_b["volumeSize"] == b["volumeSize"]
    assert new_b["volumeCreated"] == b["volumeCreated"]

    # test restore
    restoreName = generate_volume_name()
    volume = client.create_volume(name=restoreName, size=SIZE,
                                  numberOfReplicas=2,
                                  fromBackup=b["url"])
    volume = common.wait_for_volume_detached(client, restoreName)
    assert volume["name"] == restoreName
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, restoreName)
    r_data = volume_read(volume, start_pos, l_data)
    assert r_data == w_data
    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, restoreName)
    client.delete(volume)

    volume = wait_for_volume_delete(client, restoreName)

    bv.backupDelete(name=b["name"])

    backups = bv.backupList()
    found = False
    for b in backups:
        if b["snapshotName"] == snap2["name"]:
            found = True
            break
    assert not found


def get_random_client(clients): # NOQA
    for host_id, client in clients.iteritems():
        break
    return client


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


def is_backupTarget_s3(s):
    return s.startswith("s3://")
