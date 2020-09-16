import common
import pytest
import os
import subprocess
import time

from random import choice
from string import ascii_lowercase, digits

import copy

from common import core_api, client, pod  # NOQA
from common import Mi, Gi, SIZE, DATA_SIZE_IN_MB_2
from common import DEFAULT_DISK_PATH, DIRECTORY_PATH
from common import CONDITION_STATUS_FALSE, CONDITION_STATUS_TRUE, \
    NODE_CONDITION_SCHEDULABLE, DISK_CONDITION_SCHEDULABLE
from common import get_core_api_client, get_longhorn_api_client, \
    get_self_host_id
from common import SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE, \
    SETTING_DEFAULT_DATA_PATH, \
    SETTING_CREATE_DEFAULT_DISK_LABELED_NODES, \
    DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_DISABLE_SCHEDULING_ON_CORDONED_NODE
from common import VOLUME_FRONTEND_BLOCKDEV
from common import get_volume_endpoint
from common import wait_for_node_tag_update, \
    wait_for_node_schedulable_condition
from common import wait_for_disk_status, wait_for_disk_conditions, \
    wait_for_disk_connected, wait_for_disk_storage_available, \
    wait_for_disk_deletion, cleanup_node_disks
from common import exec_nsenter

from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import SETTING_MKFS_EXT4_PARAMS

from common import settings_reset # NOQA
from common import create_and_check_volume
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_and_wait_pod
from common import write_pod_volume_random_data
from common import get_pod_data_md5sum
from common import wait_for_volume_healthy
from common import wait_for_volume_replica_count
from common import wait_for_volume_degraded
from common import delete_and_wait_pod
from common import wait_for_volume_detached
from common import wait_for_volume_healthy_no_frontend

from common import RETRY_COUNTS, RETRY_INTERVAL

CREATE_DEFAULT_DISK_LABEL = "node.longhorn.io/create-default-disk"
CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG = "config"
DEFAULT_DISK_CONFIG_ANNOTATION = "node.longhorn.io/default-disks-config"
DEFAULT_NODE_TAG_ANNOTATION = "node.longhorn.io/default-node-tags"
SMALL_DISK_SIZE = (2 * 1024 * 1024)
TEST_FILE = 'test'
NODE_UPDATE_WAIT_INTERVAL = 2


def set_node_cordon(api, node_name, to_cordon):
    """
    Set a kubernetes node schedulable status
    """
    payload = {
        "spec": {
            "unschedulable": to_cordon
        }
    }

    api.patch_node(node_name, payload)


@pytest.fixture
def random_disk_path():
    return os.path.abspath(
        "/var/lib/longhorn-" + "".join(choice(ascii_lowercase + digits)
                                       for _ in range(6)))


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

    mkfs_ext4_settings = client.by_id_setting(SETTING_MKFS_EXT4_PARAMS)
    mkfs_ext4_options = mkfs_ext4_settings.value

    # prepare the disk in the host filesystem
    disk_path = common.prepare_host_disk(get_volume_endpoint(volume),
                                         volume.name,
                                         mkfs_ext4_options)
    return disk_path


def cleanup_host_disk_with_volume(client, *args):  # NOQA
    # clean disk
    for vol_name in args:
        # umount disk
        common.cleanup_host_disk(vol_name)
        # clean volume
        cleanup_volume(client, vol_name)


def create_volume(client, vol_name, size, node_id, r_num):  # NOQA
    volume = client.create_volume(name=vol_name, size=size,
                                  numberOfReplicas=r_num)
    assert volume.numberOfReplicas == r_num
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

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
def test_update_node(client):  # NOQA
    """
    Test update node scheduling

    1. Get list of nodes
    2. Update scheduling to false for current node
    3. Read back to verify
    4. Update scheduling to true for current node
    5. Read back to verify
    """
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
def test_disk_operations(client):  # NOQA
    """
    Test disk operations

    The test will verify Longhorn disks work fine

    1. Try to delete all the disks. It should fail due to scheduling is enabled
    2. Create and connect two disks `disk1` and `disk2` to the current node.
    3. Verify two extra disks have been added to the node
    4. Disconnect and re-connect the 2 disks.
    5. Verify 'connect' and 'disconnect' calls work fine.
    6. Disable the two disks' scheduling and StorageReserved,
    7. Update the two disks.
    8. Validate all the disks properties.
    9. Delete other two disks. Validate deletion works.
    """
    lht_hostId = get_self_host_id()

    disks = client.list_disk()
    for disk in disks:
        if disk.nodeID == lht_hostId:
            break
    assert disk

    # test delete disk exception
    with pytest.raises(Exception) as e:
        client.delete(disk)
    assert "need to disable the scheduling " \
           "before deleting the connected disk" \
           in str(e.value)

    disk_path1 = create_host_disk(client, 'vol-disk-1',
                                  str(Gi), lht_hostId)
    disk_path2 = create_host_disk(client, 'vol-disk-2',
                                  str(Gi), lht_hostId)
    disk1 = client.create_disk(path=disk_path1, nodeID=lht_hostId,
                               allowScheduling=True)
    disk2 = client.create_disk(path=disk_path2, nodeID=lht_hostId,
                               allowScheduling=True)
    disk_name1 = disk1.name
    disk_name2 = disk2.name
    disk1 = wait_for_disk_connected(client, disk_name1)
    disk2 = wait_for_disk_connected(client, disk_name2)

    client.update(disk1, allowScheduling=False,
                  storageReserved=SMALL_DISK_SIZE)
    client.update(disk2, allowScheduling=False,
                  storageReserved=SMALL_DISK_SIZE)
    wait_for_disk_status(client, disk_name1, "allowScheduling", False)
    wait_for_disk_status(client, disk_name2, "allowScheduling", False)
    wait_for_disk_status(client, disk_name1,
                         "storageReserved", SMALL_DISK_SIZE)
    wait_for_disk_status(client, disk_name2,
                         "storageReserved", SMALL_DISK_SIZE)
    disk1 = wait_for_disk_storage_available(client, disk_name1, disk_path1)
    disk2 = wait_for_disk_storage_available(client, disk_name2, disk_path2)

    assert not disk1.allowScheduling
    assert disk1.storageReserved == SMALL_DISK_SIZE
    assert disk1.storageScheduled == 0
    free1, total1 = common.get_host_disk_size(disk_path1)
    assert disk1.storageMaximum == total1
    assert disk1.storageAvailable == free1

    assert not disk2.allowScheduling
    assert disk2.storageReserved == SMALL_DISK_SIZE
    assert disk2.storageScheduled == 0
    free2, total2 = common.get_host_disk_size(disk_path1)
    assert disk2.storageMaximum == total2
    assert disk2.storageAvailable == free2

    client.delete(disk1)
    client.delete(disk2)

    wait_for_disk_deletion(client, disk_name1)
    wait_for_disk_deletion(client, disk_name2)

    cleanup_host_disk_with_volume(client, 'vol-disk-1', 'vol-disk-2')


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
def test_replica_scheduler_no_disks(client):  # NOQA
    """
    Test replica scheduler with no disks available

    1. Delete all the disks on all the nodes
    2. Create a volume.
    3. Wait for volume condition `scheduled` to be false.
    """
    nodes = client.list_node()
    disks = client.list_disk()
    for disk in disks:
        client.update(disk, allowScheduling=False)
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_status(client, disk.name,
                             "allowScheduling", False)
        client.delete(disk)
    for i in range(RETRY_COUNTS):
        disks = client.list_disk()
        if len(disks) == 0:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(disks) == 0

    # test there's no disk fit for volume
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE,
                         numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)


