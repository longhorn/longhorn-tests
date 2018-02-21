import pytest
import time
import common

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import wait_for_volume_state, wait_for_volume_delete
from common import wait_for_snapshot_purge
from common import generate_volume_name


def test_hosts_and_settings(clients):  # NOQA
    hosts = clients.itervalues().next().list_host()
    for host in hosts:
        assert host["uuid"] is not None
        assert host["address"] is not None

    host_id = []
    for i in range(0, len(hosts)):
        host_id.append(hosts[i]["uuid"])

    host0_from_i = {}
    for i in range(0, len(hosts)):
        if len(host0_from_i) == 0:
            host0_from_i = clients[host_id[0]].by_id_host(host_id[0])
        else:
            assert host0_from_i["uuid"] == \
                clients[host_id[i]].by_id_host(host_id[0])["uuid"]
            assert host0_from_i["address"] == \
                clients[host_id[i]].by_id_host(host_id[0])["address"]

    client = clients[host_id[0]]

    setting_names = ["backupTarget"]
    settings = client.list_setting()
    assert len(settings) == len(setting_names)

    settingMap = {}
    for setting in settings:
        settingMap[setting["name"]] = setting

    for name in setting_names:
        assert settingMap[name] is not None

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


def test_volume_basic(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    with pytest.raises(Exception):
        volume = client.create_volume(name="wrong_volume-name-1.0", size=SIZE,
                                      numberOfReplicas=2)
        volume = client.create_volume(name="wrong_volume-name", size=SIZE,
                                      numberOfReplicas=2)

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 3

    volume = wait_for_volume_state(client, volume_name, "detached")
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

    volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

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
    assert volumes[0]["endpoint"] == DEV_PATH + volume_name

    volume = client.by_id_volume(volume_name)
    assert volume["endpoint"] == DEV_PATH + volume_name

    volume = volume.detach()

    wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.skip(reason="will rewrite later")  # NOQA
def test_recurring_snapshot(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")

    snap2s = {"name": "snap2s", "cron": "@every 2s",
              "task": "snapshot", "retain": 3}
    snap3s = {"name": "snap3s", "cron": "@every 3s",
              "task": "snapshot", "retain": 2}
    volume.recurringUpdate(jobs=[snap2s, snap3s])

    time.sleep(0.1)
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    time.sleep(10)

    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    assert count == 5

    snap4s = {"name": "snap4s", "cron": "@every 4s",
              "task": "snapshot", "retain": 2}
    volume.recurringUpdate(jobs=[snap2s, snap4s])

    time.sleep(10)

    snapshots = volume.snapshotList()
    count = 0
    for snapshot in snapshots:
        if snapshot["removed"] is False:
            count += 1
    assert count == 7

    volume = volume.detach()

    wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)

    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_snapshot(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)

    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    snapshot_test(client, volume_name)
    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def snapshot_test(client, volname):
    volume = client.by_id_volume(volname)

    snap1 = volume.snapshotCreate()
    snap2 = volume.snapshotCreate()
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
    assert snapMap[snap3["name"]]["children"] == ["volume-head"]
    assert snapMap[snap3["name"]]["removed"] is True

    snap = volume.snapshotGet(name=snap3["name"])
    assert snap["name"] == snap3["name"]
    assert snap["parent"] == snap3["parent"]
    assert snap["children"] == snap3["children"]
    assert snap["removed"] is True

    volume.snapshotRevert(name=snap2["name"])

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
    assert snapMap[snap3["name"]]["children"] == []
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


def test_backup(clients, volume_name):  # NOQA
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    backup_test(client, host_id, volume_name)
    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    volume = wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def backup_test(client, host_id, volname):
    volume = client.by_id_volume(volname)

    setting = client.by_id_setting("backupTarget")
    setting = client.update(setting, value=common.get_backupstore_url())
    assert setting["value"] == common.get_backupstore_url()

    volume.snapshotCreate()
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
    volume = wait_for_volume_state(client, restoreName, "detached")
    assert volume["name"] == restoreName
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, restoreName, "healthy")
    volume = volume.detach()
    volume = wait_for_volume_state(client, restoreName, "detached")
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


def test_volume_multinode(clients, volume_name):  # NOQA
    hosts = clients.keys()

    volume = get_random_client(clients).create_volume(name=volume_name,
                                                      size=SIZE,
                                                      numberOfReplicas=2)
    volume = wait_for_volume_state(get_random_client(clients),
                                   volume_name, "detached")

    for host_id in hosts:
        volume = volume.attach(hostId=host_id)
        volume = wait_for_volume_state(get_random_client(clients),
                                       volume_name, "healthy")
        assert volume["state"] == "healthy"
        assert volume["controller"]["hostId"] == host_id
        volume = volume.detach()
        volume = wait_for_volume_state(get_random_client(clients),
                                       volume_name, "detached")

    get_random_client(clients).delete(volume)
    wait_for_volume_delete(get_random_client(clients), volume_name)

    volumes = get_random_client(clients).list_volume()
    assert len(volumes) == 0
