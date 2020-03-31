import common
import pytest
import os
import subprocess
import time

from random import choice
from string import ascii_lowercase, digits

from common import core_api, client  # NOQA
from common import Gi, SIZE, CONDITION_STATUS_FALSE, \
    CONDITION_STATUS_TRUE, DEFAULT_DISK_PATH, DIRECTORY_PATH, \
    DISK_CONDITION_SCHEDULABLE, DISK_CONDITION_READY
from common import get_core_api_client, get_longhorn_api_client, \
    get_self_host_id
from common import SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE, \
    SETTING_DEFAULT_DATA_PATH, \
    SETTING_CREATE_DEFAULT_DISK_LABELED_NODES, \
    DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    DEFAULT_REPLICA_DIRECTORY
from common import get_volume_endpoint
from common import get_update_disks
from common import wait_for_disk_status, wait_for_disk_update, \
    wait_for_disk_conditions, wait_for_node_tag_update, \
    cleanup_node_disks
from common import exec_nsenter
from common import wait_for_replica_directory

CREATE_DEFAULT_DISK_LABEL = "node.longhorn.io/create-default-disk"
CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG = "config"
DEFAULT_DISK_CONFIG_ANNOTATION = "node.longhorn.io/default-disks-config"
DEFAULT_NODE_TAG_ANNOTATION = "node.longhorn.io/default-node-tags"
SMALL_DISK_SIZE = (1 * 1024 * 1024)
TEST_FILE = 'test'
NODE_UPDATE_WAIT_INTERVAL = 2


@pytest.fixture
def random_disk_path():
    return "/var/lib/longhorn-" + "".join(choice(ascii_lowercase + digits)
                                          for _ in range(6))


@pytest.yield_fixture
def reset_default_disk_label():
    k8sapi = get_core_api_client()
    lhapi = get_longhorn_api_client()
    nodes = lhapi.list_node()
    for node in nodes:
        k8sapi.patch_node(node.id, {
            "metadata": {
                "labels": {
                    CREATE_DEFAULT_DISK_LABEL: None
                }
            }
        })

    yield

    k8sapi = get_core_api_client()
    lhapi = get_longhorn_api_client()
    nodes = lhapi.list_node()
    for node in nodes:
        k8sapi.patch_node(node.id, {
            "metadata": {
                "labels": {
                    CREATE_DEFAULT_DISK_LABEL: None
                }
            }
        })


@pytest.yield_fixture
def reset_disk_and_tag_annotations():
    k8sapi = get_core_api_client()
    lhapi = get_longhorn_api_client()
    nodes = lhapi.list_node()
    for node in nodes:
        k8sapi.patch_node(node.id, {
            "metadata": {
                "annotations": {
                    DEFAULT_DISK_CONFIG_ANNOTATION: None,
                    DEFAULT_NODE_TAG_ANNOTATION: None,
                }
            }
        })

    yield

    k8sapi = get_core_api_client()
    lhapi = get_longhorn_api_client()
    nodes = lhapi.list_node()
    for node in nodes:
        k8sapi.patch_node(node.id, {
            "metadata": {
                "annotations": {
                    DEFAULT_DISK_CONFIG_ANNOTATION: None,
                    DEFAULT_NODE_TAG_ANNOTATION: None,
                }
            }
        })


@pytest.yield_fixture
def reset_disk_settings():
    api = get_longhorn_api_client()
    setting = api.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    api.update(setting, value="false")
    setting = api.by_id_setting(SETTING_DEFAULT_DATA_PATH)
    api.update(setting, value=DEFAULT_DISK_PATH)

    yield

    api = get_longhorn_api_client()
    setting = api.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    api.update(setting, value="false")
    setting = api.by_id_setting(SETTING_DEFAULT_DATA_PATH)
    api.update(setting, value=DEFAULT_DISK_PATH)


def create_host_disk(client, vol_name, size, node_id):  # NOQA
    # create a single replica volume and attach it to node
    volume = create_volume(client, vol_name, size, node_id, 1)

    # prepare the disk in the host filesystem
    disk_path = common.prepare_host_disk(get_volume_endpoint(volume),
                                         volume.name)
    return disk_path