@pytest.mark.node  # NOQA
def test_disable_scheduling_on_cordoned_node(client,  # NOQA
                                             core_api,  # NOQA
                                             reset_default_disk_label,  # NOQA
                                             reset_disk_and_tag_annotations,  # NOQA
                                             reset_disk_settings):  # NOQA
    """
    Test replica scheduler: schedule replica based on
    `Disable Scheduling On Cordoned Node` setting

    1. Set `Disable Scheduling On Cordoned Node` to true.
    2. Set `Replica Soft Anti-Affinity` to false.
    3. Set cordon on one node.
    4. Create a volume with 3 replicas.
    5. Verify the scheduler should fail due to cordoned node.
    6. Set `Disable Scheduling On Cordoned Node` to false.
    7. Automatically the scheduler should creates three replicas
    from step 5 failure.
    8. Attach this volume, write data to it and check the data.
    9. Delete the test volume.
    """
    # Set `Disable Scheduling On Cordoned Node` to true
    disable_scheduling_on_cordoned_node_setting = \
        client.by_id_setting(SETTING_DISABLE_SCHEDULING_ON_CORDONED_NODE)
    client.update(disable_scheduling_on_cordoned_node_setting, value="true")

    # Set `Replica Node Level Soft Anti-Affinity` to false
    node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(node_soft_anti_affinity_setting, value="false")

    # Get one node
    nodes = client.list_node()
    node = nodes[0]

    # Set cordon on node
    set_node_cordon(core_api, node.name, True)

    node = wait_for_node_schedulable_condition(
        get_longhorn_api_client(), node.name)

    # Node schedulable condition should be faulse
    assert node.conditions[NODE_CONDITION_SCHEDULABLE]["status"] ==  \
        "False"
    assert node.conditions[NODE_CONDITION_SCHEDULABLE]["reason"] == \
        "KubernetesNodeCordoned"

    # Create a volume and check its schedulable condition should be false
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE,
                         numberOfReplicas=len(nodes))
    common.wait_for_volume_detached(client, vol_name)
    common.wait_for_volume_condition_scheduled(client, vol_name,
                                               "status",
                                               CONDITION_STATUS_FALSE)

    # Set uncordon on node
    set_node_cordon(core_api, node.name, False)

    # Node schedulable condition should be true
    node = wait_for_node_schedulable_condition(
        get_longhorn_api_client(), node.name)
    assert node.conditions[NODE_CONDITION_SCHEDULABLE]["status"] == "True"

    # Created volume schedulable condition change to true
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""

    # Attach the volume and write data then check it.
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, vol_name)

    assert len(volume.replicas) == 3

    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    # Cleanup volume
    cleanup_volume(client, vol_name)

@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_replica_scheduler_large_volume_fit_small_disk(client):  # NOQA
    """
    Test replica scheduler: not schedule a large volume to small disk

    1. Create a host disk `small_disk` and connect it to the current node.
    2. Create a new large volume.
    3. Verify the volume wasn't scheduled on the `small_disk`.
    """
    # create a small size disk on current node
    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)

    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    disk = client.create_disk(
        path=small_disk_path, nodeID=lht_hostId, allowScheduling=True)
    disk = wait_for_disk_status(client, disk.name, "state", "connected")

    # volume is too large to fill into small size disk on current node
    vol_name = common.generate_volume_name()
    volume = create_volume(client, vol_name, str(Gi),
                           lht_hostId, len(nodes))

    # check replica on current node shouldn't schedule to small disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        if id == lht_hostId:
            assert replica.diskID != disk.name
            assert replica.dataPath != disk.path
        node_hosts = list(filter(lambda x: x != id, node_hosts))

    assert len(node_hosts) == 0


@pytest.mark.node  # NOQA
def test_replica_scheduler_too_large_volume_fit_any_disks(client):  # NOQA
    """
    Test replica scheduler: volume is too large to fit any disks

    1. Disable all default disks on all nodes by setting storageReserved to
    maximum size
    2. Create volume.
    3. Verify the volume scheduled condition is false.
    4. Reduce the storageReserved on all the disks to just enough for one
    replica.
    5. The volume should automatically change scheduled condition to true
    6. Attach the volume.
    7. Make sure every replica landed on different nodes's default disk.
    """

    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    disks = client.list_disk()

    expect_node_disk = {}
    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            client.update(disk, allowScheduling=disk.allowScheduling,
                          storageReserved=disk.storageMaximum)
            disk = wait_for_disk_status(
                client, disk.name, "storageReserved", disk.storageMaximum)
            expect_node_disk[disk.nodeID] = disk

    # volume is too large to fill into any disks
    volume_size = 4 * Gi
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=str(volume_size),
                         numberOfReplicas=len(nodes))
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)

    # Reduce StorageReserved of each default disk so that each node can fit
    # only one replica.
    needed_for_scheduling = int(
        volume_size * 1.5 * 100 /
        int(DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE))

    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            reserved = disk.storageMaximum - needed_for_scheduling
            client.update(disk, allowScheduling=disk.allowScheduling,
                          storageReserved=reserved)
            wait_for_disk_status(
                client, disk.name, "storageReserved", reserved)

    # check volume status
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    assert volume.state == "detached"
    assert volume.created != ""
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)

    node_hosts = []
    for node in nodes:
        node_hosts.append(node.name)
    assert len(node_hosts) != 0
    # check all replica should be scheduled to default disk
    for replica in volume.replicas:
        id = replica.hostId
        assert id != ""
        assert replica.running
        expect_disk = expect_node_disk[id]
        assert replica.diskID == expect_disk.name
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)


