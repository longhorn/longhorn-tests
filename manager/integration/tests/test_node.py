import common
import pytest
import os
import subprocess
import time
import yaml

from random import choice
from string import ascii_lowercase, digits

from common import core_api, client, csi_pv, pvc, pod_make  # NOQA
from common import Gi, SIZE, CONDITION_STATUS_FALSE, \
    CONDITION_STATUS_TRUE, DEFAULT_DISK_PATH, DIRECTORY_PATH, \
    DISK_CONDITION_SCHEDULABLE, DISK_CONDITION_READY, \
    NODE_CONDITION_SCHEDULABLE
from common import get_core_api_client, get_longhorn_api_client, \
    get_self_host_id
from common import SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE, \
    SETTING_DEFAULT_DATA_PATH, \
    SETTING_CREATE_DEFAULT_DISK_LABELED_NODES, \
    DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE, \
    SETTING_DISABLE_SCHEDULING_ON_CORDONED_NODE, \
    SETTING_DETACH_MANUALLY_ATTACHED_VOLUMES_WHEN_CORDONED
from common import get_volume_endpoint
from common import get_update_disks
from common import wait_for_disk_status, wait_for_disk_update, \
    wait_for_disk_conditions, wait_for_node_tag_update, \
    cleanup_node_disks, wait_for_disk_storage_available, \
    wait_for_disk_uuid, wait_for_node_schedulable_condition

from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import volume_name # NOQA
from common import settings_reset # NOQA
from common import Mi, DATA_SIZE_IN_MB_2
from common import create_and_wait_pod
from common import get_pod_data_md5sum
from common import wait_for_volume_healthy
from common import wait_for_volume_replica_count
from common import is_replica_available
from common import delete_and_wait_pod
from common import wait_for_volume_detached
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import create_volume, cleanup_volume_by_name
from common import create_host_disk, cleanup_host_disks
from common import set_node_cordon
from common import set_node_tags, set_node_scheduling
from common import set_node_scheduling_eviction
from common import update_node_disks
from common import update_setting
from common import SETTING_NODE_DRAIN_POLICY, DATA_SIZE_IN_MB_3
from common import make_deployment_with_pvc # NOQA
from common import prepare_host_disk, wait_for_volume_degraded
from common import create_deployment_and_write_data
from common import wait_scheduling_failure

from backupstore import set_random_backupstore # NOQA
from concurrent.futures import ThreadPoolExecutor, TimeoutError


CREATE_DEFAULT_DISK_LABEL = "node.longhorn.io/create-default-disk"
CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG = "config"
DEFAULT_DISK_CONFIG_ANNOTATION = "node.longhorn.io/default-disks-config"
DEFAULT_NODE_TAG_ANNOTATION = "node.longhorn.io/default-node-tags"
SMALL_DISK_SIZE = (2 * 1024 * 1024)
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
    node = set_node_scheduling(client, node, allowScheduling=False, retry=True)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", False)
    assert not node.allowScheduling
    node = client.by_id_node(lht_hostId)
    assert not node.allowScheduling

    node = set_node_scheduling(client, node, allowScheduling=True, retry=True)
    node = common.wait_for_node_update(client, lht_hostId,
                                       "allowScheduling", True)
    assert node.allowScheduling
    node = client.by_id_node(lht_hostId)
    assert node.allowScheduling


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_disk_update(client):  # NOQA
    """
    Test update node disks

    The test will use Longhorn to create disks on the node.

    1. Get the current node
    2. Try to delete all the disks. It should fail due to scheduling is enabled
    3. Create two disks `disk1` and `disk2`, attach them to the current node.
    4. Add two disks to the current node.
    5. Verify two extra disks have been added to the node
    6. Disable the two disks' scheduling, and set StorageReserved
    7. Update the two disks.
    8. Validate all the disks properties.
    9. Delete other two disks. Validate deletion works.
    """
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    disks = node.disks

    # test delete disk exception
    with pytest.raises(Exception) as e:
        update_node_disks(client, node.name, disks={}, retry=True)
    assert "disable the disk" in str(e.value)

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
    update_disk["disk1"] = disk1
    update_disk["disk2"] = disk2

    # save disks to node
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node.disks) == len(update_disk)
    node = client.by_id_node(lht_hostId)
    assert len(node.disks) == len(update_disk)

    # update disk
    disks = node.disks
    update_disk = get_update_disks(disks)
    for disk in update_disk.values():
        # keep default disk for other tests
        if disk.path == disk_path1 or disk.path == disk_path2:
            disk.allowScheduling = False
            disk.storageReserved = SMALL_DISK_SIZE
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    disks = node.disks
    # wait for node controller to update disk status
    for name, disk in iter(disks.items()):
        if disk.path == disk_path1 or disk.path == disk_path2:
            wait_for_disk_status(client, lht_hostId, name,
                                 "allowScheduling", False)
            wait_for_disk_status(client, lht_hostId, name,
                                 "storageReserved", SMALL_DISK_SIZE)
            wait_for_disk_storage_available(client, lht_hostId, name,
                                            disk_path1)

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
    remain_disk = {}
    for name, disk in update_disk.items():
        if disk.path != disk_path1 and disk.path != disk_path2:
            remain_disk[name] = disk
    node = update_node_disks(client, node.name, disks=remain_disk, retry=True)
    node = wait_for_disk_update(client, lht_hostId,
                                len(remain_disk))
    assert len(node.disks) == len(remain_disk)
    # cleanup disks
    cleanup_host_disks(client, 'vol-disk-1', 'vol-disk-2')


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
    # delete all disks on each node
    for node in nodes:
        disks = node.disks
        # set allowScheduling to false
        for name, disk in iter(disks.items()):
            disk.allowScheduling = False
        update_disks = get_update_disks(disks)
        node = update_node_disks(client, node.name, disks=update_disks,
                                 retry=True)
        for name, disk in iter(node.disks.items()):
            # wait for node controller update disk status
            wait_for_disk_status(client, node.name, name,
                                 "allowScheduling", False)
            wait_for_disk_status(client, node.name, name,
                                 "storageScheduled", 0)

        node = client.by_id_node(node.name)
        for name, disk in iter(node.disks.items()):
            assert not disk.allowScheduling
        node = update_node_disks(client, node.name, disks={}, retry=True)
        node = common.wait_for_disk_update(client, node.name, 0)
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
    5. Set `Disable Scheduling On Cordoned Node` to false.
    6. Automatically the scheduler should creates three replicas
       from step 5 failure.
    7. Attach this volume, write data to it and check the data.
    8. Delete the test volume.
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

    # Node schedulable condition should be false
    assert node.conditions[NODE_CONDITION_SCHEDULABLE]["status"] ==  \
        "False"
    assert node.conditions[NODE_CONDITION_SCHEDULABLE]["reason"] == \
        "KubernetesNodeCordoned"

    # Create a volume
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=SIZE,
                         numberOfReplicas=len(nodes))
    common.wait_for_volume_detached(client, vol_name)

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
    cleanup_volume_by_name(client, vol_name)

