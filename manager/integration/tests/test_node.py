import common
import pytest
import os
import subprocess

from common import client  # NOQA
from common import Gi, SIZE, CONDITION_STATUS_FALSE, CONDITION_STATUS_TRUE
from common import get_self_host_id

SMALL_DISK_SIZE = (1 * 1024 * 1024)
DEFAULT_DISK_PATH = '/var/lib/rancher/longhorn/'
TEST_FILE = 'test'


def create_host_disk(client, vol_name, size, node_id):  # NOQA
    # create a single replica volume and attach it to node
    volume = create_volume(client, vol_name, size, node_id, 1)

    # prepare the disk in the host filesystem
    disk_path = common.prepare_host_disk(volume["endpoint"], volume["name"])
    return disk_path


def cleanup_host_disk(client, *args):  # NOQA
    # clean disk
    for vol_name in args:
        # umount disk
        common.cleanup_host_disk(vol_name)
        # clean volume
        cleanup_volume(client, vol_name)


def get_update_disks(disks):
    update_disk = []
    for key, disk in disks.iteritems():
        update_disk.append(disk)
    return update_disk


@pytest.mark.node  # NOQA
def test_node(client):  # NOQA
    # test node update
    nodes = client.list_node()
    assert len(nodes) > 0

    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    node = client.update(node, allowScheduling=False)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", False)
    assert not node["allowScheduling"]
    node = client.by_id_node(lht_hostId)
    assert not node["allowScheduling"]

    node = client.update(node, allowScheduling=True)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", True)
    assert node["allowScheduling"]
    node = client.by_id_node(lht_hostId)
    assert node["allowScheduling"]

    disks = node["disks"]
    # test add same disk by different mount path exception
    with pytest.raises(Exception) as e:
        disk = {"path": "/var/lib", "allowScheduling": True,
                "storageMaximum": 5*Gi, "storageReserved": 2*Gi}
        update_disk = get_update_disks(disks)
        update_disk.append(disk)
        node = node.diskUpdate(disks=update_disk)
    assert "the same file system" in str(e.value)

    # test delete disk exception
    with pytest.raises(Exception) as e:
        node.diskUpdate(disks=[])
    assert "disable the disk" in str(e.value)

    # create multiple disks for node
    node = client.by_id_node(lht_hostId)
    disks = node["disks"]
    disk_path1 = create_host_disk(client, 'vol-disk-1',
                                  SIZE, lht_hostId)
    disk1 = {"path": disk_path1, "allowScheduling": True,
             "storageMaximum": 5*Gi, "storageReserved": 2*Gi}
    disk_path2 = create_host_disk(client, 'vol-disk-2',
                                  SIZE, lht_hostId)
    disk2 = {"path": disk_path2, "allowScheduling": True}

    update_disk = get_update_disks(disks)
    # add new disk for node
    update_disk.append(disk1)
    update_disk.append(disk2)

    # save disks to node
    node = node.diskUpdate(disks=update_disk)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node["disks"]) == len(update_disk)
    node = client.by_id_node(lht_hostId)
    assert len(node["disks"]) == len(update_disk)

    # update disk
    disks = node["disks"]
    update_disk = get_update_disks(disks)
    for disk in update_disk:
        # keep default disk for other tests
        if disk["path"] == disk_path1 or disk["path"] == disk_path2:
            disk["allowScheduling"] = False
            disk["storageReserved"] = Gi
    node = node.diskUpdate(disks=update_disk)
    disks = node["disks"]
    # wait for node controller to update disk status
    for fsid, disk in disks.iteritems():
        if disk["path"] == disk_path1 or disk["path"] == disk_path2:
            common.wait_for_disk_status(client, lht_hostId, fsid,
                                        "allowScheduling", False)
            common.wait_for_disk_status(client, lht_hostId, fsid,
                                        "storageReserved", Gi)
            free, total = common.get_host_disk_size(disk_path1)
            common.wait_for_disk_status(client, lht_hostId, fsid,
                                        "storageAvailable", free)

    node = client.by_id_node(lht_hostId)
    disks = node["disks"]
    for key, disk in disks.iteritems():
        if disk["path"] == disk_path1:
            assert not disk["allowScheduling"]
            assert disk["storageReserved"] == Gi
            assert disk["storageScheduled"] == 0
            assert disk["storageMaximum"] == 5*Gi
            free, total = common.get_host_disk_size(disk_path1)
            assert disk["storageAvailable"] == free
        elif disk["path"] == disk_path2:
            assert not disk["allowScheduling"]
            assert disk["storageReserved"] == Gi
            assert disk["storageScheduled"] == 0
            free, total = common.get_host_disk_size(disk_path2)
            assert disk["storageMaximum"] == total
            assert disk["storageAvailable"] == free

    # delete other disks, just remain default disk
    update_disk = get_update_disks(disks)
    remain_disk = []
    for disk in update_disk:
        if disk["path"] != disk_path1 and disk["path"] != disk_path2:
            remain_disk.append(disk)
    node = node.diskUpdate(disks=remain_disk)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(remain_disk))
    assert len(node["disks"]) == len(remain_disk)
    # cleanup disks
    cleanup_host_disk(client, 'vol-disk-1', 'vol-disk-2')