@pytest.mark.node  # NOQA
def test_replica_scheduler_update_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: update overprovisioning setting

    1. Set setting `overprovisioning` to 0. (disable all scheduling)
    2. Create a new volume. Verify volume's `scheduled` condition is false.
    3. Set setting `over provisioning` to 100%.
    4. Verify volume's `scheduled` condition now become true.
    5. Attach the volume.
    6. Make sure every replica landed on different nodes's default disk.
    """
    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    disks = client.list_disk()

    expect_node_disk = {}
    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            expect_node_disk[disk.nodeID] = disk

    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value

    # set storage over provisioning percentage to 0
    # to test all replica couldn't be scheduled
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="0")
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE, numberOfReplicas=len(nodes))
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)

    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    # check volume status
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
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
        assert replica.diskID == expect_disk.name
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)
    client.update(over_provisioning_setting,
                  value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_exceed_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: exceeding overprovisioning parameter

    1. Set setting `overprovisioning` to 100
    2. Update every disks to set 1G available for scheduling
    3. Try to schedule a volume of 2G. Volume scheduled condition should be
    false
    """
    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value
    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    # test exceed over provisioning limit couldn't be scheduled
    disks = client.list_disk()
    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            client.update(disk, allowScheduling=disk.allowScheduling,
                          storageReserved=disk.storageMaximum - 1*Gi)
            wait_for_disk_status(
                client, disk.name,
                "storageReserved", disk.storageMaximum - 1*Gi)

    nodes = client.list_node()
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=str(2*Gi),
                         numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)
    client.delete(volume)
    common.wait_for_volume_delete(client, vol_name)
    client.update(over_provisioning_setting, value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_just_under_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: just under overprovisioning parameter

    1. Set setting `overprovisioning` to 100
    2. Get the maximum size of all the disks
    3. Create a volume using maximum_size - 2MiB as the volume size.
    4. Volume scheduled condition should be true.
    5. Make sure every replica landed on different nodes's default disk.
    """
    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    old_provisioning_setting = over_provisioning_setting.value
    # set storage over provisioning percentage to 100
    over_provisioning_setting = client.update(over_provisioning_setting,
                                              value="100")

    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    disks = client.list_disk()

    expect_node_disk = {}
    max_size_array = []
    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            expect_node_disk[disk.nodeID] = disk
            max_size_array.append(disk.storageMaximum)
        client.update(disk, allowScheduling=disk.allowScheduling,
                      storageReserved=0)
        wait_for_disk_status(
            client, disk.name, "storageReserved", 0)

    # volume size is round up by 2MiB
    max_size = min(max_size_array) - 2 * 1024 * 1024
    # test just under over provisioning limit could be scheduled
    vol_name = common.generate_volume_name()
    client.create_volume(
        name=vol_name, size=str(max_size), numberOfReplicas=len(nodes))
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
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
        assert replica.diskID == expect_disk.name
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)
    client.update(over_provisioning_setting, value=old_provisioning_setting)


@pytest.mark.node  # NOQA
def test_replica_scheduler_update_minimal_available(client):  # NOQA
    """
    Test replica scheduler: update setting `minimal available`

    1. Set setting `minimal available` to 100% (means no one can schedule)
    2. Verify for all disks' schedulable condition to become false.
    3. Create a volume. Verify it's unschedulable.
    4. Set setting `minimal available` back to default setting
    5. Disk should become schedulable now.
    6. Volume should be scheduled now.
    7. Attach the volume.
    8. Make sure every replica landed on different nodes's default disk.
    """
    minimal_available_setting = client.by_id_setting(
        SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    old_minimal_setting = minimal_available_setting.value

    lht_hostId = get_self_host_id()
    nodes = client.list_node()

    disks = client.list_disk()
    expect_node_disk = {}
    for disk in disks:
        if disk.path == DEFAULT_DISK_PATH and disk.state == "connected":
            expect_node_disk[disk.nodeID] = disk

    # set storage minimal available percentage to 100
    # to test all replica couldn't be scheduled
    minimal_available_setting = client.update(minimal_available_setting,
                                              value="100")
    # wait for disks state
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_conditions(
            client, disk.name,
            DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_FALSE)

    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE, numberOfReplicas=len(nodes))
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)

    # set storage minimal available percentage to default value(10)
    client.update(minimal_available_setting, value=old_minimal_setting)
    # wait for disks state
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_conditions(
            client, disk.name,
            DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)

    # check volume status
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
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
        assert replica.diskID == expect_disk.name
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume(client, vol_name)


@pytest.mark.node  # NOQA
def test_node_controller_sync_storage_scheduled(client):  # NOQA
    """
    Test node controller sync storage scheduled correctly

    1. Create a volume with "number of nodes" replicas
    2. Confirm that each disks now has "volume size" scheduled
    3. Confirm every disks are still schedulable.
    """
    lht_hostId = get_self_host_id()
    nodes = client.list_node()

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
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_status(
            client, disk.name, "storageScheduled", SMALL_DISK_SIZE)

    for replica in replicas:
        disk = client.by_id_disk(replica.diskID)
        conditions = disk.conditions
        assert disk.storageScheduled == SMALL_DISK_SIZE
        assert conditions[DISK_CONDITION_SCHEDULABLE]["status"] == \
               CONDITION_STATUS_TRUE

    # clean volumes
    cleanup_volume(client, vol_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_controller_sync_storage_available(client):  # NOQA
    """
    Test node controller sync storage available correctly

    1. Create a host disk `test_disk` on the current node
    2. Write 1MiB data to the disk, and run `sync`
    3. Verify the disk `storageAvailable` will update to include the file
    """
    lht_hostId = get_self_host_id()

    # create a disk to test storageAvailable
    test_disk_path = create_host_disk(
        client, "vol-test", SIZE, lht_hostId)
    disk = client.create_disk(
        path=test_disk_path, nodeID=lht_hostId, allowScheduling=True)
    wait_for_disk_connected(client, disk.name)

    # write specified byte data into disk
    test_file_path = os.path.join(test_disk_path, TEST_FILE)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    cmd = ['dd', 'if=/dev/zero', 'of=' + test_file_path, 'bs=1M', 'count=1']
    subprocess.check_call(cmd)
    subprocess.check_call(['sync', test_file_path])

    wait_for_disk_storage_available(client, disk.name, test_disk_path)

    os.remove(test_file_path)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
def test_node_controller_sync_disk_state(client):  # NOQA
    """
    Test node controller to sync disk state

    1. Set setting `StorageMinimalAvailablePercentage` to 100
    2. All the disks will become `unschedulable`.
    3. Restore setting `StorageMinimalAvailablePercentage` to previous
    4. All the disks will become `schedulable`.
    """
    # update StorageMinimalAvailablePercentage to test Disk State
    setting = client.by_id_setting(
        SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    old_minimal_available_percentage = setting.value
    setting = client.update(setting, value="100")
    assert setting.value == "100"

    # wait for disk state update
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_conditions(
            client, disk.name,
            DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_FALSE)

    setting = client.update(setting, value=old_minimal_available_percentage)
    assert setting.value == old_minimal_available_percentage

    # wait for disk state update
    disks = client.list_disk()
    for disk in disks:
        wait_for_disk_conditions(
            client, disk.name,
            DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)


@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_extra_disk_unmount_and_remount(client):  # NOQA
    """
    [Node] Test adding default disk back with extra disk is unmounted
    on the node

    1. Clean up all disks on current node.
    2. Recreate the default disk with "allowScheduling" disabled for
       current node.
    3. Create a Longhorn volume and attach it to current node.
    4. Use the Longhorn volume as an extra host disk and
       enable "allowScheduling" of the default disk for current node.
    5. Verify all disks on current node are "Schedulable".
    6. Delete the default disk on current node.
    7. Unmount the extra disk on current node.
       And wait for it becoming "Unschedulable".
    8. Create and add the default disk back on current node.
    9. Wait and verify the default disk should become "Schedulable".
    10. Mount extra disk back on current node.
    11. Wait and verify this extra disk should become "Schedulable".
    12. Delete the host disk `extra_disk`.
    """
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)

    # Create a default disk with `allowScheduling` disabled
    # so that there is no volume replica using this disk later.
    default_disk = client.create_disk(
        path=DEFAULT_DISK_PATH, nodeID=lht_hostId,
        allowScheduling=False, storageReserved=SMALL_DISK_SIZE)
    wait_for_disk_connected(client, default_disk.name)

    # Create a volume and attached it to this node.
    # This volume will be used as an extra host disk later.
    extra_disk_volume_name = 'extra-disk'
    extra_disk_path = create_host_disk(client, extra_disk_volume_name,
                                       str(Gi), lht_hostId)
    extra_disk = client.create_disk(
        path=extra_disk_path, nodeID=lht_hostId, allowScheduling=True)
    wait_for_disk_connected(client, extra_disk.name)

    # Make sure all disks are schedulable
    disks = client.list_disk()
    for disk in disks:
        if disk.nodeID == lht_hostId:
            wait_for_disk_conditions(
                client, disk.name,
                DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)

    # Delete default disk
    default_disk = client.by_id_disk(default_disk.name)
    client.delete(default_disk)
    wait_for_disk_deletion(client, default_disk.name)

    # Umount the extra disk and wait for unschedulable condition
    common.cleanup_host_disk(extra_disk_path)
    wait_for_disk_status(client, extra_disk.name, "state", "disconnected")
    wait_for_disk_conditions(
        client, extra_disk.name,
        DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_FALSE)

    # Add default disk back and wait for schedulable condition
    default_disk = client.create_disk(
        path=DEFAULT_DISK_PATH, nodeID=lht_hostId,
        allowScheduling=True, storageReserved=SMALL_DISK_SIZE)
    wait_for_disk_connected(client, default_disk.name)
    wait_for_disk_conditions(
        client, default_disk.name,
        DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)
    wait_for_node_schedulable_condition(client, lht_hostId)

    # Mount extra disk back
    # Then verify the extra disk should be at schedulable condition
    disk_volume = client.by_id_volume(extra_disk_volume_name)
    dev = get_volume_endpoint(disk_volume)
    common.mount_disk(dev, extra_disk_path)
    extra_disk = wait_for_disk_conditions(
        client, extra_disk.name,
        DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)

    # Remove extra disk.
    client.update(extra_disk, allowScheduling=False)
    extra_disk = wait_for_disk_status(
        client, extra_disk.name, "allowScheduling", False)
    client.delete(extra_disk)

    cleanup_host_disk_with_volume(client, extra_disk_volume_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_replica_datapath_cleanup(client):  # NOQA
    """
    Test replicas data path cleanup

    Test prerequisites:
      - Enable Replica Node Level Soft Anti-Affinity setting

    1. Create host disk `extra_disk` and add it to the current node.
    2. Disable all the disks except for the ones on the current node.
    3. Create a volume with 5 replicas (soft anti-affinity on)
        1. To make sure both default disk and extra disk can have one replica
        2. Current we don't have anti-affinity for disks on the same node
    4. Verify the data path for replicas are created.
    5. Delete the volume.
    6. Verify the data path for replicas are deleted.
    """
    lht_hostId = get_self_host_id()

    # set soft antiaffinity setting to true
    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="true")

    extra_disk_path = create_host_disk(client, "extra-disk",
                                       "10G", lht_hostId)
    extra_disk = client.create_disk(
        path=extra_disk_path, nodeID=lht_hostId, allowScheduling=True)
    wait_for_disk_connected(client, extra_disk.name)

    # disable all the disks except the ones on the current node
    disks = client.list_disk()
    for disk in disks:
        if disk.nodeID != lht_hostId:
            client.update(disk, allowScheduling=False)
            wait_for_disk_status(client, disk.name, "allowScheduling", False)

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
    extra_disk = wait_for_disk_status(
        client, extra_disk.name, "storageScheduled", 0)

    client.update(extra_disk, allowScheduing=False)
    extra_disk = wait_for_disk_status(
        client, extra_disk.name, "allowScheduling", False)
    client.delete(extra_disk)
    wait_for_disk_deletion(client, extra_disk.name)

    cleanup_host_disk_with_volume(client, 'extra-disk')


@pytest.mark.node
def test_node_default_disk_labeled(
        client, core_api, random_disk_path,   # NOQA
        reset_default_disk_label, reset_disk_settings):  # NOQA
    """
    Test node feature: create default Disk according to the node label

    Makes sure the created Disk matches the Default Data Path Setting.

    1. Add labels to node 0 and 1, don't add label to node 2.
    2. Remove all the disks on node 1 and 2.
        1. The initial default disk will not be recreated.
    3. Set setting `default disk path` to a random disk path.
    4. Set setting `create default disk labeled node` to true.
    5. Check node 0. It should still use the previous default disk path.
        1. Due to we didn't remove the disk from node 0.
    6. Check node 1. A new disk should be created at the random disk path.
    7. Check node 2. There is still no disks
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

    # Check each case.
    for i in range(RETRY_COUNTS):
        node0_verified = False
        node1_verified = False
        node0_disk_count = 0
        node1_disk_count = 0
        disks = client.list_disk()
        for disk in disks:
            if disk.nodeID == cases["disk_exists"]:
                assert disk.path == DEFAULT_DISK_PATH
                wait_for_disk_connected(client, disk.name)
                node0_disk_count += 1
                node0_verified = True
            if disk.nodeID == cases["labeled"]:
                assert disk.path == random_disk_path
                wait_for_disk_connected(client, disk.name)
                node1_disk_count += 1
                node1_verified = True
        if node0_verified and node1_verified:
            break
        time.sleep(RETRY_INTERVAL)
    assert node0_disk_count == 1 and node1_disk_count == 1
    assert node0_verified and node1_verified

    # Remove the Disk from the Node used for this test case so we can have the
    # fixtures clean up after.
    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="false")

    cleanup_node_disks(client, cases["unlabeled"])
    disks = client.list_disk()
    for disk in disks:
        assert disk.nodeID != cases["unlabeled"]