@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_replica_scheduler_large_volume_fit_small_disk(client):  # NOQA
    """
    Test replica scheduler: not schedule a large volume to small disk

    1. Create a host disk `small_disk` and attach i to the current node.
    2. Create a new large volume.
    3. Verify the volume wasn't scheduled on the `small_disk`.
    """
    nodes = client.list_node()
    # create a small size disk on current node
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    small_disk = {"path": small_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks["small-disks"] = small_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
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

    cleanup_volume_by_name(client, vol_name)

    # cleanup test disks
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk = disks[unexpected_disk["fsid"]]
    disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = wait_for_disk_status(client, lht_hostId,
                                unexpected_disk["fsid"],
                                "allowScheduling", False)
    disks = node.disks
    disk = disks[unexpected_disk["fsid"]]
    assert not disk.allowScheduling
    disks.pop(unexpected_disk["fsid"])
    update_disks = get_update_disks(disks)
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    cleanup_host_disks(client, 'vol-small')


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
    nodes = client.list_node()
    lht_hostId = get_self_host_id()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for _, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_node_disk[node.name] = expect_disk
            disk.storageReserved = disk.storageMaximum
        update_disks = get_update_disks(disks)
        update_node_disks(client, node.name, disks=update_disks, retry=True)

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
        for disk in update_disks.values():
            disk.storageReserved = \
                disk.storageMaximum - needed_for_scheduling
        node = update_node_disks(client, node.name, disks=update_disks,
                                 retry=True)
        disks = node.disks
        for name, disk in iter(disks.items()):
            wait_for_disk_status(client, node.name,
                                 name, "storageReserved",
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
        assert replica.diskID == expect_disk.diskUUID
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume_by_name(client, vol_name)


@pytest.mark.node  # NOQA
def test_replica_scheduler_update_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: update overprovisioning setting

    1. Set setting `overprovisioning` to 0. (disable all scheduling)
    2. Create a new volume. Verify volume's `scheduled` condition is false.
    3. Set setting `over provisioning` to 200%.
    4. Verify volume's `scheduled` condition now become true.
    5. Attach the volume.
    6. Make sure every replica landed on different nodes's default disk.
    """
    nodes = client.list_node()
    lht_hostId = get_self_host_id()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for _, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_node_disk[node.name] = expect_disk

    # set storage over provisioning percentage to 0
    # to test all replica couldn't be scheduled
    update_setting(client, SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, "0")

    vol_name = common.generate_volume_name()
    volume = client.create_volume(name=vol_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # set storage over provisioning percentage to 200
    update_setting(client, SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE, "200")

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
        assert replica.diskID == expect_disk.diskUUID
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume_by_name(client, vol_name)


@pytest.mark.node  # NOQA
def test_replica_scheduler_exceed_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: exceeding overprovisioning parameter

    1. Set setting `overprovisioning` to 100 (default)
    2. Update every disks to set 1G available for scheduling
    3. Try to schedule a volume of 2G. Volume scheduled condition should be
    false
    """
    # test exceed over provisioning limit couldn't be scheduled
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            disk.storageReserved = \
                disk.storageMaximum - 1*Gi
        update_disks = get_update_disks(disks)
        node = update_node_disks(client, node.name, disks=update_disks,
                                 retry=True)
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


@pytest.mark.node  # NOQA
def test_replica_scheduler_just_under_over_provisioning(client):  # NOQA
    """
    Test replica scheduler: just under overprovisioning parameter

    1. Set setting `overprovisioning` to 100 (default)
    2. Get the maximum size of all the disks
    3. Create a volume using maximum_size - 2MiB as the volume size.
    4. Volume scheduled condition should be true.
    5. Make sure every replica landed on different nodes's default disk.
    """
    lht_hostId = get_self_host_id()
    nodes = client.list_node()
    expect_node_disk = {}
    max_size_array = []
    for node in nodes:
        disks = node.disks
        for _, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
                expect_node_disk[node.name] = expect_disk
                max_size_array.append(disk.storageMaximum)
            disk.storageReserved = 0
            update_disks = get_update_disks(disks)
            node = update_node_disks(client, node.name, disks=update_disks,
                                     retry=True)
            disks = node.disks
            for fsid, disk in iter(disks.items()):
                wait_for_disk_status(client, node.name,
                                     fsid, "storageReserved", 0)

    # volume size is round up by 2MiB
    max_size = min(max_size_array) - 2 * 1024 * 1024
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
        assert replica.diskID == expect_disk.diskUUID
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume_by_name(client, vol_name)


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

    nodes = client.list_node()
    expect_node_disk = {}
    for node in nodes:
        disks = node.disks
        for _, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                expect_disk = disk
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
        assert replica.diskID == expect_disk.diskUUID
        assert expect_disk.path in replica.dataPath
        node_hosts = list(filter(lambda x: x != id, node_hosts))
    assert len(node_hosts) == 0

    # clean volume and disk
    cleanup_volume_by_name(client, vol_name)


@pytest.mark.node  # NOQA
def test_node_controller_sync_storage_scheduled(client):  # NOQA
    """
    Test node controller sync storage scheduled correctly

    1. Wait until no disk has anything scheduled
    2. Create a volume with "number of nodes" replicas
    3. Confirm that each disks now has "volume size" scheduled
    4. Confirm every disks are still schedulable.
    """
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
            disk_found = False
            if replica.hostId == node.name:
                for _, disk in iter(disks.items()):
                    if replica.diskID == disk.diskUUID:
                        disk_found = True
                        conditions = disk.conditions
                        assert disk.storageScheduled == SMALL_DISK_SIZE
                        assert \
                            conditions[DISK_CONDITION_SCHEDULABLE]["status"] \
                            == CONDITION_STATUS_TRUE
                        break
                assert disk_found

    # clean volumes
    cleanup_volume_by_name(client, vol_name)


@pytest.mark.coretest   # NOQA
@pytest.mark.node  # NOQA
@pytest.mark.mountdisk  # NOQA
def test_node_controller_sync_storage_available(client):  # NOQA
    """
    Test node controller sync storage available correctly

    1. Create a host disk `test_disk` on the current node
    2. Write 1MiB data to the disk, and run `sync`
    3. Verify the disk `storageAvailable` will update to include the file
    """
    lht_hostId = get_self_host_id()
    # create a disk to test storageAvailable
    node = client.by_id_node(lht_hostId)
    test_disk_path = create_host_disk(client, "vol-test", SIZE, lht_hostId)
    test_disk = {"path": test_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks["test-disk"] = test_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = common.wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node.disks) == len(update_disks)

    # write specified byte data into disk
    test_file_path = os.path.join(test_disk_path, TEST_FILE)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    cmd = ['dd', 'if=/dev/zero', 'of=' + test_file_path, 'bs=1M', 'count=1']
    subprocess.check_call(cmd)
    subprocess.check_call(['sync', test_file_path])
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    # wait for node controller update disk status
    expect_disk = {}
    for fsid, disk in iter(disks.items()):
        if disk.path == test_disk_path:
            node = wait_for_disk_storage_available(client, lht_hostId,
                                                   fsid, test_disk_path)
            expect_disk = node.disks[fsid]
            break

    free, total = common.get_host_disk_size(test_disk_path)
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
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = wait_for_disk_status(client, lht_hostId, wait_fsid,
                                "allowScheduling", False)
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == test_disk_path:
            disks.pop(fsid)
            break
    update_disks = get_update_disks(disks)
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node.disks) == len(update_disks)
    cleanup_host_disks(client, 'vol-test')


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


@pytest.mark.node  # NOQA
@pytest.mark.mountdisk # NOQA
def test_node_default_disk_added_back_with_extra_disk_unmounted(client):  # NOQA
    """
    [Node] Test adding default disk back with extra disk is unmounted
    on the node

    1. Clean up all disks on node 1.
    2. Recreate the default disk with "allowScheduling" disabled for
       node 1.
    3. Create a Longhorn volume and attach it to node 1.
    4. Use the Longhorn volume as an extra host disk and
       enable "allowScheduling" of the default disk for node 1.
    5. Verify all disks on node 1 are "Schedulable".
    6. Delete the default disk on node 1.
    7. Unmount the extra disk on node 1.
       And wait for it becoming "Unschedulable".
    8. Create and add the default disk back on node 1.
    9. Wait and verify the default disk should become "Schedulable".
    10. Mount extra disk back on node 1.
    11. Wait and verify this extra disk should become "Schedulable".
    12. Delete the host disk `extra_disk`.
    """
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    node = client.by_id_node(lht_hostId)

    # Create a default disk with `allowScheduling` disabled
    # so that there is no volume replica using this disk later.
    default_disk = {"default-disk":
                    {"path": DEFAULT_DISK_PATH,
                     "allowScheduling": False,
                     "storageReserved": SMALL_DISK_SIZE}}
    node = update_node_disks(client, node.name, default_disk, retry=True)
    node = wait_for_disk_update(client, node.name, 1)
    wait_for_disk_status(client, node.name, "default-disk",
                         "allowScheduling", False)
    assert len(node.disks) == 1

    # Create a volume and attached it to this node.
    # This volume will be used as an extra host disk later.
    extra_disk_volume_name = 'extra-disk'
    extra_disk_path = create_host_disk(client, extra_disk_volume_name,
                                       str(Gi), lht_hostId)
    extra_disk = {"path": extra_disk_path, "allowScheduling": True}

    update_disk = get_update_disks(node.disks)
    update_disk["default-disk"].allowScheduling = True
    update_disk["extra-disk"] = extra_disk
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node.disks) == len(update_disk)

    # Make sure all disks are schedulable
    for name, disk in node.disks.items():
        wait_for_disk_conditions(client, node.name,
                                 name, DISK_CONDITION_SCHEDULABLE,
                                 CONDITION_STATUS_TRUE)

    # Delete default disk
    update_disk = get_update_disks(node.disks)
    update_disk["default-disk"].allowScheduling = False
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    remain_disk = {}
    for name, disk in node.disks.items():
        if disk.path == extra_disk_path:
            remain_disk[name] = disk
    node = update_node_disks(client, node.name, disks=remain_disk, retry=True)
    node = wait_for_disk_update(client, lht_hostId,
                                len(remain_disk))
    assert len(node.disks) == len(remain_disk)

    # Umount the extra disk and wait for unschedulable condition
    common.umount_disk(extra_disk_path)
    for name, disk in node.disks.items():
        wait_for_disk_conditions(client, node.name,
                                 name, DISK_CONDITION_SCHEDULABLE,
                                 CONDITION_STATUS_FALSE)

    # Add default disk back and wait for schedulable condition
    default_disk = {"path": DEFAULT_DISK_PATH, "allowScheduling": True,
                    "storageReserved": SMALL_DISK_SIZE}
    update_disk = get_update_disks(node.disks)
    update_disk["default-disk"] = default_disk
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    for name, disk in node.disks.items():
        if disk.path == DEFAULT_DISK_PATH:
            wait_for_disk_conditions(client, node.name,
                                     name, DISK_CONDITION_SCHEDULABLE,
                                     CONDITION_STATUS_TRUE)

    # Mount extra disk back
    disk_volume = client.by_id_volume(extra_disk_volume_name)
    dev = get_volume_endpoint(disk_volume)
    common.mount_disk(dev, extra_disk_path)

    # Check all the disks should be at schedulable condition
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    for name, disk in node.disks.items():
        wait_for_disk_conditions(client, node.name,
                                 name, DISK_CONDITION_SCHEDULABLE,
                                 CONDITION_STATUS_TRUE)

    # Remove extra disk.
    update_disk = get_update_disks(node.disks)
    update_disk[extra_disk_volume_name].allowScheduling = False
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))

    update_disk = get_update_disks(node.disks)
    remain_disk = {}
    for name, disk in update_disk.items():
        if disk.path != extra_disk_path:
            remain_disk[name] = disk
    node = update_node_disks(client, node.name, disks=remain_disk, retry=True)
    node = wait_for_disk_update(client, lht_hostId,
                                len(remain_disk))

    cleanup_host_disks(client, extra_disk_volume_name)