def create_volume(client, vol_name, size, node_id, r_num):  # NOQA
    volume = client.create_volume(name=vol_name, size=size,
                                  numberOfReplicas=r_num)
    assert volume["numberOfReplicas"] == r_num
    assert volume["frontend"] == "blockdev"

    volume = common.wait_for_volume_detached(client, vol_name)
    assert len(volume["replicas"]) == r_num

    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volumeByName = client.by_id_volume(vol_name)
    assert volumeByName["name"] == volume["name"]
    assert volumeByName["size"] == volume["size"]
    assert volumeByName["numberOfReplicas"] == volume["numberOfReplicas"]
    assert volumeByName["state"] == volume["state"]
    assert volumeByName["created"] == volume["created"]

    volume.attach(hostId=node_id)
    volume = common.wait_for_volume_healthy(client, vol_name)

    return volume


def cleanup_volume(client, vol_name):  # NOQA
    volume = client.by_id_volume(vol_name)
    volume.detach()
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)


@pytest.mark.node  # NOQA
def test_replica_scheduler(client):  # NOQA
    nodes = client.list_node()
    # delete all disks on each node
    for node in nodes:
        disks = node["disks"]
        name = node["name"]
        # set allowScheduling to false
        for fsid, disk in disks.iteritems():
            disk["allowScheduling"] = False
        update_disks = get_update_disks(disks)
        node = node.diskUpdate(disks=update_disks)
        for fsid, disk in node["disks"].iteritems():
            # wait for node controller update disk status
            common.wait_for_disk_status(client, name, fsid,
                                        "allowScheduling", False)
            common.wait_for_disk_status(client, name, fsid,
                                        "storageScheduled", 0)

        node = client.by_id_node(name)
        for fsid, disk in node["disks"].iteritems():
            assert not disk["allowScheduling"]
        node = node.diskUpdate(disks=[])
        node = common.wait_for_disk_update(client, name, 0)
        assert len(node["disks"]) == 0

    # test there's no disk fit for volume
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)

    # create default disk for each node
    expect_node_disk = {}
    nodes = client.list_node()
    for node in nodes:
        default_disk = {"path": DEFAULT_DISK_PATH, "allowScheduling": True,
                        "storageMaximum": 5*Gi, "storageReserved": 3*Gi}
        node = node.diskUpdate(disks=[default_disk])
        node = common.wait_for_disk_update(client, node["name"], 1)
        assert(len(node["disks"])) == 1
        expect_node_disk[node["name"]] = node["disks"]

    # create a small size disk on current node
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    small_disk = {"path": small_disk_path, "allowScheduling": True,
                  "storageMaximum": SMALL_DISK_SIZE}
    update_disks = get_update_disks(node["disks"])
    update_disks.append(small_disk)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node["disks"]) == len(update_disks)

    unexpected_disk = {}
    for fsid, disk in node["disks"].iteritems():
        if disk["path"] == small_disk_path:
            unexpected_disk["fsid"] = fsid
            unexpected_disk["path"] = disk["path"]
            break

    # volume is too large to fill into small size disk on current node
    vol_name = common.generate_volume_name()
    volume = create_volume(client, vol_name, SIZE, lht_hostId, len(nodes))

    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node["name"])

    # check replica on current node shouldn't schedule to small disk
    for replica in volume["replicas"]:
        id = replica["hostId"]
        assert id != ""
        assert replica["running"]
        if id == lht_hostId:
            assert replica["diskID"] != unexpected_disk["fsid"]
            assert replica["dataPath"] != unexpected_disk["path"]
        node_hosts = filter(lambda x: x != id, node_hosts)
    assert len(node_hosts) == 0

    cleanup_volume(client, vol_name)

    # volume is too large to fill into any disks
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=str(4*Gi), numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # reduce StorageReserved of each default disk
    nodes = client.list_node()
    for node in nodes:
        disks = node["disks"]
        update_disks = get_update_disks(disks)
        for disk in update_disks:
            disk["storageReserved"] = 0
        node.diskUpdate(disks=update_disks)

    # check volume status
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)
    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node["name"])
    # check all replica should be scheduled to default disk
    for replica in volume["replicas"]:
        id = replica["hostId"]
        assert id != ""
        assert replica["running"]
        expect_disk = expect_node_disk[id]
        for key, disk in expect_disk.iteritems():
            assert replica["diskID"] == key
            assert disk["path"] in replica["dataPath"]
            break
        node_hosts = filter(lambda x: x != id, node_hosts)
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)

    node = client.by_id_node(lht_hostId)
    disks = node["disks"]
    disk = disks[unexpected_disk["fsid"]]
    disk["allowScheduling"] = False
    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_status(client, lht_hostId,
                                       unexpected_disk["fsid"],
                                       "allowScheduling", False)
    disks = node["disks"]
    disk = disks[unexpected_disk["fsid"]]
    assert not disk["allowScheduling"]
    disks.pop(unexpected_disk["fsid"])
    update_disks = get_update_disks(disks)
    node.diskUpdate(disks=update_disks)
    cleanup_host_disk(client, 'vol-small')