@pytest.mark.node
def test_node_config_annotation(client, core_api,  # NOQA
                                reset_default_disk_label,  # NOQA
                                reset_disk_and_tag_annotations,  # NOQA
                                reset_disk_settings):  # NOQA
    """
    Test node feature: default disks/node configuration

    1. Set node 0 label and annotation.
    2. Set node 1 label but with invalid annotation (invalid path and tag)
    3. Cleanup disks on node 0 and 1.
        1. The initial default disk will not be recreated.
    4. Enable setting `create default disk labeled nodes`
    5. Wait for node tag to update on node 0.
    6. Verify node 0 has correct disk and tags set.
    7. Verify node 1 has no disk or tag.
    8. Update node 1's label and tag to be valid
    9. Verify now node 1 has correct disk and tags set
    """
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

    # Longhorn will not automatically recreate the default disk if setting
    # `create-default-disk-labeled-nodes` is disabled
    cleanup_node_disks(client, node0)
    cleanup_node_disks(client, node1)

    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")

    wait_for_node_tag_update(client, node0, ["tag1", "tag2"])

    found = False
    for i in range(RETRY_COUNTS):
        disks = client.list_disk()
        for disk in disks:
            if disk.nodeID == node0 and disk.path == DEFAULT_DISK_PATH:
                found = True
                disk0 = disk
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found and disk0
    wait_for_disk_connected(client, disk0.name)
    wait_for_disk_status(
        client, disk0.name, "allowScheduling", True)
    wait_for_disk_status(
        client, disk0.name, "storageReserved", 1024)
    wait_for_disk_status(
        client, disk0.name, "tags", {"ssd", "fast"})

    disks = client.list_disk()
    for disk in disks:
        assert disk.nodeID != node1

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

    found = False
    for i in range(RETRY_COUNTS):
        disks = client.list_disk()
        for disk in disks:
            if disk.nodeID == node1 and disk.path == DEFAULT_DISK_PATH:
                found = True
                disk1 = disk
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found and disk1
    wait_for_disk_connected(client, disk1.name)
    wait_for_disk_status(
        client, disk1.name, "allowScheduling", True)
    wait_for_disk_status(
        client, disk1.name, "storageReserved", 2048)
    wait_for_disk_status(
        client, disk1.name, "tags", {"hdd", "slow"})