@pytest.mark.node  # NOQA
@pytest.mark.mountdisk  # NOQA
def test_node_umount_disk(client):  # NOQA
    """
    [Node] Test umount and delete the extra disk on the node

    1. Create host disk and attach it to the current node
    2. Disable the existing disk's scheduling on the current node
    3. Add the disk to the current node
    4. Wait for node to recognize the disk
    5. Create a volume with "number of nodes" replicas
    6. Umount the disk from the host
    7. Verify the disk `READY` condition become false.
        1. Maximum and available storage become zero.
        2. No change to storage scheduled and storage reserved.
    8. Try to delete the extra disk, it should fail due to need to disable
    scheduling first
    9. Update the other disk on the node to be allow scheduling. Disable the
    scheduling for the extra disk
    10. Mount the disk back
    11. Verify the disk `READY` condition become true, and other states
    12. Umount and delete the disk.
    """

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
    for disk in update_disk.values():
        disk.allowScheduling = False
    # add new disk for node
    update_disk["disk1"] = disk1
    # save disks to node
    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disk))
    assert len(node.disks) == len(update_disk)
    node = client.by_id_node(lht_hostId)
    assert len(node.disks) == len(update_disk)

    disks = node.disks
    # wait for node controller to update disk status
    for name, disk in iter(disks.items()):
        if disk.path == disk_path1:
            wait_for_disk_status(client, lht_hostId, name,
                                 "allowScheduling", True)
            wait_for_disk_status(client, lht_hostId, name,
                                 "storageReserved", SMALL_DISK_SIZE)
            _, total = common.get_host_disk_size(disk_path1)
            wait_for_disk_status(client, lht_hostId, name,
                                 "storageMaximum", total)
            wait_for_disk_storage_available(client, lht_hostId, name,
                                            disk_path1)

    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for key, disk in iter(disks.items()):
        if disk.path == disk_path1:
            assert disk.allowScheduling
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == 0
            free, total = common.get_host_disk_size(disk_path1)
            assert disk.storageMaximum == total
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
            wait_for_disk_status(client, lht_hostId,
                                 fsid, "storageScheduled", 0)
            wait_for_disk_conditions(client, lht_hostId, fsid,
                                     DISK_CONDITION_READY,
                                     CONDITION_STATUS_FALSE)

    # check result
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    update_disks = {}
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            assert disk.allowScheduling
            assert disk.storageMaximum == 0
            assert disk.storageAvailable == 0
            assert disk.storageReserved == SMALL_DISK_SIZE
            assert disk.storageScheduled == 0
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
            update_disks[fsid] = disk

    # delete umount disk exception
    with pytest.raises(Exception) as e:
        update_node_disks(client, node.name, disks=update_disks, retry=True)
    assert "disable the disk" in str(e.value)

    # update other disks
    disks = node.disks
    for fsid, disk in iter(disks.items()):
        if disk.path == disk_path1:
            disk.allowScheduling = False
        else:
            disk.allowScheduling = True
    test_update = get_update_disks(disks)
    node = update_node_disks(client, node.name, disks=test_update, retry=True)
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
    cleanup_volume_by_name(client, vol_name)
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
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)
    cmd = ['rm', '-r', mount_path]
    subprocess.check_call(cmd)


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
    nodes = client.list_node()
    lht_hostId = get_self_host_id()

    # set soft antiaffinity setting to true
    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="true")

    node = client.by_id_node(lht_hostId)
    extra_disk_path = create_host_disk(client, "extra-disk",
                                       "10G", lht_hostId)
    extra_disk = {"path": extra_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks["extra-disk"] = extra_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
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
        update_node_disks(client, node.name, disks=update_disks, retry=True)
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
        assert os.listdir(data_path)

    cleanup_volume_by_name(client, vol_name)

    # data path should be gone due to the cleanup of replica
    for data_path in data_paths:
        try:
            os.listdir(data_path)
            raise AssertionError(f"data path {data_path} should be gone")
        except FileNotFoundError:
            pass

    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk = disks[extra_disk_fsid]
    disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
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
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))

    cleanup_host_disks(client, 'extra-disk')


@pytest.mark.node  # NOQA
def test_node_default_disk_labeled(client, core_api, random_disk_path,  reset_default_disk_label,  reset_disk_settings):  # NOQA
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
    wait_for_disk_update(client, cases["labeled"], 1)

    # Check each case.
    node = client.by_id_node(cases["disk_exists"])
    assert len(node.disks) == 1
    assert node.disks[list(node.disks)[0]].path == \
        DEFAULT_DISK_PATH

    node = client.by_id_node(cases["labeled"])
    assert len(node.disks) == 1
    assert node.disks[list(node.disks)[0]].path == \
        random_disk_path

    # Remove the Disk from the Node used for this test case so we can have the
    # fixtures clean up after.
    setting = client.by_id_setting(SETTING_CREATE_DEFAULT_DISK_LABELED_NODES)
    client.update(setting, value="false")
    cleanup_node_disks(client, node.id)

    node = client.by_id_node(cases["unlabeled"])
    assert len(node.disks) == 0


@pytest.mark.node  # NOQA
def test_node_config_annotation(client, core_api, reset_default_disk_label, reset_disk_and_tag_annotations, reset_disk_settings):  # NOQA
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