def cleanup_host_disk(client, *args):  # NOQA
    # clean disk
    for vol_name in args:
        # umount disk
        common.cleanup_host_disk(vol_name)
        # clean volume
        cleanup_volume(client, vol_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
def test_update_node(client):  # NOQA
    # test node update
    nodes = client.list_node()
    assert len(nodes) > 0

    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    node = client.update(node, allowScheduling=False)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", False)
    assert not node.allowScheduling
    node = client.by_id_node(lht_hostId)
    assert not node.allowScheduling

    node = client.update(node, allowScheduling=True)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", True)
    assert node.allowScheduling
    node = client.by_id_node(lht_hostId)
    assert node.allowScheduling


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_disk_update(client):  # NOQA
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    # test add same disk by different mount path exception
    with pytest.raises(Exception) as e:
        disk = {"path": "/var/lib", "allowScheduling": True,
                "storageReserved": 2 * Gi}
        update_disk = get_update_disks(disks)
        update_disk.append(disk)
        node = node.diskUpdate(disks=update_disk)
    assert "the same file system" in str(e.value)

    # test delete disk exception
    with pytest.raises(Exception) as e:
        node.diskUpdate(disks=[])
    assert "disable the disk" in str(e.value)

    # test storageReserved invalid exception
    with pytest.raises(Exception) as e:
        for fsid, disk in iter(disks.items()):
            disk.storageReserved = disk.storageMaximum + 1*Gi
        update_disk = get_update_disks(disks)
        node.diskUpdate(disks=update_disk)
    assert "storageReserved setting of disk" in str(e.value)

    # create multiple disks for node
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk_path1 = create_host_disk(client, 'vol-disk-1',
                                  str(Gi), lht_hostId)
    disk1 = {"path": disk_path1, "allowScheduling": True}
    disk_path2 = create_host_disk(client, 'vol-disk-2',
                                  str(Gi), lht_hostId)
    disk2 = {"path": disk_path2, "allowScheduling": True}

    update_disk = get_update_disks(disks)
    # add new disk for node
    update_disk.append(disk1)
    update_disk.append(disk2)

    # save disks to node
    node = node.diskUpdate(disks=update_disk)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node.disks) == len(update_disk)
    node = client.by_id_node(lht_hostId)
    assert len(node.disks) == len(update_disk)

    # update disk
    disks = node.disks
    update_disk = get_update_disks(disks)
    for disk in update_disk:
        # keep default disk for other tests
        if disk.path == disk_path1 or disk.path == disk_path2:
            disk.allowScheduling = False
            disk.storageReserved = SMALL_DISK_SIZE
    node = node.diskUpdate(disks=update_disk)
    disks = node.disks
    # wait for node controller to update disk status
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1 or disk.path == disk_path2:
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "allowScheduling", False)
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "storageReserved", SMALL_DISK_SIZE)
            free, total = common.get_host_disk_size(disk_path1)
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "storageAvailable", free)

    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for key, disk in iter(disks.items()):
        if disk.path == disk_path1:
            assert not disk.allowScheduling
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == 0
            free, total = common.get_host_disk_size(disk_path1)
            assert disk.storageMaximum == total
            assert disk.storageAvailable == free
        elif disk.path == disk_path2:
            assert not disk.allowScheduling
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == 0
            free, total = common.get_host_disk_size(disk_path2)
            assert disk.storageMaximum == total
            assert disk.storageAvailable == free

    # delete other disks, just remain default disk
    update_disk = get_update_disks(disks)
    remain_disk = []
    for disk in update_disk:
        if disk.path != disk_path1 and disk.path != disk_path2:
            remain_disk.append(disk)
    node = node.diskUpdate(disks=remain_disk)
    node = wait_for_disk_update(client, lht_hostId,
                                len(remain_disk))
    assert len(node.disks) == len(remain_disk)
    # cleanup disks
    cleanup_host_disk(client, 'vol-disk-1', 'vol-disk-2')


def create_volume(client, vol_name, size, node_id, r_num):  # NOQA
    volume = client.create_volume(name=vol_name, size=size,
                                  numberOfReplicas=r_num)
    assert volume.numberOfReplicas == r_num
    assert volume.frontend == "blockdev"

    volume = common.wait_for_volume_detached(client, vol_name)
    assert len(volume.replicas) == r_num

    assert volume.state == "detached"
    assert volume.created != ""

    volumeByName = client.by_id_volume(vol_name)
    assert volumeByName.name == volume.name
    assert volumeByName.size == volume.size
    assert volumeByName.numberOfReplicas == volume.numberOfReplicas
    assert volumeByName.state == volume.state
    assert volumeByName.created == volume.created

    volume.attach(hostId=node_id)
    volume = common.wait_for_volume_healthy(client, vol_name)

    return volume