@pytest.mark.node
def test_node_config_annotation_invalid(client, core_api,  # NOQA
                                        reset_default_disk_label,  # NOQA
                                        reset_disk_and_tag_annotations,  # NOQA
                                        reset_disk_settings):  # NOQA
    """
    Test invalid node annotations for default disks/node configuration


    Case1: The invalid disk annotation shouldn't intervene the node controller.

    1. Set invalid disk annotation
    2. The node tag or disks won't be updated
    3. Create a new disk. It will be updated by the node controller.


    Case2: The existing node disks keep unchanged even if the annotation is
    corrected.

    1. Set valid disk annotation but set `allowScheduling` to false, etc.
    2. Make sure the current disk won't change

    Case3: the correct annotation should be applied after cleaning up all disks

    1. Delete all the disks on the node
    2. Wait for the config from disk annotation applied

    Case4: The invalid tag annotation shouldn't intervene the node controller.

    1. Cleanup the node annotation and remove the node disks/tags
    2. Set invalid tag annotation
    3. Disk and tags configuration will not be applied
    4. Disk and tags can still be updated on the node

    Case5: The existing node keep unchanged even if the tag annotation is fixed
    up.

    1. With existing tags, change tag annotation.
    2. It won't change the current node's tag

    Case6: Clean up all node tags then the correct annotation should be applied

    1. Clean the current tags
    2. New tags from node annotation should be applied

    Case7: Same disk name in annotation shouldn't intereven the node controller
    1. Create one disk for node
    2. Set the same name in annotation and set label and enable
       "Create Default Disk on Labeled Nodes" in settings.
    3. The node tag or disks won't be updated.
    """
    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="true")

    nodes = client.list_node().data
    node_name = nodes[0].id

    # Case1: The invalid disk annotation shouldn't
    # intervene the node controller.

    # Case1.1: Multiple paths on the same filesystem is invalid disk
    # annotation, Longhorn shouldn't apply this.

    # make a clean condition for test to start.
    cleanup_node_disks(client, node_name)

    # patch label and annotations to the node.
    host_dirs = [
        os.path.abspath(os.path.join(DEFAULT_DISK_PATH, "engine-binaries")),
        os.path.abspath(os.path.join(DEFAULT_DISK_PATH, "replicas"))
    ]
    core_api.patch_node(node_name, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"' + host_dirs[0] + '",' +
                    '"allowScheduling":false,' +
                    '"storageReserved":1024},' +
                    '{"path":"' + host_dirs[1] + '",' +
                    '"allowScheduling":false,' +
                    '"storageReserved": 1024}]'
            }
        }
    })

    # Longhorn shouldn't apply the invalid disk annotation.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    disks = client.list_disk()
    for disk in disks:
        assert disk.nodeID != node_name
    node = client.by_id_node(node_name)
    assert not node.tags

    # Case1.2: Invalid disk path annotation shouldn't be applied to Longhorn.
    cleanup_node_disks(client, node_name)
    core_api.patch_node(node_name, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"/invalid-path","allowScheduling":false,' +
                    '"storageReserved":1024,"tags":["ssd","fast"]}]',
            }
        }
    })
    # Longhorn shouldn't apply the invalid disk annotation.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    disks = client.list_disk()
    for disk in disks:
        assert disk.nodeID != node_name
    node = client.by_id_node(node_name)
    assert not node.tags

    # Case1.3: Disk and tag update should work fine even if there is
    # invalid disk annotation.
    disk = client.create_disk(
        path=DEFAULT_DISK_PATH, nodeID=node_name, allowScheduling=True)
    wait_for_disk_connected(client, disk.name)
    wait_for_disk_conditions(
        client, disk.name, DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)
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
    disks = client.list_disk()
    node_disk_count = 0
    for disk in disks:
        if disk.nodeID == node_name:
            node_disk_count += 1
            assert disk.path == DEFAULT_DISK_PATH
            assert disk.allowScheduling is True
            assert disk.storageReserved == 0
            assert not disk.tags
    assert node_disk_count == 1

    # Case3: the correct annotation should be applied
    # after cleaning up all disks
    for disk in disks:
        if disk.nodeID == node_name:
            client.update(disk, allowScheduling=False)
            old_disk = wait_for_disk_status(
                client, disk.name, "allowScheduling", False)
            client.delete(old_disk)

    new_disk_created = False
    for i in range(RETRY_COUNTS):
        disks = client.list_disk()
        for disk in disks:
            if disk.nodeID == node_name and \
                    disk.name != old_disk.name:
                new_disk_created = True
                assert disk.path == DEFAULT_DISK_PATH
                assert disk.allowScheduling is False
                assert disk.storageReserved == 2048
                assert set(disk.tags) == {"hdd", "slow"}
                break
        if new_disk_created:
            break
        time.sleep(RETRY_INTERVAL)

    # do cleanup then test the invalid tag annotation.
    core_api.patch_node(node_name, {
        "metadata": {
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION: None,
            }
        }
    })
    cleanup_node_disks(client, node_name)
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
    disks = client.list_disk()
    for disk in disks:
        assert disk.nodeID != node_name
    node = client.by_id_node(node_name)
    assert not node.tags

    # Case4.2: Disk and tag update should work fine even if there is
    # invalid tag annotation.
    disk = client.create_disk(
        path=DEFAULT_DISK_PATH, nodeID=node_name,
        allowScheduling=True, storageReserved=1024)
    wait_for_disk_connected(client, disk.name)
    disks = client.list_disk()
    node_disk_count = 0
    for disk in disks:
        if disk.nodeID == node_name:
            node_disk_count += 1
            assert disk.path == DEFAULT_DISK_PATH
            assert disk.allowScheduling is True
            assert disk.storageReserved == 1024
            assert not disk.tags
    assert node_disk_count == 1
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
def test_node_config_annotation_missing(client, core_api,  # NOQA
                                        reset_default_disk_label,  # NOQA
                                        reset_disk_and_tag_annotations,  # NOQA
                                        reset_disk_settings):  # NOQA
    """
    Test node labeled for configuration but no annotation

    1. Set setting `create default disk labeled nodes` to true
    2. Set the config label on node 0 but leave annotation empty
    3. Verify disk update works.
    4. Verify tag update works
    5. Verify using tag annotation for configuration works.
    6. After remove the tag annotaion, verify unset tag node works fine.
    7. Set tag annotation again. Verify node updated for the tag.
    """
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
    disks = client.list_disk()
    node_disk_count = 0
    for disk in disks:
        if disk.nodeID == node_name:
            node_disk_count += 1
            client.update(
                disk, allowScheduling=False, storageReserved=0,
                tags=["original"])
            wait_for_disk_status(client, disk.name, "allowScheduling", False)
            wait_for_disk_status(client, disk.name, "storageReserved", 0)
            wait_for_disk_status(client, disk.name, "tags", ["original"])
    assert node_disk_count == 1

    # Case2: Tag update with disk set should work fine
    node = client.by_id_node(node_name)
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