@pytest.mark.node  # NOQA
def test_node_config_annotation_invalid(client, core_api, reset_default_disk_label, reset_disk_and_tag_annotations, reset_disk_settings):  # NOQA
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
        os.path.join(DEFAULT_DISK_PATH, "engine-binaries"),
        os.path.join(DEFAULT_DISK_PATH, "replicas")
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
                    '"storageReserved":1024,' +
                    '"name":"' + os.path.basename(host_dirs[0]) + '"},' +
                    '{"path":"' + host_dirs[1] + '",' +
                    '"allowScheduling":false,' +
                    '"storageReserved": 1024,' +
                    '"name":"' + os.path.basename(host_dirs[1]) + '"}]'
            }
        }
    })

    # Longhorn shouldn't apply the invalid disk annotation.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    node = client.by_id_node(node_name)
    assert len(node.disks) == 0
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
    node = client.by_id_node(node_name)
    assert len(node.disks) == 0
    assert not node.tags

    # Case1.3: Disk and tag update should work fine even if there is
    # invalid disk annotation.
    disk = {"default-disk": {"path": DEFAULT_DISK_PATH,
            "allowScheduling": True}}
    update_node_disks(client, node.name, disks=disk, retry=True)
    node = wait_for_disk_update(client, node_name, 1)
    assert len(node.disks) == 1
    for fsid, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 0
        assert disk.diskUUID != ""
        assert not disk.tags
        break
    disk_uuid = disk.diskUUID
    set_node_tags(client, node, tags=["tag1", "tag2"], retry=True)
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
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    update_node_disks(client, node.name, disks={}, retry=True)
    node = wait_for_disk_uuid(client, node_name, disk_uuid)
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
    set_node_tags(client, node, tags=[], retry=True)
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
    disk = {"default-disk": {"path": DEFAULT_DISK_PATH,
            "allowScheduling": True, "storageReserved": 1024}}
    update_node_disks(client, node.name, disks=disk, retry=True)
    node = wait_for_disk_update(client, node_name, 1)
    assert len(node.disks) == 1
    for _, disk in iter(node.disks.items()):
        assert disk.path == DEFAULT_DISK_PATH
        assert disk.allowScheduling is True
        assert disk.storageReserved == 1024
        assert not disk.tags
        break
    set_node_tags(client, node, tags=["tag3", "tag4"], retry=True)
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
    set_node_tags(client, node, tags=[], retry=True)
    wait_for_node_tag_update(client, node_name, ["storage"])

    # Case7: Same disk name in annotation shouldn't intervene the node
    # controller

    # clean up any existing disk and create one disk for node
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk_path1 = create_host_disk(client, 'vol-disk-1',
                                  str(Gi), lht_hostId)

    # patch label and annotations to the node
    core_api.patch_node(lht_hostId, {
        "metadata": {
            "labels": {
                CREATE_DEFAULT_DISK_LABEL:
                    CREATE_DEFAULT_DISK_LABEL_VALUE_CONFIG
            },
            "annotations": {
                DEFAULT_DISK_CONFIG_ANNOTATION:
                    '[{"path":"' + DEFAULT_DISK_PATH +
                    '","allowScheduling":true,' +
                    '"storageReserved": 1024,"tags": ["ssd", "fast"],' +
                    '"name":"same-name"},' +
                    '{"path":"' + disk_path1 +
                    '","allowScheduling":true,' +
                    '"storageReserved":1024,"name":"same-name"}]'
            }
        }
    })

    # same disk name shouldn't be applied to Longhorn.
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    node = client.by_id_node(lht_hostId)
    assert len(node.disks) == 0

    # do cleanup.
    cleanup_host_disks(client, 'vol-disk-1')


@pytest.mark.node  # NOQA
def test_node_config_annotation_missing(client, core_api, reset_default_disk_label, reset_disk_and_tag_annotations, reset_disk_settings):  # NOQA
    """
    Test node labeled for configuration but no annotation

    1. Set setting `create default disk labeled nodes` to true
    2. Set the config label on node 0 but leave annotation empty
    3. Verify disk update works.
    4. Verify tag update works
    5. Verify using tag annotation for configuration works.
    6. After remove the tag annotation, verify unset tag node works fine.
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
    node = client.by_id_node(node_name)
    assert len(node.disks) == 1
    update_disks = {}
    for name, disk in iter(node.disks.items()):
        disk.allowScheduling = False
        disk.storageReserved = 0
        disk.tags = ["original"]
        update_disks[name] = disk
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = wait_for_disk_status(client, node_name, name,
                                "storageReserved", 0)
    assert len(node.disks) == 1
    assert disk.allowScheduling is False
    assert disk.storageReserved == 0
    assert set(disk.tags) == {"original"}

    # Case2: Tag update with disk set should work fine
    set_node_tags(client, node, tags=["tag0"], retry=True)
    wait_for_node_tag_update(client, node_name, ["tag0"])
    set_node_tags(client, node, tags=[], retry=True)
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
    set_node_tags(client, node, tags=[], retry=True)
    wait_for_node_tag_update(client, node_name, [])

    # Case4: Tag update with disk unset should work fine
    cleanup_node_disks(client, node_name)
    set_node_tags(client, node, tags=["tag2"], retry=True)
    wait_for_node_tag_update(client, node_name, ["tag2"])
    set_node_tags(client, node, tags=[], retry=True)
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
def test_replica_scheduler_rebuild_restore_is_too_big(set_random_backupstore, client):  # NOQA
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
        a suitable disk for rebuilding replica, since the replica with the
        existing data cannot fit in the small disk
    6. Enable the scheduling for other disks, disable scheduling for small disk
    7. Verify the volume reports `scheduled = true`. And verify the data.
    8. Cleanup the volume.
    9. Verify the restored volume reports `scheduled = true`.
    10. Wait for the restored volume to complete restoration, then check data.

    """
    nodes = client.list_node()
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    small_disk_path = create_host_disk(client, "vol-small",
                                       SIZE, lht_hostId)
    small_disk = {"path": small_disk_path, "allowScheduling": False}
    update_disks = get_update_disks(node.disks)
    update_disks["small-disk"] = small_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)

    # volume is same size as the small disk
    volume_size = SIZE
    vol_name = common.generate_volume_name()
    client.create_volume(name=vol_name, size=str(volume_size),
                         numberOfReplicas=len(nodes))
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, vol_name)

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)

    # disable all the scheduling except for the small disk
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                disk.allowScheduling = False
            elif disk.path == small_disk_path:
                disk.allowScheduling = True
        update_disks = get_update_disks(disks)
        update_node_disks(client, node.name, disks=update_disks, retry=True)

    data = {'len': int(int(SIZE) * 0.9), 'pos': 0}
    data['content'] = common.generate_random_data(data['len'])
    _, b, _, _ = common.create_backup(client, vol_name, data)

    # cannot schedule for restore volume
    restore_name = common.generate_volume_name()
    client.create_volume(name=restore_name, size=SIZE,
                         numberOfReplicas=1,
                         fromBackup=b.url)
    r_vol = common.wait_for_volume_condition_scheduled(client, restore_name,
                                                       "status",
                                                       CONDITION_STATUS_FALSE)

    # cannot schedule due to all disks except for the small disk is disabled
    # And the small disk won't have enough space after taking the replica
    volume = volume.replicaRemove(name=volume.replicas[0].name)
    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)

    # enable the scheduling
    nodes = client.list_node()
    for node in nodes:
        disks = node.disks
        for fsid, disk in iter(disks.items()):
            if disk.path == DEFAULT_DISK_PATH:
                disk.allowScheduling = True
            elif disk.path == small_disk_path:
                disk.allowScheduling = False
        update_disks = get_update_disks(disks)
        update_node_disks(client, node.name, disks=update_disks, retry=True)

    volume = common.wait_for_volume_condition_scheduled(client, vol_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)

    common.check_volume_data(volume, data, check_checksum=False)

    cleanup_volume_by_name(client, vol_name)

    r_vol = common.wait_for_volume_condition_scheduled(client, restore_name,
                                                       "status",
                                                       CONDITION_STATUS_TRUE)
    r_vol = common.wait_for_volume_restoration_completed(client, restore_name)
    r_vol = common.wait_for_volume_detached(client, restore_name)
    r_vol.attach(hostId=lht_hostId)
    r_vol = common.wait_for_volume_healthy(client, restore_name)

    common.check_volume_data(r_vol, data, check_checksum=False)

    cleanup_volume_by_name(client, restore_name)

    # cleanup test disks
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    update_disks = {}
    for name, disk in iter(disks.items()):
        if disk.path != small_disk_path:
            update_disks[name] = disk
    update_node_disks(client, node.name, disks=update_disks, retry=True)

    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    cleanup_host_disks(client, 'vol-small')