@pytest.mark.node  # NOQA
def test_node_controller(client):  # NOQA
    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    for node in nodes:
        for fsid, disk in node["disks"].iteritems():
            # wait for node controller update disk status
            common.wait_for_disk_status(client, node["name"], fsid,
                                        "storageScheduled", 0)

    # create a volume and test update StorageScheduled of each node
    vol_name = common.generate_volume_name()
    volume = create_volume(client, vol_name, str(SMALL_DISK_SIZE),
                           lht_hostId, len(nodes))
    replicas = volume["replicas"]
    for replica in replicas:
        id = replica["hostId"]
        assert id != ""
        assert replica["running"]

    # wait for node controller to update disk status
    for node in nodes:
        disks = node["disks"]
        for fsid, disk in disks.iteritems():
            common.wait_for_disk_status(client, node["name"], fsid,
                                        "storageScheduled", SMALL_DISK_SIZE)

    nodes = client.list_node()
    for node in nodes:
        disks = node["disks"]
        for replica in replicas:
            if replica["hostId"] == node["name"]:
                disk = disks[replica["diskID"]]
                assert disk["storageScheduled"] == SMALL_DISK_SIZE
                break

    # clean volumes
    cleanup_volume(client, vol_name)

    # create a disk to test storageAvailable
    node = client.by_id_node(lht_hostId)
    test_disk_path = create_host_disk(client, "vol-test", SIZE, lht_hostId)
    test_disk = {"path": test_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node["disks"])
    update_disks.append(test_disk)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node["disks"]) == len(update_disks)

    # write specified byte data into disk
    test_file_path = os.path.join(test_disk_path, TEST_FILE)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    cmd = ['dd', 'if=/dev/zero', 'of=' + test_file_path, 'bs=1M', 'count=1']
    subprocess.check_call(cmd)
    node = client.by_id_node(lht_hostId)
    disks = node["disks"]
    # wait for node controller update disk status
    expect_disk = {}
    free, total = common.get_host_disk_size(test_disk_path)
    for fsid, disk in disks.iteritems():
        if disk["path"] == test_disk_path:
            node = common.wait_for_disk_status(client, lht_hostId, fsid,
                                               "storageAvailable", free)
            expect_disk = node["disks"][fsid]
            break

    assert expect_disk["storageAvailable"] == free

    os.remove(test_file_path)
    # cleanup test disks
    node = client.by_id_node(lht_hostId)
    disks = node["disks"]
    wait_fsid = ''
    for fsid, disk in disks.iteritems():
        if disk["path"] == test_disk_path:
            wait_fsid = fsid
            disk["allowScheduling"] = False

    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_status(client, lht_hostId, wait_fsid,
                                       "allowScheduling", False)
    disks = node["disks"]
    for fsid, disk in disks.iteritems():
        if disk["path"] == test_disk_path:
            disks.pop(fsid)
            break
    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node["disks"]) == len(update_disks)
    cleanup_host_disk(client, 'vol-test')