@pytest.mark.node  # NOQA
def test_replica_scheduler_rebuild_restore_is_too_big(client):  # NOQA
    """
    Test replica scheduler: rebuild/restore can be too big to fit a disk

    1. Create a small host disk with `SIZE` and add it to the current node.
    2. Create a volume with size `SIZE`.
    3. Disable all scheduling except for the small disk.
    4. Write a data size `SIZE * 0.9` to the volume and make a backup
    5. Create a restored volume with 1 replica from backup.
        1. Verify the restored volume cannot be scheduled since the existing
        data cannot fit in the small disk
    6. Delete a replica of volume.
        1. Verify the volume reports `scheduled = false` due to unable to find
        a suitable disk for rebuliding replica, since the replica with the
        existing data cannot fit in the small disk
    6. Enable the scheduling for other disks, disable scheduling for small disk
    7. Verify the volume reports `scheduled = true`. And verify the data.
    8. Cleanup the volume.
    9. Verify the restored volume reports `scheduled = true`.
    10. Wait for the restored volume to complete restoration, then check data.

    """
    common.set_random_backupstore(client)

    lht_hostId = get_self_host_id()
    nodes = client.list_node()

    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    small_disk = client.create_disk(
        path=small_disk_path, nodeID=lht_hostId, allowScheduling=False)
    small_disk_name = small_disk.name
    wait_for_disk_connected(client, small_disk_name)

    # volume is same size as the small disk
    volume_size = SIZE
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=str(volume_size),
                         numberOfReplicas=len(nodes))
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)

    volume.attach(hostId=lht_hostId)
    common.wait_for_volume_healthy(client, vol_name)

    # disable all the scheduling except for the small disk
    disks = client.list_disk()
    for disk in disks:
        if disk.name != small_disk_name:
            client.update(disk, allowScheduling=False)
            wait_for_disk_status(client, disk.name, "allowScheduling", False)
        else:
            client.update(disk, allowScheduling=True)
            wait_for_disk_status(client, disk.name, "allowScheduling", True)

    data = {'len': int(int(SIZE) * 0.9), 'pos': 0}
    data['content'] = common.generate_random_data(data['len'])
    _, b, _, _ = common.create_backup(client, vol_name, data)

    # cannot schedule for restore volume
    restore_name = common.generate_volume_name()
    client.create_volume(
        name=restore_name, size=SIZE, numberOfReplicas=1, fromBackup=b.url)
    common.wait_for_volume_condition_scheduled(
        client, restore_name, "status", CONDITION_STATUS_FALSE)

    # cannot schedule due to all disks except for the small disk is disabled
    # And the small disk won't have enough space after taking the replica
    volume.replicaRemove(name=volume.replicas[0].name)
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_FALSE)

    # enable the scheduling
    disks = client.list_disk()
    for disk in disks:
        if disk.name != small_disk_name:
            client.update(disk, allowScheduling=True)
            wait_for_disk_status(client, disk.name, "allowScheduling", True)
        else:
            client.update(disk, allowScheduling=False)
            wait_for_disk_status(client, disk.name, "allowScheduling", False)

    volume = common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)

    common.check_volume_data(volume, data, check_checksum=False)

    cleanup_volume(client, vol_name)

    common.wait_for_volume_condition_scheduled(
        client, restore_name, "status", CONDITION_STATUS_TRUE)
    common.wait_for_volume_restoration_completed(client, restore_name)
    r_vol = common.wait_for_volume_detached(client, restore_name)
    r_vol.attach(hostId=lht_hostId)
    r_vol = common.wait_for_volume_healthy(client, restore_name)

    common.check_volume_data(r_vol, data, check_checksum=False)

    cleanup_volume(client, restore_name)

    cleanup_host_disk_with_volume(client, 'vol-small')