@pytest.mark.node  # NOQA
def test_disk_migration(client):  # NOQA
    """
    1. Disable the node soft anti-affinity.
    2. Create a new host disk.
    3. Disable the default disk and add the extra disk with scheduling enabled
       for the current node.
    4. Launch a Longhorn volume with 1 replica.
       Then verify the only replica is scheduled to the new disk.
    5. Write random data to the volume then verify the data.
    6. Detach the volume.
    7. Unmount then remount the disk to another path. (disk migration)
    8. Create another Longhorn disk based on the migrated path.
    9. Verify the Longhorn disk state.
       - The Longhorn disk added before the migration should
         become "unschedulable".
       - The Longhorn disk created after the migration should
         become "schedulable".
    10. Verify the replica DiskID and the path is updated.
    11. Attach the volume. Then verify the state and the data.
    """
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")

    lht_hostId = get_self_host_id()

    node = client.by_id_node(lht_hostId)
    update_disks = get_update_disks(node.disks)
    for fsid, disk in iter(update_disks.items()):
        disk.allowScheduling = False
        update_disks[fsid] = disk
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    disk_vol_name = 'vol-disk'
    extra_disk_name = "extra-disk"
    extra_disk_path = create_host_disk(
        client, disk_vol_name, str(Gi), lht_hostId)
    extra_disk_manifest = \
        {"path": extra_disk_path, "allowScheduling": True, "tags": ["extra"]}
    update_disks[extra_disk_name] = extra_disk_manifest
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)
    node = wait_for_disk_conditions(
        client, node.name,
        extra_disk_name, DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)
    extra_disk = node.disks[extra_disk_name]

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
    assert volume.replicas[0].diskID == extra_disk.diskUUID
    assert volume.replicas[0].diskPath == extra_disk.path

    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    volume.detach()
    volume = common.wait_for_volume_detached(client, vol_name)

    # Mount the volume disk to another path
    common.cleanup_host_disk(extra_disk_path)

    migrated_disk_path = os.path.join(
        DIRECTORY_PATH, disk_vol_name+"-migrated")
    dev = get_volume_endpoint(client.by_id_volume(disk_vol_name))
    common.mount_disk(dev, migrated_disk_path)

    node = client.by_id_node(lht_hostId)
    update_disks = get_update_disks(node.disks)
    migrated_disk_name = "migrated-disk"
    migrated_disk_manifest = \
        {"path": migrated_disk_path, "allowScheduling": True,
         "tags": ["extra"]}
    update_disks[migrated_disk_name] = migrated_disk_manifest
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))
    assert len(node.disks) == len(update_disks)
    wait_for_disk_conditions(
        client, node.name,
        extra_disk_name, DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_FALSE)
    node = wait_for_disk_conditions(
        client, node.name,
        migrated_disk_name, DISK_CONDITION_SCHEDULABLE, CONDITION_STATUS_TRUE)
    migrated_disk = node.disks[migrated_disk_name]
    assert migrated_disk.diskUUID == extra_disk.diskUUID

    replica_migrated = False
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(vol_name)
        assert len(volume.replicas) == 1
        replica = volume.replicas[0]
        assert replica.hostId == lht_hostId
        if replica.diskID == migrated_disk.diskUUID and \
                replica.diskPath == migrated_disk.path:
            replica_migrated = True
            break
        time.sleep(RETRY_INTERVAL)
    assert replica_migrated

    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, vol_name)
    common.check_volume_data(volume, data)

    cleanup_volume_by_name(client, vol_name)


def test_node_eviction(client, core_api, csi_pv, pvc, pod_make, volume_name): # NOQA
    """
    Test node eviction (assuming this is a 3 nodes cluster)

    Case: node 1, 3 to node 1, 2 eviction
    1. Disable scheduling on node 2.
    2. Create pv, pvc, pod with volume of 2 replicas.
    3. Write some data and get the checksum.
    4. Set 'Eviction Requested' to 'false' and enable scheduling on node 2.
    5. Set 'Eviction Requested' to 'true' and disable scheduling on node 3.
    6. Check volume 'healthy' and wait for replicas running on node 1 and 2.
    7. Check volume data checksum.
    """
    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # schedule replicas to node 1, 3
    set_node_scheduling(client, node2, allowScheduling=False, retry=True)

    data_path = "/data/test"
    pod_name, _, _, created_md5sum = \
        common.prepare_pod_with_data_in_mb(client, core_api, csi_pv,
                                           pvc, pod_make, volume_name,
                                           num_of_replicas=2,
                                           data_path=data_path)

    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name, node3.name])

    # replica now running on node 1, 3
    # enable node 2
    set_node_scheduling_eviction(client,
                                 node2,
                                 allowScheduling=True,
                                 evictionRequested=False,
                                 retry=True)
    # disable node 3 to have replica schedule to node 1, 2
    set_node_scheduling_eviction(client,
                                 node3,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)

    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name, node2.name])

    expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert expect_md5sum == created_md5sum


def test_node_eviction_no_schedulable_node(client, core_api, csi_pv, pvc, pod_make, volume_name, settings_reset): # NOQA
    """
    Test node eviction (assuming this is a 3 nodes cluster)

    1. Disable scheduling on node 3.
    2. Create pv, pvc, pod with volume of 2 replicas.
    3. Write some data and get the checksum.
    4. Disable scheduling and set 'Eviction Requested' to 'true' on node 1.
    5. Volume should be failed to schedule new replica.
    6. Set 'Eviction Requested' to 'false' to cancel node 1 eviction.
    7. Check replica has the same hostID.
    8. Check volume data checksum.
    """
    nodes = client.list_node()
    node1 = nodes[0]
    node3 = nodes[2]

    # schedule replicas to node 1, 2
    set_node_scheduling(client, node3, allowScheduling=False, retry=True)

    data_path = "/data/test"
    pod_name, _, _, created_md5sum = \
        common.prepare_pod_with_data_in_mb(client, core_api, csi_pv,
                                           pvc, pod_make, volume_name,
                                           data_path=data_path,
                                           num_of_replicas=2)

    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2

    created_replicas = {}
    for r in volume.replicas:
        assert r.mode == "RW"
        assert r.running is True
        created_replicas[r.name] = r["hostId"]

    set_node_scheduling_eviction(client,
                                 node1,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)
    try:
        wait_for_volume_replica_count(client, volume_name, 3)
        raise AssertionError("no new replica should be created")
    except AssertionError:
        pass

    wait_scheduling_failure(client, volume_name)

    set_node_scheduling_eviction(client,
                                 node1,
                                 allowScheduling=False,
                                 evictionRequested=False,
                                 retry=True)

    volume = client.by_id_volume(volume_name)
    for r in volume.replicas:
        if r.name in created_replicas:
            assert r.running is True
            assert r.mode == "RW"
            assert r.hostId == created_replicas[r.name]
        else:
            assert False

    expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert expect_md5sum == created_md5sum


def test_node_eviction_soft_anti_affinity(client, core_api, csi_pv, pvc, pod_make, volume_name, settings_reset): # NOQA
    """
    Test node eviction (assuming this is a 3 nodes cluster)

    Case #1: node 1,2 to node 2 eviction
    1. Disable scheduling on node 3.
    2. Create pv, pvc, pod with volume of 2 replicas.
    3. Write some data and get the checksum.
    7. Set 'Eviction Requested' to 'true' and disable scheduling on node 1.
    8. Set 'Replica Node Level Soft Anti-Affinity' to 'true'.
    9. Check volume 'healthy' and wait for replicas running on node 2
    Case #2: node 2 to node 1, 3 eviction
    10. Enable scheduling on node 1 and 3.
    11. Set 'Replica Node Level Soft Anti-Affinity' to 'false'.
    12. Set 'Eviction Requested' to 'true' and disable scheduling on node 2.
    13. Check volume 'healthy' and wait for replicas running on node 1 and 3.
    14. Check volume data checksum.
    """
    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # schedule replicas to node 1, 2
    set_node_scheduling(client, node3, allowScheduling=False, retry=True)

    data_path = "/data/test"
    pod_name, _, _, created_md5sum = \
        common.prepare_pod_with_data_in_mb(client, core_api, csi_pv,
                                           pvc, pod_make, volume_name,
                                           num_of_replicas=2,
                                           data_path=data_path)

    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name, node2.name])

    set_node_scheduling_eviction(client,
                                 node1,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)

    # enable anti-affinity allow the 2 replicas running on node 2
    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="true")

    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node2.name],
                                      anti_affinity=True)

    # replicas now all running on node 2, enable schedule on node 3
    set_node_scheduling(client, node3, allowScheduling=True, retry=True)
    # replicas now all running on node 2, enable schedule on node 1
    set_node_scheduling(client, node1, allowScheduling=True, retry=True)

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    # replica now all running on node 2, disable node 2 schedule to
    # schedule to node 1, 3
    set_node_scheduling_eviction(client,
                                 node2,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)
    common.wait_for_volume_healthy(client, volume_name)

    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name, node3.name],
                                      chk_vol_healthy=False)

    expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert expect_md5sum == created_md5sum