def cleanup_volume(client, vol_name):  # NOQA
    volume = client.by_id_volume(vol_name)
    volume.detach()
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
def test_replica_scheduler_no_disks(client):  # NOQA
    nodes = client.list_node()
    # delete all disks on each node
    for node in nodes:
        disks = node.disks
        name = node.name
        # set allowScheduling to false
        for fsid, disk in iter(disks.items()):
            disk.allowScheduling = False
        update_disks = get_update_disks(disks)
        node = node.diskUpdate(disks=update_disks)
        for fsid, disk in iter(node.disks.items()):
            # wait for node controller update disk status
            wait_for_disk_status(client, name, fsid,
                                 "allowScheduling", False)
            wait_for_disk_status(client, name, fsid,
                                 "storageScheduled", 0)

        node = client.by_id_node(name)
        for fsid, disk in iter(node.disks.items()):
            assert not disk.allowScheduling
        node = node.diskUpdate(disks=[])
        node = common.wait_for_disk_update(client, name, 0)
        assert len(node.disks) == 0

    # test there's no disk fit for volume
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)


@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_replica_scheduler_large_volume_fit_small_disk(client):  # NOQA
    nodes = client.list_node()
    # create a small size disk on current node
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    small_disk = {"path": small_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks.append(small_disk)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)

    unexpected_disk = {}
    for fsid, disk in iter(node.disks.items()):
        if disk.path == small_disk_path:
            unexpected_disk["fsid"] = fsid
            unexpected_disk["path"] = disk["path"]
            break

    # volume is too large to fill into small size disk on current node
    vol_name = common.generate_volume_name()
    volume = create_volume(client,
                           vol_name,
                           str(Gi),
                           lht_hostId,
                           len(nodes))

    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)

    # check replica on current node shouldn't schedule to small disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        if id == lht_hostId:
            assert replica.diskID != unexpected_disk["fsid"]
            assert replica.dataPath != unexpected_disk["path"]
        node_hosts = list(filter(lambda x: x != id, node_hosts))

    assert len(node_hosts) == 0

    cleanup_volume(client, vol_name)

    # cleanup test disks
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk = disks[unexpected_disk["fsid"]]
    disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_status(client, lht_hostId,
                                unexpected_disk["fsid"],
                                "allowScheduling", False)
    disks = node.disks
    disk = disks[unexpected_disk["fsid"]]
    assert not disk.allowScheduling
    disks.pop(unexpected_disk["fsid"])
    update_disks = get_update_disks(disks)
    node.diskUpdate(disks=update_disks)
    cleanup_host_disk(client, 'vol-small')


@pytest.mark.node  # NOQA
def test_replica_scheduler_too_large_volume_fit_any_disks(client):  # NOQA
    nodes = client.list_node()
    lht_hostId = get_self_host_id()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_disk.fsid = fsid
                expect_node_disk[node.name] = expect_disk
            disk.storageReserved = disk.storageMaximum
        update_disks = get_update_disks(disks)
        node.diskUpdate(disks=update_disks)

    # volume is too large to fill into any disks
    volume_size = 4 * Gi
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=str(volume_size),
                         numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # Reduce StorageReserved of each default disk so that each node can fit
    # only one replica.
    needed_for_scheduling = int(
        volume_size * 1.5 * 100 /
        int(DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE))
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        update_disks = get_update_disks(disks)
        for disk in update_disks:
            disk.storageReserved = \
                disk.storageMaximum - needed_for_scheduling
        node = node.diskUpdate(disks=update_disks)
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_status(client, node.name,
                                 fsid, "storageReserved",
                                 disk.storageMaximum-needed_for_scheduling)

    # check volume status
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)
    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)
    # check all replica should be scheduled to default disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        expect_disk = expect_node_disk[id]
        assert replica.diskID == expect_disk.fsid
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)