@pytest.mark.node  # NOQA
def test_disk_migration(client):  # NOQA
    """
    1. Disable the node soft anti-affinity.
    2. Create a new disk for the current node.
    3. Add the corresponding Longhorn disk.
    4. Disable the default disk for the current node.
    5. Launch a Longhorn volume with 1 replica.
       Then verify the only replica is scheduled to the new disk.
    6. Write random data to the volume then verify the data.
    7. Detach the volume.
    7. Unmount then remount the disk to another path. (disk migration)
    8. Create another Longhorn disk based on the migrated path.
    9. Verify the Longhorn disk state.
       - The Longhorn disk created before the migration should
         become "disconnected".
       - The Longhorn disk created after the migration should
         become "connected".
    10. Verify the replica DiskID and the path is updated.
    11. Attach the volume. Then verify the state and the data.
    """
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")

    lht_hostId = get_self_host_id()

    disk_vol_name = 'vol-disk'
    disk_path = create_host_disk(client, disk_vol_name, str(Gi), lht_hostId)
    extra_disk = client.create_disk(path=disk_path, nodeID=lht_hostId,
                                    allowScheduling=True, tags=["extra"])
    extra_disk_name = extra_disk.name
    wait_for_disk_connected(client, extra_disk_name)
    extra_disk = wait_for_disk_status(client, extra_disk_name,
                                      "tags", ["extra"])

    disks = client.list_disk()
    for disk in disks:
        # Disable the default disk for the current node
        # Then the volume replicas must be scheduled to the new disk
        if disk.nodeID == lht_hostId and disk.path != disk_path:
            client.update(disk, allowScheduling=False)
            wait_for_disk_status(client, disk.name, "allowScheduling", False)

    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE,
                         numberOfReplicas=1, diskSelector=["extra"])
    common.wait_for_volume_condition_scheduled(
        client, vol_name, "status", CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)

    assert len(volume.replicas) == 1
    assert volume.replicas[0].running
    assert volume.replicas[0].hostId == lht_hostId
    assert volume.replicas[0].diskID == extra_disk_name
    assert extra_disk.path in volume.replicas[0].dataPath

    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    volume.detach()
    volume = common.wait_for_volume_detached(client, vol_name)

    # Mount the volume disk to another path
    common.cleanup_host_disk(disk_path)

    migrated_disk_path = os.path.join(
        DIRECTORY_PATH, disk_vol_name+"-migrated")
    dev = get_volume_endpoint(client.by_id_volume(disk_vol_name))
    common.mount_disk(dev, migrated_disk_path)

    extra_disk = client.create_disk(
        path=migrated_disk_path, nodeID=lht_hostId, allowScheduling=True,
        tags=["extra"])
    assert extra_disk.name == extra_disk_name
    extra_disk = wait_for_disk_connected(client, extra_disk_name)

    replica_migrated = False
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(vol_name)
        assert len(volume.replicas) == 1
        replica = volume.replicas[0]
        assert replica.hostId == lht_hostId
        if replica.diskID == extra_disk_name and \
                extra_disk.path in replica.dataPath:
            replica_migrated = True
            break
        time.sleep(RETRY_INTERVAL)
    assert replica_migrated

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)

    common.check_volume_data(volume, data)

    cleanup_volume(client, vol_name)