def test_node_eviction_multiple_volume(client, core_api, csi_pv, pvc, pod_make, volume_name): # NOQA
    """
    Test node eviction (assuming this is a 3 nodes cluster)

    1. Disable scheduling on node 1.
    2. Create pv, pvc, pod with volume 1 of 2 replicas.
    3. Write some data to volume 1 and get the checksum.
    2. Create pv, pvc, pod with volume 2 of 2 replicas.
    3. Write some data to volume 2 and get the checksum.
    4. Set 'Eviction Requested' to 'true' and disable scheduling on node 2.
    5. Set 'Eviction Requested' to 'false' and enable scheduling on node 1.
    6. Check volume 'healthy' and wait for replicas running on node 1 and 3.
    7. delete pods to detach volume 1 and 2.
    8. Set 'Eviction Requested' to 'false' and enable scheduling on node 2.
    9. Set 'Eviction Requested' to 'true' and disable scheduling on node 1.
    10. Wait for replicas running on node 2 and 3.
    11. Create pod 1 and pod 2. Volume 1 and 2 will be automatically
        attached.
    12. Check volume 'healthy', and replicas running on node 2 and 3.
    13. Check volume data checksum for volume 1 and 2.
    """
    nodes = client.list_node()

    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # schedule replicas to node 2, 3
    set_node_scheduling(client, node1, allowScheduling=False, retry=True)

    data_path = "/data/test"

    # create volume 1
    volume1_name = volume_name + "-1"
    pod1_name, _, pvc1_name, created_md5sum1 = \
        common.prepare_pod_with_data_in_mb(client, core_api, csi_pv,
                                           pvc, pod_make, volume1_name,
                                           num_of_replicas=2,
                                           data_path=data_path)

    common.wait_for_replica_scheduled(client, volume1_name,
                                      to_nodes=[node2.name, node3.name])

    # create volume 2
    volume2_name = volume_name + "-2"
    pod2_name, _, pvc2_name, created_md5sum2 = \
        common.prepare_pod_with_data_in_mb(client, core_api, csi_pv,
                                           pvc, pod_make, volume2_name,
                                           volume_size=str(500 * Mi),
                                           num_of_replicas=2,
                                           data_size_in_mb=DATA_SIZE_IN_MB_2,
                                           data_path=data_path)

    common.wait_for_replica_scheduled(client, volume2_name,
                                      to_nodes=[node2.name, node3.name])

    # replica running on node 2, 3
    # disable node 2
    set_node_scheduling_eviction(client,
                                 node2,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)
    # enable node 1 to have scheduled to 1, 3
    set_node_scheduling(client, node1, allowScheduling=True, retry=True)

    common.wait_for_replica_scheduled(client, volume1_name,
                                      to_nodes=[node1.name, node3.name])
    common.wait_for_replica_scheduled(client, volume2_name,
                                      to_nodes=[node1.name, node3.name])

    delete_and_wait_pod(core_api, pod1_name)
    delete_and_wait_pod(core_api, pod2_name)

    wait_for_volume_detached(client, volume1_name)
    wait_for_volume_detached(client, volume2_name)

    # replica running on node 1, 3
    # enable node 2
    set_node_scheduling_eviction(client,
                                 node2,
                                 allowScheduling=True,
                                 evictionRequested=False,
                                 retry=True)
    # disable node 1 to schedule to node 2, 3
    set_node_scheduling_eviction(client,
                                 node1,
                                 allowScheduling=False,
                                 evictionRequested=True,
                                 retry=True)

    common.wait_for_replica_scheduled(client, volume1_name,
                                      to_nodes=[node2.name, node3.name],
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)
    common.wait_for_replica_scheduled(client, volume2_name,
                                      to_nodes=[node2.name, node3.name],
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)

    pod1 = pod_make(name=pod1_name)
    pod1['spec']['volumes'] = [common.create_pvc_spec(pvc1_name)]

    pod2 = pod_make(name=pod2_name)
    pod2['spec']['volumes'] = [common.create_pvc_spec(pvc2_name)]

    create_and_wait_pod(core_api, pod1)
    create_and_wait_pod(core_api, pod2)

    common.wait_for_replica_scheduled(client, volume1_name,
                                      to_nodes=[node2.name, node3.name])
    common.wait_for_replica_scheduled(client, volume2_name,
                                      to_nodes=[node2.name, node3.name])

    expect_md5sum = get_pod_data_md5sum(core_api, pod1_name, data_path)
    assert expect_md5sum == created_md5sum1

    expect_md5sum = get_pod_data_md5sum(core_api, pod2_name, data_path)
    assert expect_md5sum == created_md5sum2


def test_disk_eviction_with_node_level_soft_anti_affinity_disabled(client, # NOQA
                                                                   volume_name, # NOQA
                                                                   request, # NOQA
                                                                   settings_reset, # NOQA
                                                                   reset_disk_settings): # NOQA
    """
    Steps:

    1. Disable the setting `Replica Node Level Soft Anti-affinity`
    2. Create a volume. Make sure there is a replica on each worker node.
    3. Write some data to the volume.
    4. Add a new schedulable disk to node-1.
    5. Disable the scheduling and enable eviction for the old disk on node-1.
    6. Verify that the replica on the old disk move to the new disk
    7. Make replica count as 1, Delete the replicas on other 2 nodes.
       Verify the data from the volume.
    """
    # Step 1
    node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(node_soft_anti_affinity_setting, value="false")

    # Step 2
    nodes = client.list_node()
    volume = client.create_volume(name=volume_name,
                                  size=SIZE, numberOfReplicas=len(nodes))
    common.wait_for_volume_detached(client, volume_name)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # Step 3
    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    # Step 4
    node = client.by_id_node(lht_hostId)
    test_disk_path = create_host_disk(client, "vol-test", str(Gi), lht_hostId)
    test_disk = {"path": test_disk_path, "allowScheduling": True}

    update_disks = get_update_disks(node.disks)
    update_disks["test-disk"] = test_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = common.wait_for_disk_update(client, lht_hostId, len(update_disks))
    assert len(node.disks) == len(update_disks)

    # Step 5
    for disk in update_disks.values():
        if disk["path"] != test_disk_path:
            disk.allowScheduling = False
            disk.evictionRequested = True

    node = update_node_disks(client, node.name, disks=update_disks, retry=True)

    # Step 6
    replica_path = test_disk_path + '/replicas'
    assert os.path.isdir(replica_path)

    # Since https://github.com/longhorn/longhorn-manager/pull/2138, the node
    # controller is responsible for triggering replica eviction. If the timing
    # of the node controller and node monitor are off, the node controller
    # may take extra time to do so. Wait for evidence eviction is in progress
    # before proceeding.
    wait_for_volume_replica_count(client, volume.name,
                                  volume.numberOfReplicas + 1)

    for i in range(common.RETRY_COMMAND_COUNT):
        if len(os.listdir(replica_path)) > 0:
            break
        time.sleep(common.RETRY_EXEC_INTERVAL)
    assert len(os.listdir(replica_path)) > 0
    volume = wait_for_volume_healthy(client, volume_name)

    # Step 7
    replica_count = 1
    volume.updateReplicaCount(replicaCount=replica_count)
    volume = wait_for_volume_healthy(client, volume_name)

    done = False
    for i in range(RETRY_COUNTS):
        other_replicas_deleted = True
        new_replica_available = False
        volume = client.by_id_volume(volume_name)
        for r in volume.replicas:
            if r.hostId != lht_hostId:
                try:
                    volume.replicaRemove(name=r.name)
                except Exception:
                    other_replicas_deleted = False
                    break
            else:
                if r.diskPath == test_disk_path and is_replica_available(r):
                    new_replica_available = True

        if other_replicas_deleted and \
                len(volume.replicas) == 1 and new_replica_available:
            done = True
            break
        time.sleep(RETRY_INTERVAL)
    assert done

    common.check_volume_data(volume, data)

    # Remove volumes let no volume mounted to extra disk
    def finalizer():
        common.cleanup_all_volumes(client)

    request.addfinalizer(finalizer)