@pytest.mark.node  # NOQA
def test_replica_scheduler_update_over_provisioning(client):  # NOQA
    nodes = client.list_node()
    lht_hostId = get_self_host_id()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_disk.fsid = fsid
                expect_node_disk[node.name] = expect_disk

    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value

    # set storage over provisioning percentage to 0
    # to test all replica couldn't be scheduled
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="0")
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    # check volume status
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)

    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)
    # check all replica should be scheduled to default disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        expect_disk = expect_node_disk[id]
        assert replica.diskID == expect_disk.fsid
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)
    client.update(over_provisioning_setting,
                  value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_exceed_over_provisioning(client):  # NOQA
    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value
    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    # test exceed over provisioning limit couldn't be scheduled
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            disk.storageReserved = \
                disk.storageMaximum - 1*Gi
        update_disks = get_update_disks(disks)
        node = node.diskUpdate(disks=update_disks)
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_status(client, node.name,
                                 fsid, "storageReserved",
                                 disk.storageMaximum - 1*Gi)

    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=str(2*Gi),
                                  numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)
    client.update(over_provisioning_setting, value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_just_under_over_provisioning(client):  # NOQA
    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value
    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    expect_node_disk = {}
    max_size_array = []
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_disk.fsid = fsid
                expect_node_disk[node.name] = expect_disk
                max_size_array.append(disk.storageMaximum)
            disk.storageReserved = 0
            update_disks = get_update_disks(disks)
            node = node.diskUpdate(disks=update_disks)
            disks = node.disks
            for fsid, disk in iter(disks.items()):
                wait_for_disk_status(client, node.name,
                                     fsid, "storageReserved", 0)

    max_size = min(max_size_array)
    # test just under over provisioning limit could be scheduled
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=str(max_size),
                                  numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)
    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)
    # check all replica should be scheduled to default disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        expect_disk = expect_node_disk[id]
        assert replica.diskID == expect_disk.fsid
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)
    client.update(over_provisioning_setting, value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_update_minimal_available(client):  # NOQA
    minimal_available_setting = client.by_id_setting(
        SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    old_minimal_setting = minimal_available_setting.value

    nodes = client.list_node()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_disk.fsid = fsid
                expect_node_disk[node.name] = expect_disk

    # set storage minimal available percentage to 100
    # to test all replica couldn't be scheduled
    minimal_available_setting = client.update(minimal_available_setting,
                                              value="100")
    # wait for disks state
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_conditions(client, node.name,
                                     fsid, DISK_CONDITION_SCHEDULABLE,
                                     CONDITION_STATUS_FALSE)

    lht_hostId = get_self_host_id()
    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # set storage minimal available percentage to default value(10)
    minimal_available_setting = client.update(minimal_available_setting,
                                              value=old_minimal_setting)
    # wait for disks state
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_conditions(client, node.name,
                                     fsid, DISK_CONDITION_SCHEDULABLE,
                                     CONDITION_STATUS_TRUE)
    # check volume status
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)
    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)
    # check all replica should be scheduled to default disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        expect_disk = expect_node_disk[id]
        assert replica.diskID == expect_disk.fsid
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)


