import common
import pytest
import time

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import check_device_data, write_device_random_data
from common import check_volume_data, write_volume_random_data
from common import get_self_host_id, volume_valid
from common import iscsi_login, iscsi_logout
from common import wait_for_volume_delete
from common import wait_for_snapshot_purge
from common import generate_volume_name
from common import SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE
from common import get_volume_endpoint, get_volume_engine
from common import get_random_client
from common import CONDITION_STATUS_FALSE, CONDITION_STATUS_TRUE

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

        if name == SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE:
            with pytest.raises(Exception) as e:
                client.update(setting, value="-100")
            assert "with invalid StorageOverProvisioningPercentag" in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert "with invalid StorageOverProvisioningPercentag" in \
                   str(e.value)
            setting = client.update(setting, value="200")
            assert setting["value"] == "200"
            setting = client.by_id_setting(name)
            assert setting["value"] == "200"
        elif name == SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE:
            with pytest.raises(Exception) as e:
                client.update(setting, value="300")
            assert "with invalid StorageMinimalAvailablePercentage" in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="-30")
            assert "with invalid StorageMinimalAvailablePercentage" in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert "with invalid StorageMinimalAvailablePercentage" in \
                   str(e.value)
            setting = client.update(setting, value="30")
            assert setting["value"] == "30"
            setting = client.by_id_setting(name)
            assert setting["value"] == "30"
        elif name == SETTING_BACKUP_TARGET:
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue$test")
            assert "with invalid BackupTarget" in \
                   str(e.value)
            setting = client.update(setting, value="nfs://test")
            assert setting["value"] == "nfs://test"
            setting = client.by_id_setting(name)
            assert setting["value"] == "nfs://test"
        else:
            setting = client.update(setting, value="testvalue")
            assert setting["value"] == "testvalue"
            setting = client.by_id_setting(name)
            assert setting["value"] == "testvalue"

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

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=num_replicas,
                                  baseImage=base_image)

    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == num_replicas
    assert volume["frontend"] == "blockdev"
    assert volume["baseImage"] == base_image

    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == num_replicas

    assert volume["state"] == "detached"
    assert volume["created"] != ""

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

    volume = volume.detach()

    common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_volume_iscsi_basic(clients, volume_name):  # NOQA
    volume_iscsi_basic_test(clients, volume_name)


def volume_iscsi_basic_test(clients, volume_name, base_image=""):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3, frontend="iscsi",
                                  baseImage=base_image)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 3
    assert volume["frontend"] == "iscsi"
    assert volume["baseImage"] == base_image

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
def test_snapshot(clients, volume_name, base_image=""):  # NOQA
    snapshot_test(clients, volume_name, base_image)


def snapshot_test(clients, volume_name, base_image):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2, baseImage=base_image)

    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["baseImage"] == base_image

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

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.coretest   # NOQA
def test_backup(clients, volume_name):  # NOQA
    backup_test(clients, volume_name, SIZE)


def backup_test(clients, volume_name, size, base_image=""):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=size,
                                  numberOfReplicas=2, baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == size
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["baseImage"] == base_image

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

        backupstore_test(client, lht_hostId, volume_name, size)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def find_backup(client, vol_name, snap_name):
    found = False
    for i in range(100):
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv["name"] == vol_name:
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
            if b["snapshotName"] == snap_name:
                found = True
                break
        if found:
            break
        time.sleep(1)
    assert found

    return bv, b


def backupstore_test(client, host_id, volname, size):
    volume = client.by_id_volume(volname)
    volume.snapshotCreate()
    data = write_volume_random_data(volume)
    snap2 = volume.snapshotCreate()
    volume.snapshotCreate()

    volume.snapshotBackup(name=snap2["name"])

    bv, b = find_backup(client, volname, snap2["name"])

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
    volume = client.create_volume(name=restoreName, size=size,
                                  numberOfReplicas=2,
                                  fromBackup=b["url"])
    volume = common.wait_for_volume_detached(client, restoreName)
    assert volume["name"] == restoreName
    assert volume["size"] == size
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, restoreName)
    check_volume_data(volume, data)
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