def drain_node(core_api, node): # NOQA    
    set_node_cordon(core_api, node.id, True)

    command = [
        "kubectl",
        "drain",
        node.id,
        "--ignore-daemonsets",
        "--delete-emptydir-data",
        "--grace-period=-1"
    ]

    subprocess.run(command, check=True)


def get_replica_detail(replica_name):
    """
    Get allreplica information by this function
    """
    command = ["kubectl", "get",
               "replicas.longhorn.io",
               "-n",
               "longhorn-system",
               replica_name,
               "-o",
               "yaml"]
    output = subprocess.check_output(command, text=True)
    replica_info = yaml.safe_load(output)
    return replica_info


def check_node_auto_evict_state(client, target_node, expect_state): # NOQA
    def get_specific_node(client, target_node):
        nodes = client.list_node()
        for node in nodes:
            if node.id == target_node.id:
                return node

    for i in range(RETRY_COUNTS):
        node = get_specific_node(client, target_node)
        if node.autoEvicting is expect_state:
            break
        time.sleep(RETRY_INTERVAL)
    assert node.autoEvicting is expect_state


def check_replica_evict_state(client, volume_name, node, expect_state): # NOQA
    volume = client.by_id_volume(volume_name)
    for replica in volume.replicas:
        if replica.hostId == node.id:
            replica_name = replica.name
            break

    replica_info = get_replica_detail(replica_name)
    eviction_requested = replica_info["spec"]["evictionRequested"]
    assert eviction_requested is expect_state


def wait_drain_complete(future, timeout, copmpleted=True):
    """
    Wait concurrent.futures object complete in a duration
    """
    def stop_drain_process():
        """
        Both future.cancel() and executer.shutdown(wait=False) can not really
        stop the drain process.
        Use this function to stop drain process
        """
        command = ["pkill", "-f", "kubectl drain"]
        subprocess.check_output(command, text=True)

    thread_timeout = timeout
    try:
        future.result(timeout=thread_timeout)
        drain_complete = True
    except TimeoutError:
        print("drain node thread exceed timeout ({})s".format(thread_timeout))
        drain_complete = False
        stop_drain_process()
    finally:
        assert drain_complete is copmpleted


def make_replica_on_specific_node(client, volume_name, node): # NOQA
    volume = client.by_id_volume(volume_name)
    volume.updateReplicaCount(replicaCount=1)
    for replica in volume.replicas:
        if replica.hostId != node.id:
            volume.replicaRemove(name=replica.name)
    wait_for_volume_replica_count(client, volume_name, 1)


def get_all_replica_name(client, volume_name): # NOQA
    volume_replicas = []
    volume = client.by_id_volume(volume_name)
    for replica in volume.replicas:
        volume_replicas.append(replica.name)

    return volume_replicas


def check_all_replicas_evict_state(client, volume_name, expect_state): # NOQA
    volume = client.by_id_volume(volume_name)
    for replica in volume.replicas:
        replica_info = get_replica_detail(replica.name)
        eviction_requested = replica_info["spec"]["evictionRequested"]
        assert eviction_requested is expect_state


def test_drain_with_block_for_eviction_success(client, # NOQA
                                               core_api, # NOQA
                                               volume_name, # NOQA
                                               make_deployment_with_pvc): # NOQA
    """
    Test drain completes after evicting replica with node-drain-policy
    block-for-eviction

    1. Set `node-drain-policy` to `block-for-eviction`.
    2. Create a volume.
    3. Ensure (through soft anti-affinity, low replica count, and/or enough
       disks) that an evicted replica of the volume can be scheduled elsewhere.
    4. Write data to the volume.
    5. Drain a node one of the volume's replicas is scheduled to.
    6. While the drain is ongoing:
       - Verify that `node.status.autoEvicting == true`.
       - Optionally verify that `replica.spec.evictionRequested == true`.
    7. Verify the drain completes.
    8. Uncordon the node.
    9. Verify the replica on the drained node has moved to a different one.
    10. Verify that `node.status.autoEvicting == false`.
    11. Verify that `replica.spec.evictionRequested == false`.
    12. Verify the volume's data.
    """
    host_id = get_self_host_id()
    nodes = client.list_node()
    evict_nodes = [node for node in nodes if node.id != host_id][:2]
    evict_source_node = evict_nodes[0]
    evict_target_node = evict_nodes[1]

    # Step 1
    setting = client.by_id_setting(
        SETTING_NODE_DRAIN_POLICY)
    client.update(setting, value="block-for-eviction")

    # Step 2, 3, 4
    volume, pod, checksum, _ = create_deployment_and_write_data(client,
                                                                core_api,
                                                                make_deployment_with_pvc, # NOQA
                                                                volume_name,
                                                                str(1 * Gi),
                                                                3,
                                                                DATA_SIZE_IN_MB_3, host_id) # NOQA

    # Make replica not locate on eviction target node
    volume.updateReplicaCount(replicaCount=2)
    for replica in volume.replicas:
        if replica.hostId == evict_target_node.id:
            volume.replicaRemove(name=replica.name)
            break

    wait_for_volume_replica_count(client, volume_name, 2)

    # Step 5
    # drain eviction source node
    executor = ThreadPoolExecutor(max_workers=5)
    future = executor.submit(drain_node, core_api, evict_source_node)

    # Step 6
    check_replica_evict_state(client, volume_name, evict_source_node, True)
    check_node_auto_evict_state(client, evict_source_node, True)

    # Step 7
    wait_drain_complete(future, 60)
    wait_for_volume_replica_count(client, volume_name, 2)

    # Step 8
    set_node_cordon(core_api, evict_source_node.id, False)

    # Step 9
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2
    for replica in volume.replicas:
        assert replica.hostId != evict_source_node.id

    # Stpe 10
    check_node_auto_evict_state(client, evict_source_node, False)

    # Step 11
    check_replica_evict_state(client, volume_name, evict_target_node, False)

    # Step 12
    data_path = data_path = '/data/test'
    test_data_checksum = get_pod_data_md5sum(core_api,
                                             pod,
                                             data_path)
    assert checksum == test_data_checksum