@pytest.mark.node  # NOQA
def test_node_controller_sync_storage_scheduled(client):  # NOQA
    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    for node in nodes:
        for fsid, disk in iter(node.disks.items()):
            # wait for node controller update disk status
            wait_for_disk_status(client, node.name, fsid,
                                 "storageScheduled", 0)

    # create a volume and test update StorageScheduled of each node
    vol_name = common.generate_volume_name()
    volume = create_volume(client, vol_name, str(SMALL_DISK_SIZE),
                           lht_hostId, len(nodes))
    replicas = volume.replicas
    for replica in replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running

    # wait for node controller to update disk status
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_status(client, node.name, fsid,
                                 "storageScheduled", SMALL_DISK_SIZE)

    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for replica in replicas:
            if replica.hostId == node.name:
                disk = disks[replica["diskID"]]
                conditions = disk.conditions
                assert disk.storageScheduled == SMALL_DISK_SIZE
                assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                    CONDITION_STATUS_TRUE
                break

    # clean volumes
    cleanup_volume(client, vol_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_controller_sync_storage_available(client):  # NOQA
    lht_hostId = get_self_host_id()
    # create a disk to test storageAvailable
    node = client.by_id_node(lht_hostId)
    test_disk_path = create_host_disk(client, "vol-test", SIZE, lht_hostId)
    test_disk = {"path": test_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks.append(test_disk)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node.disks) == len(update_disks)

    # write specified byte data into disk
    test_file_path = os.path.join(test_disk_path, TEST_FILE)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    cmd = ['dd', 'if=/dev/zero', 'of=' + test_file_path, 'bs=1M', 'count=1']
    subprocess.check_call(cmd)
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    # wait for node controller update disk status
    expect_disk = {}
    free, total = common.get_host_disk_size(test_disk_path)
    for fsid, disk in iter(disks.items()):
        if disk.path == test_disk_path:
            node = wait_for_disk_status(client, lht_hostId, fsid,
                                        "storageAvailable", free)
            expect_disk = node.disks[fsid]
            break

    assert expect_disk.storageAvailable == free

    os.remove(test_file_path)
    # cleanup test disks
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    wait_fsid = ''
    for fsid, disk in iter(disks.items()):
        if disk.path == test_disk_path:
            wait_fsid = fsid
            disk.allowScheduling = False

    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_status(client, lht_hostId, wait_fsid,
                                "allowScheduling", False)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == test_disk_path:
            disks.pop(fsid)
            break
    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node.disks) == len(update_disks)
    cleanup_host_disk(client, 'vol-test')


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
def test_node_controller_sync_disk_state(client):  # NOQA
    # update StorageMinimalAvailablePercentage to test Disk State
    setting = client.by_id_setting(
        SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    old_minimal_available_percentage = setting.value
    setting = client.update(setting, value="100")
    assert setting.value == "100"
    nodes = client.list_node()
    # wait for node controller to update disk state
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_conditions(client, node.name,
                                     fsid, DISK_CONDITION_SCHEDULABLE,
                                     CONDITION_STATUS_FALSE)

    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_FALSE

    setting = client.update(setting, value=old_minimal_available_percentage)
    assert setting.value == old_minimal_available_percentage
    # wait for node controller to update disk state
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            wait_for_disk_conditions(client, node.name,
                                     fsid, DISK_CONDITION_SCHEDULABLE,
                                     CONDITION_STATUS_TRUE)

    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_TRUE


@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_delete_umount_disks(client):  # NOQA
    # create test disks for node
    disk_volume_name = 'vol-disk-1'
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk_path1 = create_host_disk(client, disk_volume_name,
                                  str(Gi), lht_hostId)
    disk1 = {"path": disk_path1, "allowScheduling": True,
             "storageReserved": SMALL_DISK_SIZE}

    update_disk = get_update_disks(disks)
    for disk in update_disk:
        disk.allowScheduling = False
    # add new disk for node
    update_disk.append(disk1)
    # save disks to node
    node = node.diskUpdate(disks=update_disk)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node.disks) == len(update_disk)
    node = client.by_id_node(lht_hostId)
    assert len(node.disks) == len(update_disk)

    disks = node.disks
    # wait for node controller to update disk status
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "allowScheduling", True)
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "storageReserved", SMALL_DISK_SIZE)
            free, total = common.get_host_disk_size(disk_path1)
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "storageAvailable", free)
            wait_for_disk_status(client, lht_hostId, fsid,
                                 "storageMaximum", total)

    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for key, disk in iter(disks.items()):
        if disk.path == disk_path1:
            assert disk.allowScheduling
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == 0
            free, total = common.get_host_disk_size(disk_path1)
            assert disk.storageMaximum == total
            assert disk.storageAvailable == free
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_READY]["status"] == \
                CONDITION_STATUS_TRUE
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_TRUE
        else:
            assert not disk.allowScheduling

    # create a volume
    nodes = client.list_node()
    vol_name = common.generate_volume_name()
    volume = create_volume(client, vol_name, str(SMALL_DISK_SIZE),
                           lht_hostId, len(nodes))
    replicas = volume.replicas
    for replica in replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        if id == lht_hostId:
            assert replica.dataPath.startswith(disk_path1)

    # umount the disk
    mount_path = os.path.join(DIRECTORY_PATH, disk_volume_name)
    # After longhorn refactor, umount_disk will fail with
    # `target is busy` error from Linux as replica is using
    # this mount path for storing it's files.
    # As a work around, we are using `-l` flag that does the
    # unmount for active mount destinations.
    common.lazy_umount_disk(mount_path)

    # wait for update node status
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "storageMaximum", 0)
            wait_for_disk_conditions(client, lht_hostId, fsid,
                                     DISK_CONDITION_READY,
                                     CONDITION_STATUS_FALSE)

    # check result
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    update_disks = []
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            assert disk.allowScheduling
            assert disk.storageMaximum == 0
            assert disk.storageAvailable == 0
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == SMALL_DISK_SIZE
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_READY]["status"] == \
                CONDITION_STATUS_FALSE
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_FALSE
        else:
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_READY]["status"] == \
                CONDITION_STATUS_TRUE
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_TRUE
            update_disks.append(disk)

    # delete umount disk exception
    with pytest.raises(Exception) as e:
        node.diskUpdate(disks=update_disks)
    assert "disable the disk" in str(e.value)

    # update other disks
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            disk.allowScheduling = False
        else:
            disk.allowScheduling = True
    test_update = get_update_disks(disks)
    node = node.diskUpdate(disks=test_update)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path != disk_path1:
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "allowScheduling", True)
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path != disk_path1:
            assert disk.allowScheduling

    # mount the disk back
    mount_path = os.path.join(DIRECTORY_PATH, disk_volume_name)
    disk_volume = client.by_id_volume(disk_volume_name)
    dev = get_volume_endpoint(disk_volume)
    common.mount_disk(dev, mount_path)

    # wait for update node status
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "allowScheduling", False)
            wait_for_disk_conditions(client, lht_hostId, fsid,
                                     DISK_CONDITION_READY,
                                     CONDITION_STATUS_TRUE)

    # check result
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            free, total = common.get_host_disk_size(disk_path1)
            assert not disk.allowScheduling
            assert disk.storageMaximum == total
            assert disk.storageAvailable == free
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == SMALL_DISK_SIZE
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_READY]["status"] == \
                CONDITION_STATUS_TRUE
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_TRUE
        else:
            conditions = disk.conditions
            assert conditions[DISK_CONDITION_READY]["status"] == \
                CONDITION_STATUS_TRUE
            assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
                CONDITION_STATUS_TRUE

    # delete volume and umount disk
    cleanup_volume(client, vol_name)
    mount_path = os.path.join(DIRECTORY_PATH, disk_volume_name)
    common.umount_disk(mount_path)

    # wait for update node status
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "allowScheduling", False)
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "storageScheduled", 0)
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "storageMaximum", 0)

    # test delete the umount disk
    node = client.by_id_node(lht_hostId)
    node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)
    cmd = ['rm', '-r', mount_path]
    subprocess.check_call(cmd)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_replica_cleanup(client):  # NOQA
    nodes = client.list_node()
    lht_hostId = get_self_host_id()

    node = client.by_id_node(lht_hostId)
    extra_disk_path = create_host_disk(client, "extra-disk",
                                       "10G", lht_hostId)
    extra_disk = {"path": extra_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks.append(extra_disk)
    node = node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)

    extra_disk_fsid = ""
    for fsid, disk in iter(node.disks.items()):
        if disk.path == extra_disk_path:
            extra_disk_fsid = fsid
            break

    for node in nodes:
        # disable all the disks except the ones on the current node
        if node.name == lht_hostId:
            continue
        for fsid, disk in iter(node.disks.items()):
            break
        disk.allowScheduling = False
        update_disks = get_update_disks(node.disks)
        node.diskUpdate(disks=update_disks)
        node = wait_for_disk_status(client, node.name,
                                    fsid,
                                    "allowScheduling", False)

    vol_name = common.generate_volume_name()
    # more replicas, make sure both default and extra disk will get one
    volume = create_volume(client, vol_name, str(Gi), lht_hostId, 5)
    data_paths = []
    for replica in volume.replicas:
        data_paths.append(replica.dataPath)

    # data path should exist now
    for data_path in data_paths:
        assert exec_nsenter("ls {}".format(data_path))

    cleanup_volume(client, vol_name)

    # data path should be gone due to the cleanup of replica
    for data_path in data_paths:
        with pytest.raises(subprocess.CalledProcessError):
            exec_nsenter("ls {}".format(data_path))

    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk = disks[extra_disk_fsid]
    disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_status(client, lht_hostId,
                                extra_disk_fsid,
                                "allowScheduling", False)
    wait_for_disk_status(client, lht_hostId, extra_disk_fsid,
                         "storageScheduled", 0)

    disks = node.disks
    disk = disks[extra_disk_fsid]
    assert not disk.allowScheduling
    disks.pop(extra_disk_fsid)
    update_disks = get_update_disks(disks)
    node.diskUpdate(disks=update_disks)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))

    cleanup_host_disk(client, 'extra-disk')