def test_node_eviction(client, core_api, volume_name, pod, settings_reset): # NOQA
    """
    Test node eviction (assuming this is a 3 nodes cluster)

    1. Disable scheduling on node 3.
    2. Create volume 1 with 2 replicas.
    3. Attach volume 1 to node 1 and write some data to it and get
    checksum 1.
    4. Disable scheduling and set 'Eviction Requested' to 'true' on node 1.
    5. Volume 1 should be failed to schedule new replica.
    6. Set 'Eviction Requested' to 'false' to cancel node 1 eviction and
    check there should be 1 replica on node 1 and node 2.
    7. Set 'Eviction Requested' to 'true' on node 1.
    8. Set 'Replica Node Level Soft Anti-Affinity' to 'true'.
    9. The eviction should be success, and no replica on node 1, 2 replicas
    on node 2.
    10. Enable scheduling on node 3, and set 'Eviction Requested' to
    'false', enable scheduling on node 1.
    11. Set 'Replica Node Level Soft Anti-Affinity' to 'false'.
    12. Disable scheduling and set 'Eviction Requested' to 'true' on
    node 2. And make sure the volume is in healthy state during the
    eviction.
    13. The eviction should be success and no replica on node 2. And 1
    replica on node 1 and node 3. And verify the data with checksum 1.
    14. Set 'Eviction Requested' to 'false' and enable scheduling on node 2.
    15. Remove the replica on node 1 to make volume 1 in 'Degraded'
    State. And set 'Eviction Requested' to 'true' and disable scheduling
    on node 3.
    16. Once volume 1 is back at 'Healthy' state, and the eviction is
    done, there should be 1 replica on node 1 and node 2. And verify the
    data with checksum 1.
    17. Disable scheduling on node 1.
    18. Create volume 2 with 2 replicas.
    19. Attach volume 2 to node 2 and write some data to it and get
    checksum 2. (volume 1 has replicas on node 1&2, volume 2 has replicas
    on node 2&3)
    20. Enable scheduling on node 1. And set 'Eviction Requested' to 'true'
    and disable scheduling on node 2.
    21. After the eviction is success, volume 1 should has replicas on node
    1&3 and volume 2 should has replicas on node 1&3.
    22. Detach volume 1 and volume 2.
    23. Disable scheduling and set 'Eviction Requested' to 'true' on node 1.
    24. Both volume 1 and 2 will be auto-attached and make sure the volumes
    are in healthy state during the eviction.
    25. After the eviction is success, volume 1 should has replicas on node
    2&3, and volume 2 should has replicas on node 2&3.
    26. Enabled scheduling and set 'Eviction Requested' to 'false' on node
    1.
    27. Verify the data on volume 1 and volume 2, the checksum should be
    the same as checksum 1 and checksum 2.
    28. Set 'Eviction Requested' to 'false' and enable scheduling on node 2.
    """
    nodes = client.list_node()

    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]
    client.update(node3, allowScheduling=False)

    volume1_name = volume_name + "-1"
    volume1_size = str(500 * Mi)
    volume1_data_path = "/data/test"
    pv1_name = volume1_name + "-pv"
    pvc1_name = volume1_name + "-pvc"
    pod1_name = volume1_name + "-pod"
    pod1 = copy.deepcopy(pod)

    pod1['metadata']['name'] = pod1_name
    pod1['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": pvc1_name
        }
    }]

    pod1['spec']['nodeSelector'] = \
        {"kubernetes.io/hostname": node1.name}

    volume1 = create_and_check_volume(client,
                                      volume1_name,
                                      num_of_replicas=2,
                                      size=volume1_size)

    create_pv_for_volume(client, core_api, volume1, pv1_name)
    create_pvc_for_volume(client, core_api, volume1, pvc1_name)

    create_and_wait_pod(core_api, pod1)
    volume1 = wait_for_volume_healthy(client, volume1_name)

    volume1_replica1 = volume1.replicas[0]
    volume1_replica2 = volume1.replicas[1]

    assert volume1_replica1.mode == "RW"
    assert volume1_replica2.mode == "RW"
    assert volume1_replica1.running is True
    assert volume1_replica2.running is True

    write_pod_volume_random_data(core_api,
                                 pod1_name,
                                 volume1_data_path,
                                 DATA_SIZE_IN_MB_2)

    volume1_md5sum = get_pod_data_md5sum(core_api,
                                         pod1_name,
                                         volume1_data_path)

    client.update(node1, allowScheduling=False, evictionRequested=True)
    wait_for_volume_replica_count(client, volume1_name, 3)

    volume1 = client.by_id_volume(volume1_name)

    volume1_err_replica = None
    for replica in volume1.replicas:
        if replica.name == volume1_replica1.name or \
           replica.name == volume1_replica2.name:
            assert replica.running is True
            assert replica.mode == "RW"
        else:
            volume1_err_replica = replica
            break
    assert volume1_err_replica is not None
    assert volume1_err_replica.running is False
    assert volume1_err_replica.mode == ''

    client.update(node1, allowScheduling=False, evictionRequested=False)
    wait_for_volume_replica_count(client, volume1_name, 2)

    volume1 = client.by_id_volume(volume1_name)

    for replica in volume1.replicas:
        if replica.name == volume1_replica1.name:
            assert replica.running is True
            assert replica.mode == "RW"
            assert replica.hostId == volume1_replica1["hostId"]
        elif replica.name == volume1_replica2.name:
            assert replica.running is True
            assert replica.mode == "RW"
            assert replica.hostId == volume1_replica2["hostId"]
        else:
            assert False

    client.update(node1, evictionRequested=True)

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    try:
        client.update(replica_node_soft_anti_affinity_setting,
                      value="true")
    except Exception as e:
        print("\nException when update "
              "Replica Node Level Soft Anti-Affinity setting",
              replica_node_soft_anti_affinity_setting)
        print(e)

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume1_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    for replica in volume1.replicas:
        assert replica.hostId == node2.name
        assert replica.running is True
        assert replica.mode == "RW"

    client.update(node3, allowScheduling=True, evictionRequested=False)
    client.update(node1, allowScheduling=True)

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    try:
        client.update(replica_node_soft_anti_affinity_setting,
                      value="false")
    except Exception as e:
        print("\nException when update "
              "Replica Node Level Soft Anti-Affinity setting",
              replica_node_soft_anti_affinity_setting)
        print(e)

    client.update(node2, allowScheduling=False, evictionRequested=True)

    volume1 = client.by_id_volume(volume1_name)
    assert volume1.robustness == "healthy"

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume1_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    assert volume1.robustness == "healthy"

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume1_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    assert volume1.robustness == "healthy"

    for replica in volume1.replicas:
        if replica.hostId == node1.name:
            assert replica.running is True
            assert replica.mode == "RW"
        elif replica.hostId == node3.name:
            assert replica.running is True
            assert replica.mode == "RW"
        else:
            assert False

    v1md5sum = get_pod_data_md5sum(core_api,
                                   pod1_name,
                                   volume1_data_path)

    assert v1md5sum == volume1_md5sum
    client.update(node2, allowScheduling=True, evictionRequested=False)
    volume1 = client.by_id_volume(volume1_name)

    for replica in volume1.replicas:
        if replica.hostId == node1.name:
            break

    volume1.replicaRemove(name=replica.name)

    client.update(node3, allowScheduling=False, evictionRequested=True)
    wait_for_volume_degraded(client, volume1_name)
    wait_for_volume_healthy(client, volume1_name)

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume1_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    assert volume1.robustness == "healthy"

    for replica in volume1.replicas:
        if replica.hostId == node1.name:
            assert replica.running is True
            assert replica.mode == "RW"
        elif replica.hostId == node2.name:
            assert replica.running is True
            assert replica.mode == "RW"
        else:
            assert False

    v1md5sum = get_pod_data_md5sum(core_api,
                                   pod1_name,
                                   volume1_data_path)

    assert v1md5sum == volume1_md5sum

    client.update(node1, allowScheduling=False)
    client.update(node3, allowScheduling=True, evictionRequested=False)

    volume2_name = volume_name + "-2"
    volume2_size = str(500 * Mi)
    volume2_data_path = "/data/test"
    pv2_name = volume2_name + "-pv"
    pvc2_name = volume2_name + "-pvc"
    pod2_name = volume2_name + "-pod"
    pod2 = copy.deepcopy(pod)

    pod2['metadata']['name'] = pod2_name

    pod2['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": pvc2_name
        }
    }]

    pod2['spec']['nodeSelector'] = \
        {"kubernetes.io/hostname": node2.name}

    volume2 = create_and_check_volume(client,
                                      volume2_name,
                                      num_of_replicas=2,
                                      size=volume2_size)

    create_pv_for_volume(client, core_api, volume2, pv2_name)
    create_pvc_for_volume(client, core_api, volume2, pvc2_name)

    create_and_wait_pod(core_api, pod2)
    volume2 = wait_for_volume_healthy(client, volume2_name)

    volume2_replica1 = volume2.replicas[0]
    volume2_replica2 = volume2.replicas[1]

    assert volume2_replica1.mode == "RW"
    assert volume2_replica2.mode == "RW"
    assert volume2_replica1.running is True
    assert volume2_replica2.running is True

    write_pod_volume_random_data(core_api,
                                 pod2_name,
                                 volume2_data_path,
                                 DATA_SIZE_IN_MB_2)

    volume2_md5sum = get_pod_data_md5sum(core_api,
                                         pod2_name,
                                         volume2_data_path)

    client.update(node1, allowScheduling=True)
    client.update(node2, allowScheduling=False, evictionRequested=True)

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume2_name, 3)

    wait_for_volume_replica_count(client, volume1_name, 2)
    wait_for_volume_replica_count(client, volume2_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    volume2 = client.by_id_volume(volume2_name)

    for v1replica in volume1.replicas:
        assert v1replica.hostId == node1.name or \
               v1replica.hostId == node3.name

    for v2replica in volume2.replicas:
        assert v2replica.hostId == node1.name or \
               v2replica.hostId == node3.name

    delete_and_wait_pod(core_api, pod1_name)
    delete_and_wait_pod(core_api, pod2_name)

    wait_for_volume_detached(client, volume1_name)
    wait_for_volume_detached(client, volume2_name)

    client.update(node2, allowScheduling=True, evictionRequested=False)
    client.update(node1, allowScheduling=False, evictionRequested=True)

    wait_for_volume_healthy_no_frontend(client, volume1_name)
    wait_for_volume_healthy_no_frontend(client, volume2_name)

    wait_for_volume_replica_count(client, volume1_name, 3)
    wait_for_volume_replica_count(client, volume2_name, 3)

    wait_for_volume_replica_count(client, volume1_name, 2)
    wait_for_volume_replica_count(client, volume2_name, 2)

    volume1 = client.by_id_volume(volume1_name)
    volume2 = client.by_id_volume(volume2_name)

    for v1replica in volume1.replicas:
        assert v1replica.hostId == node2.name or \
               v1replica.hostId == node3.name

    for v2replica in volume2.replicas:
        assert v2replica.hostId == node2.name or \
               v2replica.hostId == node3.name

    wait_for_volume_detached(client, volume1_name)
    wait_for_volume_detached(client, volume2_name)

    create_and_wait_pod(core_api, pod1)
    create_and_wait_pod(core_api, pod2)

    wait_for_volume_healthy(client, volume2_name)
    wait_for_volume_healthy(client, volume2_name)

    v1md5sum = get_pod_data_md5sum(core_api,
                                   pod1_name,
                                   volume1_data_path)

    assert v1md5sum == volume1_md5sum

    v2md5sum = get_pod_data_md5sum(core_api,
                                   pod2_name,
                                   volume2_data_path)

    assert v2md5sum == volume2_md5sum