def test_drain_with_block_for_eviction_if_contains_last_replica_success(client, # NOQA
                                                                        core_api, # NOQA
                                                                        make_deployment_with_pvc): # NOQA
    """
    Test drain completes after evicting replicas with node-drain-policy
    block-for-eviction-if-contains-last-replica

    1. Set `node-drain-policy` to
       `block-for-eviction-if-contains-last-replica`.
    2. Create one volume with a single replica and another volume with three
       replicas.
    3. Ensure (through soft anti-affinity, low replica count, and/or enough
    disks) that evicted replicas of both volumes can be scheduled elsewhere.
    4. Write data to the volumes.
    5. Drain a node both volumes have a replica scheduled to.
    6. While the drain is ongoing:
       - Verify that the volume with three replicas becomes degraded.
       - Verify that `node.status.autoEvicting == true`.
       - Optionally verify that `replica.spec.evictionRequested == true` on the
         replica for the volume that only has one.
       - Optionally verify that `replica.spec.evictionRequested == false` on
         the replica for the volume that has three.
    7. Verify the drain completes.
    8. Uncordon the node.
    9. Verify the replica for the volume with one replica has moved to a
       different node.
    10. Verify the replica for the volume with three replicas has not moved.
    11. Verify that `node.status.autoEvicting == false`.
    12. Verify that `replica.spec.evictionRequested == false` on all replicas.
    13. Verify the the data in both volumes.
    """
    host_id = get_self_host_id()
    nodes = client.list_node()
    evict_nodes = [node for node in nodes if node.id != host_id][:2]
    evict_source_node = evict_nodes[0]
    # Create extra disk on current node
    node = client.by_id_node(host_id)
    disks = node.disks

    disk_volume_name = 'vol-disk'
    disk_volume = client.create_volume(name=disk_volume_name,
                                       size=str(2 * Gi),
                                       numberOfReplicas=1,
                                       dataLocality="strict-local")
    disk_volume = wait_for_volume_detached(client, disk_volume_name)

    disk_volume.attach(hostId=host_id)
    disk_volume = wait_for_volume_healthy(client, disk_volume_name)
    disk_path = prepare_host_disk(get_volume_endpoint(disk_volume),
                                  disk_volume_name)
    disk = {"path": disk_path, "allowScheduling": True}

    update_disk = get_update_disks(disks)
    update_disk["disk1"] = disk

    node = update_node_disks(client, node.name, disks=update_disk, retry=True)
    node = wait_for_disk_update(client, host_id, len(update_disk))
    assert len(node.disks) == len(update_disk)

    # Step 1
    setting = client.by_id_setting(
        SETTING_NODE_DRAIN_POLICY)
    client.update(setting, value="block-for-eviction-if-contains-last-replica")

    # Step 2, 3
    volume1_name = "vol-1"
    volume2_name = "vol-2"
    volume1, pod1, checksum1, _ = create_deployment_and_write_data(client,
                                                                   core_api,
                                                                   make_deployment_with_pvc, # NOQA
                                                                   volume1_name, # NOQA
                                                                   str(1 * Gi),
                                                                   3,
                                                                   DATA_SIZE_IN_MB_3, # NOQA
                                                                   host_id) # NOQA
    volume2, pod2, checksum2, _ = create_deployment_and_write_data(client,
                                                                   core_api,
                                                                   make_deployment_with_pvc,  # NOQA
                                                                   volume2_name, # NOQA
                                                                   str(1 * Gi),
                                                                   3,
                                                                   DATA_SIZE_IN_MB_3, # NOQA
                                                                   host_id) # NOQA
    # Make volume 1 replica only located on evict_source_node
    make_replica_on_specific_node(client, volume1_name, evict_source_node)
    volume2_replicas = get_all_replica_name(client, volume2_name)

    # Step 5
    executor = ThreadPoolExecutor(max_workers=5)
    future = executor.submit(drain_node, core_api, evict_source_node)

    # Step 6
    check_replica_evict_state(client, volume1_name, evict_source_node, True)
    check_node_auto_evict_state(client, evict_source_node, True)

    volume2 = wait_for_volume_degraded(client, volume2_name)
    check_all_replicas_evict_state(client, volume2_name, False)

    # Step 7
    wait_drain_complete(future, 60)

    # Step 8
    set_node_cordon(core_api, evict_source_node.id, False)

    # Step 9
    volume1 = client.by_id_volume(volume1_name)
    wait_for_volume_replica_count(client, volume1_name, 1)
    for replica in volume1.replicas:
        assert replica.hostId != evict_source_node.id

    # Step 10
    # Verify volume2 replicas not moved by check replica name
    # stored before the node drain
    volume2 = wait_for_volume_healthy(client, volume2_name)
    for replica in volume2.replicas:
        assert replica.name in volume2_replicas

    # Step 11
    check_node_auto_evict_state(client, evict_source_node, False)

    # Step 12
    check_all_replicas_evict_state(client, volume1_name, False)
    check_all_replicas_evict_state(client, volume2_name, False)

    # Step 13
    data_path = '/data/test'
    test_data_checksum1 = get_pod_data_md5sum(core_api,
                                              pod1,
                                              data_path)
    assert checksum1 == test_data_checksum1

    test_data_checksum2 = get_pod_data_md5sum(core_api,
                                              pod2,
                                              data_path)
    assert checksum2 == test_data_checksum2


def test_drain_with_block_for_eviction_failure(client, # NOQA
                                               core_api, # NOQA
                                               volume_name, # NOQA
                                               make_deployment_with_pvc): # NOQA
    """
    Test drain never completes with node-drain-policy block-for-eviction

    1. Set `node-drain-policy` to `block-for-eviction`.
    2. Create a volume.
    3. Ensure (through soft anti-affinity, high replica count, and/or not
       enough disks) that an evicted replica of the volume cannot be scheduled
       elsewhere.
    4. Write data to the volume.
    5. Drain a node one of the volume's replicas is scheduled to.
    6. While the drain is ongoing:
       - Verify that `node.status.autoEvicting == true`.
       - Verify that `replica.spec.evictionRequested == true`.
    7. Verify the drain never completes.
    8. Stop the drain, check volume is healthy and data correct
    """
    host_id = get_self_host_id()
    nodes = client.list_node()
    evict_nodes = [node for node in nodes if node.id != host_id][:2]
    evict_source_node = evict_nodes[0]

    # Step 1
    setting = client.by_id_setting(
        SETTING_NODE_DRAIN_POLICY)
    client.update(setting, value="block-for-eviction")

    # Step 2, 3, 4
    volume, pod, checksum, _ = create_deployment_and_write_data(client,
                                                                core_api,
                                                                make_deployment_with_pvc, # NOQA
                                                                volume_name,
                                                                str(1 * Gi),
                                                                3,
                                                                DATA_SIZE_IN_MB_3, host_id) # NOQA

    # Step 5
    executor = ThreadPoolExecutor(max_workers=5)
    future = executor.submit(drain_node, core_api, evict_source_node)

    # Step 6
    check_replica_evict_state(client, volume_name, evict_source_node, True)
    check_node_auto_evict_state(client, evict_source_node, True)

    # Step 7
    wait_drain_complete(future, 90, False)

    # Step 8
    set_node_cordon(core_api, evict_source_node.id, False)
    wait_for_volume_healthy(client, volume_name)
    data_path = '/data/test'
    test_data_checksum = get_pod_data_md5sum(core_api,
                                             pod,
                                             data_path)
    assert checksum == test_data_checksum


@pytest.mark.node  # NOQA
def test_auto_detach_volume_when_node_is_cordoned(client, core_api, volume_name):  # NOQA
    """
    Test auto detach volume when node is cordoned

    1. Set `detach-manually-attached-volumes-when-cordoned` to `false`.
    2. Create a volume and attached to the node through API (manually).
    3. Cordon the node.
    4. Set `detach-manually-attached-volumes-when-cordoned` to `true`.
    5. Volume will be detached automatically.
    """

    # Set `Detach Manually Attached Volumes When Cordoned` to false
    detach_manually_attached_volumes_when_cordoned = \
        client.by_id_setting(
            SETTING_DETACH_MANUALLY_ATTACHED_VOLUMES_WHEN_CORDONED)
    client.update(detach_manually_attached_volumes_when_cordoned,
                  value="false")

    # Create a volume
    volume = client.create_volume(name=volume_name,
                                  size=SIZE,
                                  numberOfReplicas=3)
    volume = common.wait_for_volume_detached(client,
                                             volume_name)
    assert volume.restoreRequired is False

    # Attach to the node
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.restoreRequired is False

    # Cordon the node
    set_node_cordon(core_api, host_id, True)

    # Volume is still attached for a while
    time.sleep(NODE_UPDATE_WAIT_INTERVAL)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.restoreRequired is False

    # Set `Detach Manually Attached Volumes When Cordoned` to true
    client.update(detach_manually_attached_volumes_when_cordoned, value="true")

    # Volume should be detached
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume.restoreRequired is False

    # Delete the Volume
    client.delete(volume)
    common.wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume().data
    assert len(volumes) == 0

@pytest.mark.skip(reason="TODO")  # NOQA
def test_do_not_react_to_brief_kubelet_restart():
    """
    Test the node controller ignores Ready == False due to KubeletNotReady for
    ten seconds before reacting.

    Repeat the following five times:
    1. Verify status.conditions[type == Ready] == True for the Longhorn node we
       are running on.
    2. Kill the kubelet process (e.g. `pkill kubelet`).
    3. Verify status.conditions[type == Ready] != False for the Longhorn node
       we are running on at any point for at least ten seconds.
    """