@pytest.mark.node
def test_node_default_disk_labeled(client, core_api, random_disk_path,  reset_default_disk_label,  # NOQA
                                   reset_disk_settings):  # NOQA
    """
    Test that only Nodes with the proper label applied get a default Disk
    created on them when one doesn't already exist. Makes sure the created
    Disk matches the Default Data Path Setting.
    """
    # Set up cases.
    cases = {
        "disk_exists": None,
        "labeled": None,
        "unlabeled": None
    }
    nodes = client.list_node().data
    assert len(nodes) >= 3

    node = nodes[0]
    cases["disk_exists"] = node.id
    core_api.patch_node(node.id, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL: "true"
            }
        }
    })

    node = nodes[1]
    cases["labeled"] = node.id
    core_api.patch_node(node.id, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL: "true"
            }
        }
    })
    cleanup_node_disks(client, node.id)

    node = nodes[2]
    cases["unlabeled"] = node.id
    cleanup_node_disks(client, node.id)

    # Set disk creation and path Settings.
    setting = client.by_id_setting(SETTING_DEFAULT_DATA_PATH)
    client.update(setting, value=random_disk_path)
    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")
    wait_for_disk_update(client, cases["labeled"], 1)

    # Check each case.
    node = client.by_id_node(cases["disk_exists"])
    assert len(node.disks) == 1
    assert get_update_disks(node.disks)[0].path == \
        DEFAULT_DISK_PATH

    node = client.by_id_node(cases["labeled"])
    assert len(node.disks) == 1
    assert get_update_disks(node.disks)[0].path == \
        random_disk_path

    # Remove the Disk from the Node used for this test case so we can have the
    # fixtures clean up after.
    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="false")
    cleanup_node_disks(client, node.id)

    node = client.by_id_node(cases["unlabeled"])
    assert len(node.disks) == 0


@pytest.mark.node
def test_node_config_annotations(client, core_api,  # NOQA
                                 reset_default_disk_label,  # NOQA
                                 reset_disk_and_tag_annotations,  # NOQA
                                 reset_disk_settings):  # NOQA
    nodes = client.list_node().data
    assert len(nodes) >= 3

    node0 = nodes[0].id
    core_api.patch_node(node0, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"' + DEFAULT_DISK_PATH +
                    '","allowScheduling":true,' +
                    '"storageReserved":1024,"tags":["ssd","fast"]}]',
                DEFAULT_NODE_TAG_ANNOTATION: '["tag2","tag2","tag1"]',
            }
        }
    })

    node1 = nodes[1].id
    core_api.patch_node(node1, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"/invalid-path","allowScheduling":false,' +
                    '"storageReserved":1024,"tags":["ssd","fast"]}]',
                DEFAULT_NODE_TAG_ANNOTATION: '["tag1",",.*invalid-tag"]',
            }
        }
    })

    cleanup_node_disks(client, node0)
    cleanup_node_disks(client, node1)

    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")

    wait_for_node_tag_update(client, node0, ["tag1", "tag2"])
    node = wait_for_disk_update(client, node0, 1)
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 1024
        assert set(disk.tags) == {"ssd", "fast"}
        break

    node = client.by_id_node(node1)
    assert len(node.disks) == 0
    assert not node.tags

    core_api.patch_node(node1, {
        "metadata": {
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"' + DEFAULT_DISK_PATH +
                    '","allowScheduling":true,' +
                    '"storageReserved":2048,"tags":["hdd","slow"]}]',
                DEFAULT_NODE_TAG_ANNOTATION: '["tag1","tag3"]',
            }
        }
    })

    wait_for_node_tag_update(client, node1, ["tag1", "tag3"])
    node = wait_for_disk_update(client, node1, 1)
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 2048
        assert set(disk.tags) == {"hdd", "slow"}
        break


@pytest.mark.node
def test_invalid_node_annotations(client, core_api,  # NOQA
                                 reset_default_disk_label,  # NOQA
                                 reset_disk_and_tag_annotations,  # NOQA
                                 reset_disk_settings):  # NOQA

    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")

    nodes = client.list_node().data
    node_name = nodes[0].id

    # Case1: The invalid disk annotation shouldn't
    # intervene the node controller.
    cleanup_node_disks(client, node_name)
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"/invalid-path","allowScheduling":false,' +
                    '"storageReserved":1024,"tags":["ssd","fast"]}]',
            }
        }
    })
    # Case1.1: Longhorn shouldn't apply the invalid disk annotation.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    node = client.by_id_node(node_name)
    assert len(node.disks) == 0
    assert not node.tags

    # Case1.2: Disk and tag update should work fine even if there is
    # invalid disk annotation.
    disk = {"path": DEFAULT_DISK_PATH, "allowScheduling": True}
    node.diskUpdate(disks=[disk])
    node = wait_for_disk_update(client, node_name, 1)
    assert len(node.disks) == 1
    for fsid, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 0
        assert not disk.tags
        break
    client.update(node, tags=["tag1", "tag2"])
    wait_for_node_tag_update(client, node_name, ["tag1", "tag2"])

    # Case2: The existing node disks keep unchanged
    # even if the annotation is corrected.
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"' + DEFAULT_DISK_PATH +
                    '","allowScheduling":false,' +
                    '"storageReserved":2048,"tags":["hdd","slow"]}]',
            }
        }
    })
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    assert len(node.disks) == 1
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 0
        assert not disk.tags
        break

    # Case3: the correct annotation should be applied
    # after cleaning up all disks
    node = client.by_id_node(node_name)
    disks = node.disks
    for _, disk in iter(disks.items()):
        disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = client.by_id_node(node_name)
    node.diskUpdate(disks=update_disks)
    node.diskUpdate(disks=[])
    # the fsid is always the same
    node = wait_for_disk_status(client, node_name, fsid,
                                "storageReserved", 2048)
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is False
        assert disk.storageReserved == 2048
        assert set(disk.tags) == {"hdd", "slow"}
        break

    # do cleanup then test the invalid tag annotation.
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION: None,
            }
        }
    })
    node = cleanup_node_disks(client, node_name)
    client.update(node, tags=[])
    wait_for_node_tag_update(client, node_name, [])

    # Case4: The invalid tag annotation shouldn't
    # intervene the node controller.
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_NODE_TAG_ANNOTATION: '[",.*invalid-tag"]',
            }
        }
    })
    # Case4.1: Longhorn shouldn't apply the invalid tag annotation.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    node = client.by_id_node(node_name)
    assert len(node.disks) == 0
    assert not node.tags

    # Case4.2: Disk and tag update should work fine even if there is
    # invalid tag annotation.
    disk = {"path": DEFAULT_DISK_PATH, "allowScheduling": True,
            "storageReserved": 1024}
    node.diskUpdate(disks=[disk])
    node = wait_for_disk_update(client, node_name, 1)
    assert len(node.disks) == 1
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 1024
        assert not disk.tags
        break
    client.update(node, tags=["tag3", "tag4"])
    wait_for_node_tag_update(client, node_name, ["tag3", "tag4"])

    # Case5: The existing node keep unchanged
    # even if the tag annotation is fixed up.
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_NODE_TAG_ANNOTATION: '["storage"]',
            }
        }
    })
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    node = client.by_id_node(node_name)
    assert set(node.tags) == {"tag3", "tag4"}

    # Case6: Clean up all node tags
    # then the correct annotation should be applied.
    client.update(node, tags=[])
    wait_for_node_tag_update(client, node_name, ["storage"])


@pytest.mark.node
def test_no_node_annotation(client, core_api,  # NOQA
                            reset_default_disk_label,  # NOQA
                            reset_disk_and_tag_annotations,  # NOQA
                            reset_disk_settings):  # NOQA

    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")

    nodes = client.list_node().data
    node_name = nodes[0].id

    # the label is set but there is no annotation.
    core_api.patch_node(node_name, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
        }
    })

    # Case1: Disk update should work fine
    node = client.by_id_node(node_name)
    assert len(node.disks) == 1
    for fsid, disk in iter(node.disks.items()):
        disk.allowScheduling = False
        disk.storageReserved = 0
        disk.tags = ["original"]
    node.diskUpdate(disks=[disk])
    node = wait_for_disk_status(client, node_name, fsid,
                                "storageReserved", 0)
    assert len(node.disks) == 1
    assert disk.allowScheduling is False
    assert disk.storageReserved == 0
    assert set(disk.tags) == {"original"}

    # Case2: Tag update with disk set should work fine
    client.update(node, tags=["tag0"])
    wait_for_node_tag_update(client, node_name, ["tag0"])
    client.update(node, tags=[])
    wait_for_node_tag_update(client, node_name, [])

    # Case3: The tag annotation with disk set should work fine
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_NODE_TAG_ANNOTATION: '["tag1"]',
            }
        }
    })
    wait_for_node_tag_update(client, node_name, ["tag1"])
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_NODE_TAG_ANNOTATION: None,
            }
        }
    })
    client.update(node, tags=[])
    wait_for_node_tag_update(client, node_name, [])

    # Case4: Tag update with disk unset should work fine
    cleanup_node_disks(client, node_name)
    client.update(node, tags=["tag2"])
    wait_for_node_tag_update(client, node_name, ["tag2"])
    client.update(node, tags=[])
    wait_for_node_tag_update(client, node_name, [])

    # Case5: The tag annotation with disk unset should work fine
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_NODE_TAG_ANNOTATION: '["tag3"]',
            }
        }
    })
    wait_for_node_tag_update(client, node_name, ["tag3"])
