import pytest

import os
import subprocess
import time
import random
import yaml

import common
from common import client, random_labels, volume_name, clients  # NOQA
from common import core_api, apps_api, pod, statefulset   # NOQA
from common import SIZE, EXPAND_SIZE
from common import check_device_data, write_device_random_data
from common import check_volume_data, write_volume_random_data
from common import get_self_host_id, volume_valid
from common import iscsi_login, iscsi_logout
from common import wait_for_volume_status
from common import wait_for_volume_delete
from common import wait_for_snapshot_purge
from common import generate_volume_name
from common import get_volume_endpoint, get_volume_engine
from common import check_volume_endpoint
from common import activate_standby_volume, check_volume_last_backup
from common import create_pv_for_volume, create_pvc_for_volume
from common import create_and_wait_pod, delete_and_wait_pod
from common import delete_and_wait_pvc, delete_and_wait_pv
from common import CONDITION_STATUS_FALSE, CONDITION_STATUS_TRUE
from common import RETRY_COUNTS, RETRY_INTERVAL, RETRY_COMMAND_COUNT
from common import DEFAULT_POD_TIMEOUT, DEFAULT_POD_INTERVAL
from common import cleanup_volume, create_and_check_volume, create_backup
from common import DEFAULT_VOLUME_SIZE
from common import Gi, Mi, Ki
from common import wait_for_volume_detached
from common import create_pvc_spec
from common import generate_random_data, write_volume_data
from common import VOLUME_RWTEST_SIZE
from common import write_pod_volume_data
from common import find_backup, find_replica_for_backup
from common import wait_for_backup_completion
from common import create_storage_class
from common import wait_for_backup_restore_completed
from common import wait_for_volume_restoration_completed
from common import read_volume_data
from common import pvc_name  # NOQA
from common import storage_class  # NOQA
from common import pod_make, csi_pv, pvc  # NOQA
from common import create_snapshot
from common import offline_expand_attached_volume
from common import wait_for_dr_volume_expansion
from common import check_block_device_size, get_device_checksum
from common import wait_for_volume_expansion, wait_for_expansion_error_clear
from common import fail_replica_expansion, wait_for_expansion_failure
from common import fix_replica_expansion_failure
from common import wait_for_volume_restoration_start
from common import write_pod_volume_random_data, get_pod_data_md5sum
from common import prepare_pod_with_data_in_mb, exec_command_in_pod
from common import crash_replica_processes
from common import wait_for_volume_condition_scheduled
from common import wait_for_volume_condition_restore
from common import wait_for_volume_condition_toomanysnapshots
from common import wait_for_volume_degraded, wait_for_volume_healthy
from common import wait_for_volume_faulted
from common import VOLUME_FRONTEND_BLOCKDEV, VOLUME_FRONTEND_ISCSI
from common import VOLUME_CONDITION_SCHEDULED
from common import DATA_SIZE_IN_MB_1
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL
from common import CONDITION_REASON_SCHEDULING_FAILURE
from common import delete_backup, get_backupstores
from common import delete_backup_volume
from common import BACKUP_BLOCK_SIZE
from common import assert_backup_state
from common import wait_for_backup_delete
from common import VOLUME_FIELD_ROBUSTNESS, VOLUME_FIELD_READY
from common import VOLUME_ROBUSTNESS_HEALTHY, VOLUME_ROBUSTNESS_FAULTED
from common import DATA_SIZE_IN_MB_2, DATA_SIZE_IN_MB_3
from common import wait_for_backup_to_start
from common import SETTING_DEFAULT_LONGHORN_STATIC_SC
from common import wait_for_backup_volume
from common import create_and_wait_statefulset
from common import create_backup_from_volume_attached_to_pod
from common import restore_backup_and_get_data_checksum
from common import write_volume_dev_random_mb_data
from common import get_volume_dev_mb_data_md5sum
from common import VOLUME_HEAD_NAME
from common import set_node_scheduling
from common import SETTING_FAILED_BACKUP_TTL
from common import wait_for_volume_creation
from common import create_host_disk, get_update_disks, update_node_disks
from common import wait_for_disk_status, wait_for_rebuild_start, wait_for_rebuild_complete # NOQA
from common import RETRY_BACKUP_COUNTS
from common import LONGHORN_NAMESPACE
from common import wait_for_snapshot_count
from common import make_deployment_with_pvc # NOQA
from common import wait_for_volume_option_trim_auto_removing_snapshots
from common import FS_TYPE_EXT4, FS_TYPE_XFS
from common import DEFAULT_BACKUP_COMPRESSION_METHOD
from common import BACKUP_COMPRESSION_METHOD_LZ4
from common import BACKUP_COMPRESSION_METHOD_GZIP
from common import BACKUP_COMPRESSION_METHOD_NONE

from backupstore import backupstore_delete_volume_cfg_file
from backupstore import backupstore_cleanup
from backupstore import backupstore_count_backup_block_files
from backupstore import backupstore_create_dummy_in_progress_backup
from backupstore import backupstore_delete_dummy_in_progress_backup
from backupstore import backupstore_create_file
from backupstore import backupstore_delete_file
from backupstore import set_random_backupstore  # NOQA
from backupstore import backupstore_get_backup_volume_prefix
from backupstore import set_backupstore_url, set_backupstore_credential_secret, set_backupstore_poll_interval  # NOQA
from backupstore import reset_backupstore_setting  # NOQA
from backupstore import set_backupstore_s3, backupstore_get_secret  # NOQA

from kubernetes import client as k8sclient

BACKUPSTORE = get_backupstores()


@pytest.mark.coretest   # NOQA
def test_hosts(client):  # NOQA
    """
    Check node name and IP
    """
    hosts = client.list_node()
    for host in hosts:
        assert host.name is not None
        assert host.address is not None

    host_id = []
    for i in range(0, len(hosts)):
        host_id.append(hosts.data[i].name)

    host0_from_i = {}
    for i in range(0, len(hosts)):
        if len(host0_from_i) == 0:
            host0_from_i = client.by_id_node(host_id[0])
        else:
            assert host0_from_i.name == \
                client.by_id_node(host_id[0]).name
            assert host0_from_i.address == \
                client.by_id_node(host_id[0]).address


@pytest.mark.coretest   # NOQA
def test_settings(client):  # NOQA
    """
    Check input for settings
    """

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
            assert name+" with invalid value " in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert name+" with invalid value " in \
                   str(e.value)
            setting = client.update(setting, value="200")
            assert setting.value == "200"
            setting = client.by_id_setting(name)
            assert setting.value == "200"
        elif name == common.SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE:
            with pytest.raises(Exception) as e:
                client.update(setting, value="300")
            assert name+" with invalid value " in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="-30")
            assert name+" with invalid value " in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert name+" with invalid value " in \
                   str(e.value)
            setting = client.update(setting, value="30")
            assert setting.value == "30"
            setting = client.by_id_setting(name)
            assert setting.value == "30"
        elif name == common.SETTING_BACKUP_TARGET:
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue$test")
            assert name+" with invalid value " in \
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
            assert name+" with invalid value " in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="testvalue")
            assert name+" with invalid value " in \
                   str(e.value)
            with pytest.raises(Exception) as e:
                client.update(setting, value="21")
            assert name+" with invalid value " in \
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
def test_volume_basic(client, volume_name):  # NOQA
    """
    Test basic volume operations:

    1. Check volume name and parameter
    2. Create a volume and attach to the current node, then check volume states
    3. Check soft anti-affinity rule
    4. Write then read back to check volume data
    """
    volume_basic_test(client, volume_name)


def volume_basic_test(client, volume_name, backing_image=""):  # NOQA
    num_hosts = len(client.list_node())
    num_replicas = 3

    with pytest.raises(Exception):
        volume = client.create_volume(name="wrong_volume-name-1.0", size=SIZE,
                                      numberOfReplicas=2)
        volume = client.create_volume(name="wrong_volume-name", size=SIZE,
                                      numberOfReplicas=2)
        volume = client.create_volume(name="wrong_volume-name", size=SIZE,
                                      numberOfReplicas=2,
                                      frontend="invalid_frontend")

    volume = create_and_check_volume(client, volume_name, num_replicas, SIZE,
                                     backing_image)
    assert volume.restoreRequired is False

    def validate_volume_basic(expected, actual):
        assert actual.name == expected.name
        assert actual.size == expected.size
        assert actual.numberOfReplicas == expected.numberOfReplicas
        assert actual.frontend == VOLUME_FRONTEND_BLOCKDEV
        assert actual.backingImage == backing_image
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
    assert volume.restoreRequired is False

    volumeByName = client.by_id_volume(volume_name)
    validate_volume_basic(volume, volumeByName)
    check_volume_endpoint(volumeByName)

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
    check_volume_endpoint(volumes[0])

    volume = client.by_id_volume(volume_name)
    volume_rw_test(get_volume_endpoint(volume))

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume.restoreRequired is False

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume().data
    assert len(volumes) == 0


def test_volume_iscsi_basic(client, volume_name):  # NOQA
    """
    Test basic volume operations with iscsi frontend

    1. Create and attach a volume with iscsi frontend
    2. Check the volume endpoint and connect it using the iscsi
    initator on the node.
    3. Write then read back volume data for validation

    """
    volume_iscsi_basic_test(client, volume_name)


def volume_iscsi_basic_test(client, volume_name, backing_image=""):  # NOQA
    host_id = get_self_host_id()
    volume = create_and_check_volume(client, volume_name, 3, SIZE,
                                     backing_image, VOLUME_FRONTEND_ISCSI)
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
    assert volumes[0].backingImage == volume.backingImage
    endpoint = get_volume_endpoint(volumes[0])

    try:
        dev = iscsi_login(endpoint)
        volume_rw_test(dev)
    finally:
        iscsi_logout(endpoint)

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_snapshot(client, volume_name, backing_image=""):  # NOQA
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
    snapshot_test(client, volume_name, backing_image)


def snapshot_test(client, volume_name, backing_image):  # NOQA
    volume = create_and_check_volume(client, volume_name,
                                     backing_image=backing_image)

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
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    check_volume_endpoint(volume)

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


def test_backup_status_for_unavailable_replicas(set_random_backupstore, client, volume_name):    # NOQA
    """
    Test backup status for unavailable replicas

    Context:

    We want to make sure that during the backup creation, once the responsible
    replica gone, the backup should in Error state and with the error message.

    Setup:

    1. Create a volume and attach to the current node
    2. Run the test for all the available backupstores

    Steps:

    1. Create a backup of volume
    2. Find the replica for that backup
    3. Disable scheduling on the node of that replica
    4. Delete the replica
    5. Verify backup status with Error state and with an error message
    6. Create a new backup
    7. Verify new backup was successful
    8. Cleanup (delete backups, delete volume)
    """
    backup_status_for_unavailable_replicas_test(
        client, volume_name, size=3 * Gi)


def backup_status_for_unavailable_replicas_test(client, volume_name,  # NOQA
                                                size, backing_image=""):  # NOQA
    volume = create_and_check_volume(client, volume_name, 2, str(size),
                                     backing_image)

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # write data to the volume
    volume_endpoint = get_volume_endpoint(volume)

    # Take snapshots without overlapping
    data_size = size/Mi
    write_volume_dev_random_mb_data(
        volume_endpoint, 0, data_size)

    # create a snapshot and backup
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    bv, b = find_backup(client, volume_name, snap.name)
    backup_id = b.id

    # find the replica for this backup
    replica_name = find_replica_for_backup(client, volume_name, backup_id)

    # disable scheduling on that node
    volume = client.by_id_volume(volume_name)
    for r in volume.replicas:
        if r.name == replica_name:
            node = client.by_id_node(r.hostId)
            node = set_node_scheduling(client, node, allowScheduling=False)
            common.wait_for_node_update(client, node.id,
                                        "allowScheduling", False)
    assert node

    # remove the replica with the backup
    volume.replicaRemove(name=replica_name)
    volume = common.wait_for_volume_degraded(client, volume_name)

    # now the backup status should in an Error state and with an error message
    def backup_failure_predicate(b):
        return b.id == backup_id and "Error" in b.state and b.error != ""
    volume = common.wait_for_backup_state(client, volume_name,
                                          backup_failure_predicate)

    # re enable scheduling on the previously disabled node
    node = client.by_id_node(node.id)
    node = set_node_scheduling(client, node, allowScheduling=True)
    common.wait_for_node_update(client, node.id,
                                "allowScheduling", True)

    # delete the old backup
    delete_backup(client, bv.name, b.name)
    volume = wait_for_volume_status(client, volume_name,
                                    "lastBackup", "")
    assert volume.lastBackupAt == ""

    # check that we can create another successful backup
    bv, b, _, _ = create_backup(client, volume_name)

    # delete the new backup
    delete_backup(client, bv.name, b.name)
    volume = wait_for_volume_status(client, volume_name, "lastBackup", "")
    assert volume.lastBackupAt == ""


def test_backup_block_deletion(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test backup block deletion

    Context:

    We want to make sure that we only delete non referenced backup blocks,
    we also don't want to delete blocks while there other backups in progress.
    The reason for this is that we don't yet know which blocks are required by
    the in progress backup, so blocks deletion could lead to a faulty backup.

    Setup:

    1. Setup minio as S3 backupstore

    Steps:

    1.  Create a volume and attach to the current node
    2.  Write 4 MB to the beginning of the volume (2 x 2MB backup blocks)
    3.  Create backup(1) of the volume
    4.  Overwrite the first of the backup blocks of data on the volume
    5.  Create backup(2) of the volume
    6.  Overwrite the first of the backup blocks of data on the volume
    7.  Create backup(3) of the volume
    8.  Verify backup block count == 4
        assert volume["DataStored"] == str(BLOCK_SIZE * expected_count)
        assert count of *.blk files for that volume == expected_count
    9.  Create an artificial in progress backup.cfg file
        json.dumps({"Name": name, "VolumeName": volume, "CreatedTime": ""})
    10. Delete backup(2)
    11. Verify backup block count == 4 (because of the in progress backup)
    12. Delete the artificial in progress backup.cfg file
    13. Delete backup(1)
    14. Verify backup block count == 2
    15. Delete backup(3)
    16. Verify backup block count == 0
    17. Delete the backup volume
    18. Cleanup the volume
    """
    backupstore_cleanup(client)

    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    data0 = {'pos': 0,
             'len': 2 * BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}

    bv0, backup0, _, _ = create_backup(client, volume_name, data0)

    data1 = {'pos': 0,
             'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}

    bv1, backup1, _, _ = create_backup(client, volume_name, data1)

    data2 = {'pos': 0,
             'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}

    bv2, backup2, _, _ = create_backup(client, volume_name, data2)

    backup_blocks_count = backupstore_count_backup_block_files(client,
                                                               core_api,
                                                               volume_name)
    assert backup_blocks_count == 4

    bvs = client.list_backupVolume()

    for bv in bvs:
        if bv['name'] == volume_name:
            assert bv['dataStored'] == \
                str(backup_blocks_count * BACKUP_BLOCK_SIZE)

    backupstore_create_dummy_in_progress_backup(client, core_api, volume_name)
    delete_backup(client, volume_name, backup1.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 4

    backupstore_delete_dummy_in_progress_backup(client, core_api, volume_name)

    delete_backup(client, volume_name, backup0.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 2

    delete_backup(client, volume_name, backup2.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 0

    delete_backup_volume(client, volume_name)


def test_dr_volume_activated_with_failed_replica(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test DR volume activated with a failed replica

    Context:

    Make sure that DR volume could be activated
    as long as there is a ready replica.

    Steps:

    1.  Create a volume and attach to a node.
    2.  Create a backup of the volume with writing some data.
    3.  Create a DR volume from the backup.
    4.  Disable the replica rebuilding.
    5.  Enable the setting `allow-volume-creation-with-degraded-availability`
    6.  Make a replica failed.
    7.  Activate the DR volume.
    8.  Enable the replica rebuilding.
    9.  Attach the volume to a node.
    10. Check if data is correct.
    """
    backupstore_cleanup(client)

    host_id = get_self_host_id()
    vol = create_and_check_volume(client, volume_name, 2, SIZE)
    vol.attach(hostId=host_id)
    vol = common.wait_for_volume_healthy(client, volume_name)

    data = {'pos': 0, 'len': 2 * BACKUP_BLOCK_SIZE,
            'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}
    _, backup, _, data = create_backup(client, volume_name, data)

    dr_vol_name = "dr-" + volume_name
    dr_vol = client.create_volume(name=dr_vol_name, size=SIZE,
                                  numberOfReplicas=2, fromBackup=backup.url,
                                  frontend="", standby=True)
    check_volume_last_backup(client, dr_vol_name, backup.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup.name)

    common.update_setting(
        client, common.SETTING_CONCURRENT_REPLICA_REBUILD_PER_NODE_LIMIT, "0"
    )
    common.update_setting(client, common.SETTING_DEGRADED_AVAILABILITY, "true")

    dr_vol = client.by_id_volume(dr_vol_name)
    failed_replica = dr_vol.replicas[0]
    crash_replica_processes(client, core_api, dr_vol_name,
                            replicas=[failed_replica])
    dr_vol = wait_for_volume_degraded(client, dr_vol_name)

    activate_standby_volume(client, dr_vol_name)

    common.update_setting(
        client, common.SETTING_CONCURRENT_REPLICA_REBUILD_PER_NODE_LIMIT, "5"
    )

    dr_vol = client.by_id_volume(dr_vol_name)
    dr_vol.attach(hostId=host_id)
    dr_vol = common.wait_for_volume_healthy(client, dr_vol_name)

    check_volume_data(dr_vol, data, False)


def test_dr_volume_with_backup_block_deletion(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test DR volume last backup after block deletion.

    Context:

    We want to make sure that when the block is delete, the DR volume picks up
    the correct last backup.

    Steps:

    1.  Create a volume and attach to the current node.
    2.  Write 4 MB to the beginning of the volume (2 x 2MB backup blocks).
    3.  Create backup(0) of the volume.
    4.  Overwrite backup(0) 1st blocks of data on the volume.
        (Since backup(0) contains 2 blocks of data, the updated data is
        data1["content"] + data0["content"][BACKUP_BLOCK_SIZE:])
    5.  Create backup(1) of the volume.
    6.  Verify backup block count == 3.
    7.  Create DR volume from backup(1).
    8.  Verify DR volume last backup is backup(1).
    9.  Delete backup(1).
    10. Verify backup block count == 2.
    11. Verify DR volume last backup is backup(0).
    12. Overwrite backup(0) 1st blocks of data on the volume.
        (Since backup(0) contains 2 blocks of data, the updated data is
        data2["content"] + data0["content"][BACKUP_BLOCK_SIZE:])
    13. Create backup(2) of the volume.
    14. Verify DR volume last backup is backup(2).
    15. Activate and verify DR volume data is
        data2["content"] + data0["content"][BACKUP_BLOCK_SIZE:].
    """
    backupstore_cleanup(client)

    host_id = get_self_host_id()

    vol = create_and_check_volume(client, volume_name, 2, SIZE)
    vol.attach(hostId=host_id)
    vol = common.wait_for_volume_healthy(client, volume_name)

    data0 = {'pos': 0, 'len': 2 * BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}
    _, backup0, _, data0 = create_backup(
        client, volume_name, data0)

    data1 = {'pos': 0, 'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}
    _, backup1, _, data1 = create_backup(
        client, volume_name, data1)

    backup_blocks_count = backupstore_count_backup_block_files(client,
                                                               core_api,
                                                               volume_name)
    assert backup_blocks_count == 3

    dr_vol_name = "dr-" + volume_name
    client.create_volume(name=dr_vol_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup1.url,
                         frontend="", standby=True)
    check_volume_last_backup(client, dr_vol_name, backup1.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup1.name)

    delete_backup(client, volume_name, backup1.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 2
    check_volume_last_backup(client, dr_vol_name, backup0.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup0.name)

    data2 = {'pos': 0,
             'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}
    _, backup2, _, _ = create_backup(client, volume_name, data2)

    check_volume_last_backup(client, dr_vol_name, backup2.name)
    wait_for_volume_restoration_start(client, dr_vol_name, backup2.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup2.name)

    activate_standby_volume(client, dr_vol_name)
    dr_vol = client.by_id_volume(dr_vol_name)
    dr_vol.attach(hostId=host_id)
    dr_vol = common.wait_for_volume_healthy(client, dr_vol_name)
    final_data = {
        'pos': 0,
        'len': 2 * BACKUP_BLOCK_SIZE,
        'content': data2['content'] + data0['content'][BACKUP_BLOCK_SIZE:],
    }
    check_volume_data(dr_vol, final_data, False)


def test_dr_volume_with_backup_block_deletion_abort_during_backup_in_progress(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test DR volume last backup after block deletion aborted. This will set the
    last backup to be empty.

    Context:

    We want to make sure that when the block deletion for the last backup is
    aborted by operations such as backups in progress, the DR volume will still
    pick up the correct last backup.

    Steps:

    1.  Create a volume and attach to the current node.
    2.  Write 4 MB to the beginning of the volume (2 x 2MB backup blocks).
    3.  Create backup(0) of the volume.
    4.  Overwrite backup(0) 1st blocks of data on the volume.
        (Since backup(0) contains 2 blocks of data, the updated data is
        data1["content"] + data0["content"][BACKUP_BLOCK_SIZE:])
    5.  Create backup(1) of the volume.
    6.  Verify backup block count == 3.
    7.  Create DR volume from backup(1).
    8.  Verify DR volume last backup is backup(1).
    9.  Create an artificial in progress backup.cfg file.
        This cfg file will convince the longhorn manager that there is a
        backup being created. Then all subsequent backup block cleanup will be
        skipped.
    10. Delete backup(1).
    11. Verify backup block count == 3 (because of the in progress backup).
    12. Verify DR volume last backup is empty.
    13. Delete the artificial in progress backup.cfg file.
    14. Overwrite backup(0) 1st blocks of data on the volume.
        (Since backup(0) contains 2 blocks of data, the updated data is
        data2["content"] + data0["content"][BACKUP_BLOCK_SIZE:])
    15. Create backup(2) of the volume.
    16. Verify DR volume last backup is backup(2).
    17. Activate and verify DR volume data is
        data2["content"] + data0["content"][BACKUP_BLOCK_SIZE:].
    """
    backupstore_cleanup(client)

    host_id = get_self_host_id()

    vol = create_and_check_volume(client, volume_name, 2, SIZE)
    vol.attach(hostId=host_id)
    vol = common.wait_for_volume_healthy(client, volume_name)

    data0 = {'pos': 0, 'len': 2 * BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}
    create_backup(client, volume_name, data0)

    data1 = {'pos': 0, 'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}
    _, backup1, _, data1 = create_backup(
        client, volume_name, data1)

    backup_blocks_count = backupstore_count_backup_block_files(client,
                                                               core_api,
                                                               volume_name)
    assert backup_blocks_count == 3

    dr_vol_name = "dr-" + volume_name
    client.create_volume(name=dr_vol_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup1.url,
                         frontend="", standby=True)
    check_volume_last_backup(client, dr_vol_name, backup1.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup1.name)

    backupstore_create_dummy_in_progress_backup(client, core_api, volume_name)
    delete_backup(client, volume_name, backup1.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 3
    check_volume_last_backup(client, dr_vol_name, "")
    backupstore_delete_dummy_in_progress_backup(client, core_api, volume_name)

    data2 = {'pos': 0,
             'len': BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(BACKUP_BLOCK_SIZE)}
    _, backup2, _, _ = create_backup(client, volume_name, data2)

    check_volume_last_backup(client, dr_vol_name, backup2.name)
    wait_for_volume_restoration_start(client, dr_vol_name, backup2.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup2.name)

    activate_standby_volume(client, dr_vol_name)
    dr_vol = client.by_id_volume(dr_vol_name)
    dr_vol.attach(hostId=host_id)
    dr_vol = common.wait_for_volume_healthy(client, dr_vol_name)
    final_data = {
        'pos': 0,
        'len': 2 * BACKUP_BLOCK_SIZE,
        'content': data2['content'] + data0['content'][BACKUP_BLOCK_SIZE:],
    }
    check_volume_data(dr_vol, final_data, False)


def test_dr_volume_with_all_backup_blocks_deleted(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test DR volume can be activate after delete all backups.

    Context:

    We want to make sure that DR volume can activate after delete all backups.

    Steps:

    1.  Create a volume and attach to the current node.
    2.  Write 4 MB to the beginning of the volume (2 x 2MB backup blocks).
    3.  Create backup(0) of the volume.
    6.  Verify backup block count == 2.
    7.  Create DR volume from backup(0).
    8.  Verify DR volume last backup is backup(0).
    9.  Delete backup(0).
    10. Verify backup block count == 0.
    11. Verify DR volume last backup is empty.
    15. Activate and verify DR volume data is data(0).
    """
    backupstore_cleanup(client)

    host_id = get_self_host_id()

    vol = create_and_check_volume(client, volume_name, 2, SIZE)
    vol.attach(hostId=host_id)
    vol = common.wait_for_volume_healthy(client, volume_name)

    data0 = {'pos': 0, 'len': 2 * BACKUP_BLOCK_SIZE,
             'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}
    _, backup0, _, data0 = create_backup(
        client, volume_name, data0)

    backup_blocks_count = backupstore_count_backup_block_files(client,
                                                               core_api,
                                                               volume_name)
    assert backup_blocks_count == 2

    dr_vol_name = "dr-" + volume_name
    client.create_volume(name=dr_vol_name, size=SIZE,
                         numberOfReplicas=2, fromBackup=backup0.url,
                         frontend="", standby=True)
    check_volume_last_backup(client, dr_vol_name, backup0.name)
    wait_for_backup_restore_completed(client, dr_vol_name, backup0.name)

    delete_backup(client, volume_name, backup0.name)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume_name) == 0
    check_volume_last_backup(client, dr_vol_name, "")

    activate_standby_volume(client, dr_vol_name)
    dr_vol = client.by_id_volume(dr_vol_name)
    dr_vol.attach(hostId=host_id)
    dr_vol = common.wait_for_volume_healthy(client, dr_vol_name)
    check_volume_data(dr_vol, data0, False)


def test_backup_volume_list(set_random_backupstore, client, core_api):  # NOQA
    """
    Test backup volume list
    Context:
    We want to make sure that an error when listing a single backup volume
    does not stop us from listing all the other backup volumes. Otherwise a
    single faulty backup can block the retrieval of all known backup volumes.
    Setup:
    1. Setup minio as S3 backupstore
    Steps:
    1.  Create a volume(1,2) and attach to the current node
    2.  write some data to volume(1,2)
    3.  Create a backup(1) of volume(1,2)
    4.  request a backup list
    5.  verify backup list contains no error messages for volume(1,2)
    6.  verify backup list contains backup(1) for volume(1,2)
    7.  place a file named "backup_1234@failure.cfg"
        into the backups folder of volume(1)
    8.  request a backup list
    9.  verify backup list contains no error messages for volume(1,2)
    10. verify backup list contains backup(1) for volume(1,2)
    11. delete backup volumes(1 & 2)
    12. cleanup
    """
    backupstore_cleanup(client)

    # create 2 volumes.
    volume1_name, volume2_name = generate_volume_name(), generate_volume_name()

    volume1 = create_and_check_volume(client, volume1_name)
    volume2 = create_and_check_volume(client, volume2_name)

    host_id = get_self_host_id()
    volume1 = volume1.attach(hostId=host_id)
    volume1 = common.wait_for_volume_healthy(client, volume1_name)
    volume2 = volume2.attach(hostId=host_id)
    volume2 = common.wait_for_volume_healthy(client, volume2_name)

    bv1, backup1, snap1, _ = create_backup(client, volume1_name)
    bv2, backup2, snap2, _ = create_backup(client, volume2_name)

    def verify_no_err():
        '''
        request a backup list
        verify backup list contains no error messages for volume(1,2)
        verify backup list contains backup(1) for volume(1,2)
        '''
        for _ in range(RETRY_COUNTS):
            verified_bvs = set()
            backup_volume_list = client.list_backupVolume()
            for bv in backup_volume_list:
                if bv.name in (volume1_name, volume2_name):
                    assert not bv['messages']
                    for b in bv.backupList().data:
                        if bv.name == volume1_name \
                                and b.name == backup1.name \
                                or bv.name == volume2_name \
                                and b.name == backup2.name:
                            verified_bvs.add(bv.name)
            if len(verified_bvs) == 2:
                break
            time.sleep(RETRY_INTERVAL)
        assert len(verified_bvs) == 2

    verify_no_err()

    # place a bad named file into the backups folder of volume(1)
    prefix = \
        backupstore_get_backup_volume_prefix(client, volume1_name) + "/backups"
    backupstore_create_file(client,
                            core_api,
                            prefix + "/backup_1234@failure.cfg")

    verify_no_err()

    backupstore_delete_file(client,
                            core_api,
                            prefix + "/backup_1234@failure.cfg")

    backupstore_cleanup(client)


def test_backup_metadata_deletion(set_random_backupstore, client, core_api, volume_name):  # NOQA
    """
    Test backup metadata deletion

    Context:

    We want to be able to delete the metadata (.cfg) files,
    even if they are corrupt or in a bad state (missing volume.cfg).

    Setup:

    1. Setup minio as S3 backupstore
    2. Cleanup backupstore

    Steps:

    1.  Create volume(1,2) and attach to the current node
    2.  write some data to volume(1,2)
    3.  Create backup(1,2) of volume(1,2)
    4.  request a backup list
    5.  verify backup list contains no error messages for volume(1,2)
    6.  verify backup list contains backup(1,2) information for volume(1,2)
    7.  delete backup(1) of volume(1,2)
    8.  request a backup list
    9.  verify backup list contains no error messages for volume(1,2)
    10. verify backup list only contains backup(2) information for volume(1,2)
    11. delete volume.cfg of volume(2)
    12. request backup volume deletion for volume(2)
    13. verify that volume(2) has been deleted in the backupstore.
    14. request a backup list
    15. verify backup list only contains volume(1) and no errors
    16. verify backup list only contains backup(2) information for volume(1)
    17. delete backup volume(1)
    18. verify that volume(1) has been deleted in the backupstore.
    19. cleanup
    """
    backupstore_cleanup(client)

    volume1_name = volume_name + "-1"
    volume2_name = volume_name + "-2"

    host_id = get_self_host_id()

    volume1 = create_and_check_volume(client, volume1_name)
    volume2 = create_and_check_volume(client, volume2_name)

    volume1.attach(hostId=host_id)
    volume2.attach(hostId=host_id)

    volume1 = wait_for_volume_healthy(client, volume1_name)
    volume2 = wait_for_volume_healthy(client, volume2_name)

    v1bv, v1b1, _, _ = create_backup(client, volume1_name)
    v2bv, v2b1, _, _ = create_backup(client, volume2_name)
    _, v1b2, _, _ = create_backup(client, volume1_name)
    _, v2b2, _, _ = create_backup(client, volume2_name)

    for i in range(RETRY_COUNTS):
        found1 = found2 = found3 = found4 = False

        bvs = client.list_backupVolume()
        for bv in bvs:
            backups = bv.backupList()
            for b in backups:
                if b.name == v1b1.name:
                    found1 = True
                elif b.name == v1b2.name:
                    found2 = True
                elif b.name == v2b1.name:
                    found3 = True
                elif b.name == v2b2.name:
                    found4 = True
        if found1 & found2 & found3 & found4:
            break
        time.sleep(RETRY_INTERVAL)
    assert found1 & found2 & found3 & found4

    v1b2_new = v1bv.backupGet(name=v1b2.name)
    assert_backup_state(v1b2, v1b2_new)

    v2b1_new = v2bv.backupGet(name=v2b1.name)
    assert_backup_state(v2b1, v2b1_new)

    v2b2_new = v2bv.backupGet(name=v2b2.name)
    assert_backup_state(v2b2, v2b2_new)

    delete_backup(client, volume1_name, v1b1.name)
    delete_backup(client, volume2_name, v2b1.name)

    for i in range(RETRY_COUNTS):
        found1 = found2 = found3 = found4 = False

        bvs = client.list_backupVolume()
        for bv in bvs:
            backups = bv.backupList()
            for b in backups:
                if b.name == v1b1.name:
                    found1 = True
                elif b.name == v1b2.name:
                    found2 = True
                elif b.name == v2b1.name:
                    found3 = True
                elif b.name == v2b2.name:
                    found4 = True
        if (not found1) & found2 & (not found3) & found4:
            break
        time.sleep(RETRY_INTERVAL)
    assert (not found1) & found2 & (not found3) & found4

    assert len(v1bv.backupList()) == 1
    assert len(v2bv.backupList()) == 1
    assert v1bv.backupList()[0].name == v1b2.name
    assert v2bv.backupList()[0].name == v2b2.name

    backupstore_delete_volume_cfg_file(client, core_api, volume2_name)

    delete_backup(client, volume2_name, v2b2.name)
    assert len(v2bv.backupList()) == 0

    delete_backup_volume(client, v2bv.name)
    for i in range(RETRY_COUNTS):
        if backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume2_name) == 0:
            break
        time.sleep(RETRY_INTERVAL)
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume2_name) == 0

    for i in range(RETRY_COUNTS):
        bvs = client.list_backupVolume()

        found1 = found2 = found3 = found4 = False
        for bv in bvs:
            backups = bv.backupList()
            for b in backups:
                if b.name == v1b1.name:
                    found1 = True
                elif b.name == v1b2.name:
                    found2 = True
                elif b.name == v2b1.name:
                    found3 = True
                elif b.name == v2b2.name:
                    found4 = True
        if (not found1) & found2 & (not found3) & (not found4):
            break
        time.sleep(RETRY_INTERVAL)
    assert (not found1) & found2 & (not found3) & (not found4)

    v1b2_new = v1bv.backupGet(name=v1b2.name)
    assert_backup_state(v1b2, v1b2_new)
    assert v1b2_new.messages == v1b2.messages is None

    delete_backup(client, volume1_name, v1b2.name)
    for i in range(RETRY_COUNTS):
        if backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume1_name) == 0:
            break
    assert backupstore_count_backup_block_files(client,
                                                core_api,
                                                volume1_name) == 0

    for i in range(RETRY_COUNTS):
        found1 = found2 = found3 = found4 = False

        bvs = client.list_backupVolume()
        for bv in bvs:
            backups = bv.backupList()
            for b in backups:
                if b.name == v1b1.name:
                    found1 = True
                elif b.name == v1b2.name:
                    found2 = True
                elif b.name == v2b1.name:
                    found3 = True
                elif b.name == v2b2.name:
                    found4 = True
        if (not found1) & (not found2) & (not found3) & (not found4):
            break
        time.sleep(RETRY_INTERVAL)
    assert (not found1) & (not found2) & (not found3) & (not found4)


@pytest.mark.coretest   # NOQA
def test_backup(set_random_backupstore, client, volume_name):  # NOQA
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
    backup_test(client, volume_name, SIZE)


def backup_test(client, volume_name, size, backing_image="", compression_method=DEFAULT_BACKUP_COMPRESSION_METHOD):  # NOQA
    volume = create_and_check_volume(client, volume_name, 2, size,
                                     backing_image)

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.backupCompressionMethod == compression_method

    backupstore_test(client, lht_hostId, volume_name, size, compression_method)


def backupstore_test(client, host_id, volname, size, compression_method):  # NOQA
    bv, b, snap2, data = create_backup(client, volname)

    # test restore
    restore_name = generate_volume_name()
    volume = client.create_volume(name=restore_name, size=size,
                                  numberOfReplicas=2,
                                  fromBackup=b.url)

    volume = common.wait_for_volume_restoration_completed(client, restore_name)
    volume = common.wait_for_volume_detached(client, restore_name)
    assert volume.name == restore_name
    assert volume.size == size
    assert volume.numberOfReplicas == 2
    assert volume.state == "detached"
    assert volume.restoreRequired is False
    assert volume.backupCompressionMethod == compression_method

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, restore_name)
    check_volume_data(volume, data)
    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, restore_name)

    delete_backup(client, bv.name, b.name)
    volume = wait_for_volume_status(client, volume.name,
                                    "lastBackup", "")
    assert volume.lastBackupAt == ""

    client.delete(volume)
    volume = wait_for_volume_delete(client, restore_name)


@pytest.mark.coretest  # NOQA
def test_backup_labels(set_random_backupstore, client, random_labels, volume_name):  # NOQA
    """
    Test that the proper Labels are applied when creating a Backup manually.

    1. Create a volume
    2. Run the following steps on all backupstores
    3. Create a backup with some random labels
    4. Get backup from backupstore, verify the labels are set on the backups
    """
    backup_labels_test(client, random_labels, volume_name)


def backup_labels_test(client, random_labels, volume_name, size=SIZE, backing_image=""):  # NOQA
    host_id = get_self_host_id()

    volume = create_and_check_volume(client, volume_name, 2, size,
                                     backing_image)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    bv, b, _, _ = create_backup(client, volume_name, labels=random_labels)
    # If we're running the test with a BackingImage,
    # check field `volumeBackingImageName` is set properly.
    backup = bv.backupGet(name=b.name)
    # Longhorn will automatically add a label `longhorn.io/volume-access-mode`
    # to a newly created backup
    assert len(backup.labels) == len(random_labels) + 1
    assert random_labels["key"] == backup.labels["key"]
    assert "longhorn.io/volume-access-mode" in backup.labels.keys()
    wait_for_backup_volume(client, volume_name, backing_image)


@pytest.mark.coretest   # NOQA
def test_restore_inc(set_random_backupstore, client, core_api, volume_name, pod):  # NOQA
    """
    Test restore from disaster recovery volume (incremental restore)

    Run test against all the backupstores

    1. Create a volume and attach to the current node
    2. Generate `data0`, write to the volume, make a backup `backup0`
    3. Create three DR(standby) volumes from the backup: `sb_volume0/1/2`
    4. Wait for all three DR volumes to start the initial restoration
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
    restore_inc_test(client, core_api, volume_name, pod)


def restore_inc_test(client, core_api, volume_name, pod):  # NOQA
    std_volume = create_and_check_volume(client, volume_name, 2, SIZE)
    lht_host_id = get_self_host_id()
    std_volume.attach(hostId=lht_host_id)
    std_volume = common.wait_for_volume_healthy(client, volume_name)

    with pytest.raises(Exception) as e:
        std_volume.activate(frontend=VOLUME_FRONTEND_BLOCKDEV)
        assert "already in active mode" in str(e.value)

    data0 = {'len': 2 * BACKUP_BLOCK_SIZE, 'pos': 0,
             'content': common.generate_random_data(2 * BACKUP_BLOCK_SIZE)}
    _, backup0, _, data0 = create_backup(
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
    wait_for_backup_restore_completed(client, sb_volume0_name, backup0.name)
    wait_for_backup_restore_completed(client, sb_volume1_name, backup0.name)
    wait_for_backup_restore_completed(client, sb_volume2_name, backup0.name)

    sb_volume0 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume0_name)
    sb_volume1 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume1_name)
    sb_volume2 = common.wait_for_volume_healthy_no_frontend(client,
                                                            sb_volume2_name)

    for _ in range(RETRY_COUNTS):
        client.list_backupVolume()
        sb_volume0 = client.by_id_volume(sb_volume0_name)
        sb_volume1 = client.by_id_volume(sb_volume1_name)
        sb_volume2 = client.by_id_volume(sb_volume2_name)
        sb_engine0 = get_volume_engine(sb_volume0)
        sb_engine1 = get_volume_engine(sb_volume1)
        sb_engine2 = get_volume_engine(sb_volume2)
        if sb_volume0.restoreRequired is False or \
           sb_volume1.restoreRequired is False or \
           sb_volume2.restoreRequired is False or \
                not sb_engine0.lastRestoredBackup or \
                not sb_engine1.lastRestoredBackup or \
                not sb_engine2.lastRestoredBackup:
            time.sleep(RETRY_INTERVAL)
        else:
            break
    assert sb_volume0.standby is True
    assert sb_volume0.lastBackup == backup0.name
    assert sb_volume0.frontend == ""
    assert sb_volume0.restoreRequired is True
    sb_engine0 = get_volume_engine(sb_volume0)
    assert sb_engine0.lastRestoredBackup == backup0.name
    assert sb_engine0.requestedBackupRestore == backup0.name
    assert sb_volume1.standby is True
    assert sb_volume1.lastBackup == backup0.name
    assert sb_volume1.frontend == ""
    assert sb_volume1.restoreRequired is True
    sb_engine1 = get_volume_engine(sb_volume1)
    assert sb_engine1.lastRestoredBackup == backup0.name
    assert sb_engine1.requestedBackupRestore == backup0.name
    assert sb_volume2.standby is True
    assert sb_volume2.lastBackup == backup0.name
    assert sb_volume2.frontend == ""
    assert sb_volume2.restoreRequired is True
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
        {'len': BACKUP_BLOCK_SIZE, 'pos': 0,
         'content': zero_string * BACKUP_BLOCK_SIZE})
    check_volume_last_backup(client, sb_volume1_name, backup1.name)
    activate_standby_volume(client, sb_volume1_name)
    sb_volume1 = client.by_id_volume(sb_volume1_name)
    sb_volume1.attach(hostId=lht_host_id)
    sb_volume1 = common.wait_for_volume_healthy(client, sb_volume1_name)
    data0_modified1 = {
        'len': data0['len'],
        'pos': 0,
        'content': data1['content'] + data0['content'][data1['len']:],
    }
    check_volume_data(sb_volume1, data0_modified1, False)

    data2_len = int(BACKUP_BLOCK_SIZE/2)
    data2 = {'len': data2_len, 'pos': 0,
             'content': common.generate_random_data(data2_len)}
    _, backup2, _, data2 = create_backup(client, volume_name, data2)

    check_volume_last_backup(client, sb_volume2_name, backup2.name)
    activate_standby_volume(client, sb_volume2_name)
    sb_volume2 = client.by_id_volume(sb_volume2_name)
    sb_volume2.attach(hostId=lht_host_id)
    sb_volume2 = common.wait_for_volume_healthy(client, sb_volume2_name)
    data0_modified2 = {
        'len': data0['len'],
        'pos': 0,
        'content':
            data2['content'] +
            data1['content'][data2['len']:] +
            data0['content'][data1['len']:],
    }
    check_volume_data(sb_volume2, data0_modified2, False)

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


def test_deleting_backup_volume(set_random_backupstore, client, volume_name):  # NOQA
    """
    Test deleting backup volumes

    1. Create volume and create backup
    2. Delete the backup and make sure it's gone in the backupstore
    """
    lht_host_id = get_self_host_id()
    volume = create_and_check_volume(client, volume_name)

    volume.attach(hostId=lht_host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    create_backup(client, volume_name)
    create_backup(client, volume_name)

    delete_backup_volume(client, volume_name)
    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
@pytest.mark.skipif('nfs' not in BACKUPSTORE, reason='This test is only applicable for nfs')  # NOQA
def test_listing_backup_volume(client, backing_image=""):   # NOQA
    """
    Test listing backup volumes

    1. Create three volumes: `volume1/2/3`
    2. Setup NFS backupstore since we can manipulate the content easily
    3. Create multiple snapshots for all three volumes
    4. Rename `volume1`'s `volume.cfg` to `volume.cfg.tmp` in backupstore
    5. List backup volumes. Make sure `volume1` errors out but found other two
    6. Restore `volume1`'s `volume.cfg`.
    7. Make sure now backup volume `volume1` can be found
    8. Delete backups for `volume1/2`, make sure they cannot be found later
    9. Corrupt a backup.cfg on volume3
    11. Check that the backup is listed with the other backups of volume3
    12. Verify that the corrupted backup has Messages of type error
    13. Check that backup inspection for the previously corrupted backup fails
    14. Delete backups for `volume3`, make sure they cannot be found later
    """
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
    subprocess.check_output(["sync"])
    _, _, snap4, _ = create_backup(client, volume3_name)
    subprocess.check_output(["sync"])
    _, _, snap5, _ = create_backup(client, volume3_name)
    subprocess.check_output(["sync"])

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

    found1 = True
    found2 = found3 = False
    for i in range(RETRY_COUNTS):
        bvs = client.list_backupVolume()
        if volume1_name not in bvs:
            found1 = False
        if volume2_name in bvs:
            found2 = True
        if volume3_name in bvs:
            found3 = True
        if not found1 & found2 & found3:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found1 & found2 & found3

    cmd = ["mv", volume1_backup_volume_cfg_path + ".tmp",
           volume1_backup_volume_cfg_path]
    subprocess.check_output(cmd)
    subprocess.check_output(["sync"])

    bv1, b1 = common.find_backup(client, volume1_name, snap1.name)
    common.delete_backup(client, volume1_name, b1.name)

    bv2, b2 = common.find_backup(client, volume2_name, snap2.name)
    common.delete_backup(client, volume2_name, b2.name)

    # corrupt backup for snap4
    bv4, b4 = common.find_backup(client, volume3_name, snap4.name)
    b4_cfg_name = "backup_" + b4["name"] + ".cfg"
    cmd = ["find", "/mnt/nfs", "-type", "d", "-name", volume3_name]
    v3_backup_path = subprocess.check_output(cmd).strip().decode('utf-8')
    b4_cfg_path = os.path.join(v3_backup_path, "backups", b4_cfg_name)
    assert os.path.exists(b4_cfg_path)
    b4_tmp_cfg_path = os.path.join(v3_backup_path, b4_cfg_name)
    os.rename(b4_cfg_path, b4_tmp_cfg_path)
    assert os.path.exists(b4_tmp_cfg_path)

    corrupt_backup = open(b4_cfg_path, "w")
    assert corrupt_backup
    assert corrupt_backup.write("{corrupt: definitely") > 0
    corrupt_backup.close()
    subprocess.check_output(["sync"])

    # a corrupt backup cannot provide information about the snapshot
    found = True
    for i in range(RETRY_COMMAND_COUNT):
        if b4["name"] not in bv4.backupList():
            found = False
            break
    assert not found

    # cleanup b4
    os.remove(b4_cfg_path)
    os.rename(b4_tmp_cfg_path, b4_cfg_path)
    subprocess.check_output(["sync"])

    bv3, b3 = common.find_backup(client, volume3_name, snap3.name)
    common.delete_backup(client, volume3_name, b3.name)
    bv4, b4 = common.find_backup(client, volume3_name, snap4.name)
    common.delete_backup(client, volume3_name, b4.name)
    bv5, b5 = common.find_backup(client, volume3_name, snap5.name)
    common.delete_backup(client, volume3_name, b5.name)

    common.delete_backup_volume(client, volume3_name)
    common.wait_for_backup_volume_delete(client, volume3_name)

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
def test_volume_multinode(client, volume_name):  # NOQA
    """
    Test the volume can be attached on multiple nodes

    1. Create one volume
    2. Attach it on every node once, verify the state, then detach it
    """
    hosts = [node['name'] for node in client.list_node()]

    volume = client.create_volume(name=volume_name,
                                  size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client,
                                             volume_name)

    for host_id in hosts:
        volume = volume.attach(hostId=host_id)
        volume = common.wait_for_volume_healthy(client,
                                                volume_name)
        engine = get_volume_engine(volume)
        assert engine.hostId == host_id
        volume = volume.detach()
        volume = common.wait_for_volume_detached(client,
                                                 volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.skip(reason="TODO")
def test_pvc_storage_class_name_from_backup_volume(): # NOQA
    """
    Test the storageClasName of the restored volume's PV/PVC
    should be from the backup volume

    Given
    - Create a new StorageClass
      ```
      kind: StorageClass
      apiVersion: storage.k8s.io/v1
      metadata:
        name: longhorn-sc-name-recorded
      provisioner: driver.longhorn.io
      allowVolumeExpansion: true
      reclaimPolicy: Delete
      volumeBindingMode: Immediate
      parameters:
        numberOfReplicas: "3"
        staleReplicaTimeout: "2880"
      ```
    - Create a PVC to use this SC
      ```
      apiVersion: v1
      kind: PersistentVolumeClaim
      metadata:
        name: test-pvc
      spec:
        accessModes:
          - ReadWriteOnce
        storageClassName: longhorn-sc-name-recorded
        resources:
          requests:
            storage: 5Gi
      ```
    - Attach the Volume and write some data

    When
    - Backup the Volume

    Then
    - the backupvolume's status.storageClassName should be
      longhorn-sc-name-recorded

    When
    - Restore the backup to a new volume
    - Create PV/PVC from the new volume with create new PVC option

    Then
    - The new PVC's storageClassName should still be longhorn-sc-name-recorded
    - Verify the restored data is the same as original one
    """
    pass


@pytest.mark.coretest  # NOQA
def test_volume_scheduling_failure(client, volume_name):  # NOQA
    '''
    Test fail to schedule by disable scheduling for all the nodes

    Also test cannot attach a scheduling failed volume

    1. Disable `allowScheduling` for all nodes
    2. Create a volume.
    3. Verify the volume condition `Scheduled` is false
    4. Verify the volume is not ready for workloads
    5. Verify attaching the volume will result in error
    6. Enable `allowScheduling` for all nodes
    7. Volume should be automatically scheduled (condition become true)
    8. Volume can be attached now
    '''
    nodes = client.list_node()
    assert len(nodes) > 0

    for node in nodes:
        node = set_node_scheduling(client, node, allowScheduling=False)
        node = common.wait_for_node_update(client, node.id,
                                           "allowScheduling", False)

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3)

    volume = common.wait_for_volume_condition_scheduled(client, volume_name,
                                                        "status",
                                                        CONDITION_STATUS_FALSE)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert not volume.ready
    self_node = get_self_host_id()
    with pytest.raises(Exception) as e:
        volume.attach(hostId=self_node)
    assert "unable to attach volume" in str(e.value)

    for node in nodes:
        node = set_node_scheduling(client, node, allowScheduling=True)
        node = common.wait_for_node_update(client, node.id,
                                           "allowScheduling", True)

    volume = common.wait_for_volume_condition_scheduled(client, volume_name,
                                                        "status",
                                                        CONDITION_STATUS_TRUE)
    volume = common.wait_for_volume_detached(client, volume_name)
    volume = volume.attach(hostId=self_node)
    volume = common.wait_for_volume_healthy(client, volume_name)
    endpoint = get_volume_endpoint(volume)
    volume_rw_test(endpoint)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_setting_default_replica_count(client, volume_name):  # NOQA
    """
    Test `Default Replica Count` setting

    1. Set default replica count in the global settings to 5
    2. Create a volume without specify the replica count
    3. The volume should have 5 replicas (instead of the previous default 3)
    """
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
def test_volume_update_replica_count(client, volume_name):  # NOQA
    """
    Test updating volume's replica count

    1. Create a volume with 2 replicas
    2. Attach the volume
    3. Increase the replica to 3.
    4. Volume will become degraded and start rebuilding
    5. Wait for rebuilding to complete
    6. Update the replica count to 2. Volume should remain healthy
    7. Remove 1 replicas, so there will be 2 replicas in the volume
    8. Verify the volume is still healthy

    Volume should always be healthy even only with 2 replicas.
    """
    host_id = get_self_host_id()

    replica_count = 2
    volume = create_and_check_volume(client, volume_name, replica_count)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    replica_count = 3
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

    volume = common.wait_for_volume_replica_count(client, volume_name,
                                                  replica_count)
    assert volume.robustness == "healthy"
    assert len(volume.replicas) == replica_count

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_attach_without_frontend(client, volume_name):  # NOQA
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
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    check_volume_endpoint(volume)

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


@pytest.mark.coretest  # NOQA
def test_storage_class_from_backup(set_random_backupstore, volume_name, pvc_name, storage_class, client, core_api, pod_make):  # NOQA
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
    wait_for_backup_completion(client, volume_name, snapshot.name)
    bv, b = find_backup(client, volume_name, snapshot.name)

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
def test_expansion_basic(client, volume_name):  # NOQA
    """
    Test volume expansion using Longhorn API

    1. Create volume and attach to the current node
    2. Generate data `snap1_data` and write it to the volume
    3. Create snapshot `snap1`
    4. Online expand the volume
    5. Verify the volume has been expanded
    6. Generate data `snap2_data` and write it to the volume
    7. Create snapshot `snap2`
    8. Generate data `snap3_data` and write it after the original size
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

    TODO: Add offline expansion
    """
    volume = create_and_check_volume(client, volume_name)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    snap1_data = write_volume_random_data(volume)
    snap1 = create_snapshot(client, volume_name)

    volume.expand(size=EXPAND_SIZE)
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.size == EXPAND_SIZE
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
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    check_volume_endpoint(volume)
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


def test_expansion_with_size_round_up(client, core_api, volume_name):  # NOQA
    """
    test expand longhorn volume

    1. Create and attach longhorn volume with size '1Gi'.
    2. Write data, and offline expand volume size to '2000000000/2G'.
    3. Check if size round up '2000683008' and the written data.
    4. Write data, and online expand volume size to '2Gi'.
    5. Check if size round up '2147483648' and the written data.
    """

    volume = create_and_check_volume(client, volume_name, 2, str(1 * Gi))

    self_hostId = get_self_host_id()
    volume.attach(hostId=self_hostId, disableFrontend=False)
    volume = wait_for_volume_healthy(client, volume_name)
    test_data = write_volume_random_data(volume)

    # Step 2: Offline expansion
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    volume.expand(size="2000000000")
    wait_for_volume_expansion(client, volume_name)
    volume = wait_for_volume_detached(client, volume_name)
    assert volume.size == "2000683008"
    self_hostId = get_self_host_id()
    volume.attach(hostId=self_hostId, disableFrontend=False)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, test_data, False)

    # Step 4: Online expansion
    test_data = write_volume_random_data(volume)
    volume.expand(size=str(2 * Gi))
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.size == "2147483648"
    check_volume_data(volume, test_data, False)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest   # NOQA
def test_restore_inc_with_offline_expansion(set_random_backupstore, client, core_api, volume_name, pod):  # NOQA
    """
    Test restore from disaster recovery volume with volume offline expansion

    Run test against a random backupstores

    1. Create a volume and attach to the current node
    2. Generate `data0`, write to the volume, make a backup `backup0`
    3. Create three DR(standby) volumes from the backup: `dr_volume0/1/2`
    4. Wait for all three DR volumes to start the initial restoration
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
    lht_host_id = get_self_host_id()

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
    wait_for_backup_restore_completed(client, dr_volume0_name, backup0.name)
    wait_for_backup_restore_completed(client, dr_volume1_name, backup0.name)
    wait_for_backup_restore_completed(client, dr_volume2_name, backup0.name)

    dr_volume0 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume0_name)
    dr_volume1 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume1_name)
    dr_volume2 = common.wait_for_volume_healthy_no_frontend(client,
                                                            dr_volume2_name)

    for i in range(RETRY_COUNTS):
        client.list_backupVolume()
        dr_volume0 = client.by_id_volume(dr_volume0_name)
        dr_volume1 = client.by_id_volume(dr_volume1_name)
        dr_volume2 = client.by_id_volume(dr_volume2_name)
        dr_engine0 = get_volume_engine(dr_volume0)
        dr_engine1 = get_volume_engine(dr_volume1)
        dr_engine2 = get_volume_engine(dr_volume2)
        if dr_volume0.restoreRequired is False or \
                dr_volume1.restoreRequired is False or \
                dr_volume2.restoreRequired is False or \
                not dr_engine0.lastRestoredBackup or \
                not dr_engine1.lastRestoredBackup or \
                not dr_engine2.lastRestoredBackup:
            time.sleep(RETRY_INTERVAL)
        else:
            break
    assert dr_volume0.standby is True
    assert dr_volume0.lastBackup == backup0.name
    assert dr_volume0.frontend == ""
    assert dr_volume0.restoreRequired is True
    dr_engine0 = get_volume_engine(dr_volume0)
    assert dr_engine0.lastRestoredBackup == backup0.name
    assert dr_engine0.requestedBackupRestore == backup0.name
    assert dr_volume1.standby is True
    assert dr_volume1.lastBackup == backup0.name
    assert dr_volume1.frontend == ""
    assert dr_volume1.restoreRequired is True
    dr_engine1 = get_volume_engine(dr_volume1)
    assert dr_engine1.lastRestoredBackup == backup0.name
    assert dr_engine1.requestedBackupRestore == backup0.name
    assert dr_volume2.standby is True
    assert dr_volume2.lastBackup == backup0.name
    assert dr_volume2.frontend == ""
    assert dr_volume2.restoreRequired is True
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

    offline_expand_attached_volume(client, volume_name)
    std_volume = client.by_id_volume(volume_name)
    check_block_device_size(std_volume, int(EXPAND_SIZE))

    data1 = {'pos': VOLUME_RWTEST_SIZE, 'len': VOLUME_RWTEST_SIZE,
             'content': common.generate_random_data(VOLUME_RWTEST_SIZE)}
    bv, backup1, _, data1 = create_backup(
        client, volume_name, data1)

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

    backupstore_cleanup(client)

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


def test_engine_image_daemonset_restart(client, apps_api, volume_name):  # NOQA
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

    # Let DaemonSet really restarted
    common.wait_for_engine_image_condition(client, default_img.name, "False")

    # The Longhorn volume is still available
    # during the engine image DaemonSet restarting
    check_volume_data(volume, snap1_data)

    # Wait for the restart complete
    common.wait_for_engine_image_condition(client, default_img.name, "True")

    # Longhorn is still able to use the corresponding engine binary to
    # operate snapshot
    check_volume_data(volume, snap1_data)
    snap2_data = write_volume_random_data(volume)
    create_snapshot(client, volume_name)
    check_volume_data(volume, snap2_data)


@pytest.mark.coretest  # NOQA
def test_expansion_canceling(client, core_api, volume_name, pod, pvc, storage_class):  # NOQA
    """
    Test expansion canceling

    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Generate `test_data` and write to the pod
    3. Create an empty directory with expansion snapshot tmp meta file path
       so that the following offline expansion will fail
    4. Delete the pod and wait for volume detachment
    5. Try offline expansion via Longhorn API
    6. Wait for expansion failure then use Longhorn API to cancel it
    7. Create a new pod and validate the volume content
    8. Create an empty directory with expansion snapshot tmp meta file path
       so that the following online expansion will fail
    9. Try online expansion via Longhorn API
    10. Wait for expansion failure then use Longhorn API to cancel it
    11. Validate the volume content again, then re-write random data to the pod
    12. Retry online expansion, then verify the expansion done via Longhorn API
    13. Validate the volume content, then check if data writing looks fine
    14. Clean up pod, PVC, and PV
    """
    storage_class['parameters']['numberOfReplicas'] = "2"
    create_storage_class(storage_class)

    pod_name = 'expand-canceling-test'
    expansion_pvc_name = pod_name + "-pvc"
    pvc['metadata']['name'] = expansion_pvc_name
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    pvc['spec']['resources']['requests']['storage'] = SIZE
    common.create_pvc(pvc)

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {'claimName': expansion_pvc_name},
    }]
    create_and_wait_pod(core_api, pod)

    pv = common.wait_and_get_pv_for_pvc(core_api, expansion_pvc_name)
    assert pv.status.phase == "Bound"
    expansion_pv_name = pv.metadata.name
    volume_name = pv.spec.csi.volume_handle

    # Step 3: Prepare to fail offline expansion for one replica
    volume = client.by_id_volume(volume_name)
    replicas = volume.replicas
    fail_replica_expansion(client, core_api,
                           volume_name, EXPAND_SIZE, replicas)

    test_data1 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data1, "test_file1")

    delete_and_wait_pod(core_api, pod_name)
    volume = wait_for_volume_detached(client, volume_name)

    # Step 5 & 6: Try offline expansion, wait for the failure, then cancel it
    volume.expand(size=EXPAND_SIZE)
    wait_for_expansion_failure(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.cancelExpansion()
    wait_for_volume_expansion(client, volume_name)
    wait_for_expansion_error_clear(client, volume_name)
    wait_for_volume_detached(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.state == "detached"
    assert volume.size == SIZE
    fix_replica_expansion_failure(client, core_api,
                                  volume_name, EXPAND_SIZE, replicas)

    # Step 7: Verify the data after expansion cancellation
    create_and_wait_pod(core_api, pod)
    resp = read_volume_data(core_api, pod_name, "test_file1")
    assert resp == test_data1
    test_data2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data2, "test_file2")

    # Step 8: Prepare to fail online expansion for one replica
    volume = client.by_id_volume(volume_name)
    replicas = volume.replicas
    fail_replica_expansion(client, core_api,
                           volume_name, EXPAND_SIZE, replicas)
    # Step 9 & 10: Try online expansion, wait for the failure, then cancel it
    volume.expand(size=EXPAND_SIZE)
    wait_for_expansion_failure(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.cancelExpansion()
    wait_for_volume_expansion(client, volume_name)
    wait_for_expansion_error_clear(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.size == SIZE
    fix_replica_expansion_failure(client, core_api,
                                  volume_name, EXPAND_SIZE, replicas)

    # Step 11: Validate the data content again
    resp = read_volume_data(core_api, pod_name, "test_file1")
    assert resp == test_data1
    resp = read_volume_data(core_api, pod_name, "test_file2")
    assert resp == test_data2

    # Step 12: Retry online expansion, should succeed
    volume.expand(size=EXPAND_SIZE)
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert volume.size == EXPAND_SIZE
    assert volume.size == engine.size

    # Step 13: Write more data then re-validate the data content
    test_data3 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data3, "test_file3")
    resp = read_volume_data(core_api, pod_name, "test_file1")
    assert resp == test_data1
    resp = read_volume_data(core_api, pod_name, "test_file2")
    assert resp == test_data2
    resp = read_volume_data(core_api, pod_name, "test_file3")
    assert resp == test_data3

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, expansion_pvc_name)
    delete_and_wait_pv(core_api, expansion_pv_name)


@pytest.mark.coretest  # NOQA
def test_running_volume_with_scheduling_failure(
        client, core_api, volume_name, pod):  # NOQA
    """
    Test if the running volume still work fine
    when there is a scheduling failed replica

    Prerequisite:
    Setting "soft anti-affinity" is false.
    Setting "replica-replenishment-wait-interval" is 0

    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data to the pod volume and get the md5sum.
    4. Disable the scheduling for a node contains a running replica.
    5. Crash the replica on the scheduling disabled node for the volume.
    6. Wait for the scheduling failure which is caused
       by the new replica creation.
    7. Verify:
      7.1. `volume.ready == True`.
      7.2. `volume.conditions[scheduled].status == False`.
      7.3. the volume is Degraded.
      7.4. the new replica is created but it is not running.
    8. Write more data to the volume and get the md5sum
    9. Delete the pod and wait for the volume detached.
    10. Verify the scheduling failed replica is removed.
    11. Verify:
      11.1. `volume.ready == True`.
      11.2. `volume.conditions[scheduled].status == True`
    12. Recreate a new pod for the volume and wait for the pod running.
    13. Validate the volume content, then check if data writing looks fine.
    14. Clean up pod, PVC, and PV.
    """

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value="0")

    data_path1 = "/data/test1"
    test_pv_name = "pv-" + volume_name
    test_pvc_name = "pvc-" + volume_name
    test_pod_name = "pod-" + volume_name

    volume = create_and_check_volume(client, volume_name, size=str(1 * Gi))
    create_pv_for_volume(client, core_api, volume, test_pv_name)
    create_pvc_for_volume(client, core_api, volume, test_pvc_name)

    pod['metadata']['name'] = test_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': test_pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)
    wait_for_volume_healthy(client, volume_name)
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path1, DATA_SIZE_IN_MB_1)
    original_md5sum1 = get_pod_data_md5sum(core_api, test_pod_name,
                                           data_path1)

    volume = client.by_id_volume(volume_name)
    existing_replicas = {}
    for r in volume.replicas:
        existing_replicas[r.name] = r
    node = client.by_id_node(volume.replicas[0].hostId)
    node = set_node_scheduling(client, node, allowScheduling=False)
    common.wait_for_node_update(client, node.id,
                                "allowScheduling", False)

    crash_replica_processes(client, core_api, volume_name,
                            replicas=[volume.replicas[0]],
                            wait_to_fail=False)

    # Wait for scheduling failure.
    # It means the new replica is created but fails to be scheduled.
    wait_for_volume_condition_scheduled(client, volume_name, "status",
                                        CONDITION_STATUS_FALSE)
    wait_for_volume_condition_scheduled(client, volume_name, "reason",
                                        CONDITION_REASON_SCHEDULING_FAILURE)
    volume = wait_for_volume_degraded(client, volume_name)
    assert len(volume.replicas) == 4
    assert volume.ready
    for r in volume.replicas:
        if r.name not in existing_replicas:
            new_replica = r
            break
    assert new_replica
    assert not new_replica.running
    assert not new_replica.hostId

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_1)
    original_md5sum2 = get_pod_data_md5sum(core_api, test_pod_name, data_path2)

    delete_and_wait_pod(core_api, test_pod_name)
    wait_for_volume_detached(client, volume_name)
    volume = wait_for_volume_condition_scheduled(client, volume_name, "status",
                                                 CONDITION_STATUS_TRUE)
    assert volume.ready
    # The scheduling failed replica will be removed
    # so that the volume can be reattached later.
    assert len(volume.replicas) == 3
    for r in volume.replicas:
        assert r.hostId != ""
        assert r.name != new_replica.name

    create_and_wait_pod(core_api, pod)
    wait_for_volume_degraded(client, volume_name)

    md5sum1 = get_pod_data_md5sum(core_api, test_pod_name, data_path1)
    assert md5sum1 == original_md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, test_pod_name, data_path2)
    assert md5sum2 == original_md5sum2

    # The data writing is fine
    data_path3 = "/data/test3"
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path3, DATA_SIZE_IN_MB_1)
    get_pod_data_md5sum(core_api, test_pod_name, data_path3)

    delete_and_wait_pod(core_api, test_pod_name)
    delete_and_wait_pvc(core_api, test_pvc_name)
    delete_and_wait_pv(core_api, test_pv_name)


@pytest.mark.coretest  # NOQA
def test_expansion_with_scheduling_failure(
        client, core_api, volume_name, pod, pvc, storage_class):  # NOQA
    """
    Test if the running volume with scheduling failure
    can be expanded after the detachment.

    Prerequisite:
    Setting "soft anti-affinity" is false.

    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data to the pod volume and get the md5sum.
    4. Disable the scheduling for a node contains a running replica.
    5. Crash the replica on the scheduling disabled node for the volume.
       Then delete the failed replica so that it won't be reused.
    6. Wait for the scheduling failure which is caused
       by the new replica creation.
    7. Verify:
      7.1. `volume.ready == True`.
      7.2. `volume.conditions[scheduled].status == False`.
      7.3. the volume is Degraded.
      7.4. the new replica is created but it is not running.
    8. Write more data to the volume and get the md5sum
    9. Delete the pod and wait for the volume detached.
    10. Verify the scheduling failed replica is removed.
    11. Verify:
      11.1. `volume.ready == True`.
      11.2. `volume.conditions[scheduled].status == True`
    12. Expand the volume and wait for the expansion succeeds.
    13. Verify there is no rebuild replica after the expansion.
    14. Recreate a new pod for the volume and wait for the pod running.
    15. Validate the volume content.
    16. Verify the expanded part can be read/written correctly.
    17. Enable the node scheduling.
    18. Wait for the volume rebuild succeeds.
    19. Verify the data written in the expanded part.
    20. Clean up pod, PVC, and PV.

    Notice that the step 1 to step 11 is identical with
    those of the case test_running_volume_with_scheduling_failure().
    """
    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    data_path1 = "/data/test1"
    pvc['spec']['resources']['requests']['storage'] = str(300 * Mi)
    create_storage_class(storage_class)

    test_pod_name = 'expand-scheduling-failed-test'
    test_pvc_name = test_pod_name + "-pvc"
    pvc['metadata']['name'] = test_pvc_name
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    common.create_pvc(pvc)

    pod['metadata']['name'] = test_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {'claimName': test_pvc_name},
    }]
    create_and_wait_pod(core_api, pod)

    pv = common.wait_and_get_pv_for_pvc(core_api, test_pvc_name)
    assert pv.status.phase == "Bound"
    test_pv_name = pv.metadata.name
    volume_name = pv.spec.csi.volume_handle

    wait_for_volume_healthy(client, volume_name)
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path1, DATA_SIZE_IN_MB_1)
    original_md5sum1 = get_pod_data_md5sum(core_api, test_pod_name,
                                           data_path1)

    volume = client.by_id_volume(volume_name)
    old_replicas = {}
    for r in volume.replicas:
        old_replicas[r.name] = r
    failed_replica = volume.replicas[0]
    node = client.by_id_node(failed_replica.hostId)
    node = set_node_scheduling(client, node, allowScheduling=False)
    common.wait_for_node_update(client, node.id,
                                "allowScheduling", False)

    crash_replica_processes(client, core_api, volume_name,
                            replicas=[failed_replica],
                            wait_to_fail=False)

    # Remove the failed replica so that it won't be reused later
    volume = wait_for_volume_degraded(client, volume_name)
    volume.replicaRemove(name=failed_replica.name)

    # Wait for scheduling failure.
    # It means the new replica is created but fails to be scheduled.
    wait_for_volume_condition_scheduled(client, volume_name, "status",
                                        CONDITION_STATUS_FALSE)
    wait_for_volume_condition_scheduled(client, volume_name, "reason",
                                        CONDITION_REASON_SCHEDULING_FAILURE)
    volume = wait_for_volume_degraded(client, volume_name)
    assert len(volume.replicas) == 3
    assert volume.ready
    for r in volume.replicas:
        assert r.name != failed_replica.name
        if r.name not in old_replicas:
            new_replica = r
            break
    assert new_replica
    assert not new_replica.running
    assert not new_replica.hostId

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_1)
    original_md5sum2 = get_pod_data_md5sum(core_api, test_pod_name, data_path2)

    delete_and_wait_pod(core_api, test_pod_name)
    wait_for_volume_detached(client, volume_name)
    volume = wait_for_volume_condition_scheduled(client, volume_name, "status",
                                                 CONDITION_STATUS_TRUE)
    assert volume.ready
    # The scheduling failed replica will be removed
    # so that the volume can be reattached later.
    assert len(volume.replicas) == 2
    for r in volume.replicas:
        assert r.hostId != ""
        assert r.name != new_replica.name

    expanded_size = str(400 * Mi)
    volume.expand(size=expanded_size)
    wait_for_volume_expansion(client, volume_name, expanded_size)
    volume = wait_for_volume_detached(client, volume_name)
    assert volume.size == expanded_size
    assert len(volume.replicas) == 2
    for r in volume.replicas:
        assert r.name in old_replicas

    create_and_wait_pod(core_api, pod)
    wait_for_volume_degraded(client, volume_name)

    md5sum1 = get_pod_data_md5sum(core_api, test_pod_name, data_path1)
    assert md5sum1 == original_md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, test_pod_name, data_path2)
    assert md5sum2 == original_md5sum2

    # The data writing is fine
    data_path3 = "/data/test3"
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path3, DATA_SIZE_IN_MB_1)
    original_md5sum3 = get_pod_data_md5sum(core_api, test_pod_name, data_path3)

    node = client.by_id_node(failed_replica.hostId)
    set_node_scheduling(client, node, allowScheduling=True)
    wait_for_volume_healthy(client, volume_name)

    md5sum3 = get_pod_data_md5sum(core_api, test_pod_name, data_path3)
    assert md5sum3 == original_md5sum3

    delete_and_wait_pod(core_api, test_pod_name)
    delete_and_wait_pvc(core_api, test_pvc_name)
    delete_and_wait_pv(core_api, test_pv_name)


def test_backup_lock_deletion_during_restoration(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test backup locks
    Context:
    To test the locking mechanism that utilizes the backupstore,
    to prevent the following case of concurrent operations.
    - prevent backup deletion during backup restoration

    steps:
    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data to the pod volume and get the md5sum.
    4. Take a backup.
    5. Wait for the backup to be completed.
    6. Start backup restoration for the backup creation.
    7. Wait for restoration to be in progress.
    8. Delete the backup from the backup store.
    9. Wait for the restoration to be completed.
    10. Assert the data from the restored volume with md5sum.
    11. Assert the backup count in the backup store with 0.
    """
    common.update_setting(client,
                          common.SETTING_DEGRADED_AVAILABILITY, "false")

    backupstore_cleanup(client)
    std_volume_name = volume_name + "-std"
    restore_volume_name = volume_name + "-restore"
    _, _, _, std_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
            data_size_in_mb=DATA_SIZE_IN_MB_2)
    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)

    _, b = common.find_backup(client, std_volume_name, snap1.name)
    client.create_volume(name=restore_volume_name, fromBackup=b.url)
    wait_for_volume_restoration_start(client, restore_volume_name, b.name)

    backup_volume = client.by_id_backupVolume(std_volume_name)
    backup_volume.backupDelete(name=b.name)

    wait_for_volume_restoration_completed(client, restore_volume_name)
    wait_for_backup_delete(client, std_volume_name, b.name)
    restore_volume = wait_for_volume_detached(client, restore_volume_name)
    assert len(restore_volume.replicas) == 3

    restore_pod_name = restore_volume_name + "-pod"
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"
    restore_pod = pod_make(name=restore_pod_name)
    create_pv_for_volume(client, core_api, restore_volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, restore_volume, restore_pvc_name)
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]
    create_and_wait_pod(core_api, restore_pod)

    restore_volume = client.by_id_volume(restore_volume_name)
    assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_HEALTHY

    md5sum = get_pod_data_md5sum(core_api, restore_pod_name, "/data/test")
    assert std_md5sum == md5sum

    try:
        _, b = common.find_backup(client, std_volume_name, snap1.name)
    except AssertionError:
        b = None
    assert b is None


def test_backup_lock_deletion_during_backup(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test backup locks
    Context:
    To test the locking mechanism that utilizes the backupstore,
    to prevent the following case of concurrent operations.
    - prevent backup deletion while a backup is in progress

    steps:
    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data to the pod volume and get the md5sum.
    4. Take a backup.
    5. Wait for the backup to be completed.
    6. Write more data into the volume and compute md5sum.
    7. Take another backup of the volume.
    8. While backup is in progress, delete the older backup up.
    9. Wait for the backup creation in progress to be completed.
    10. Check the backup store, there should be 1 backup.
    11. Restore the latest backup.
    12. Wait for the restoration to be completed. Assert md5sum from step 6.
    """
    common.update_setting(client,
                          common.SETTING_DEGRADED_AVAILABILITY, "false")

    backupstore_cleanup(client)
    std_volume_name = volume_name + "-std"
    restore_volume_name_1 = volume_name + "-restore-1"

    std_pod_name, _, _, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name)
    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    _, b1 = common.find_backup(client, std_volume_name, snap1.name)

    write_pod_volume_random_data(core_api, std_pod_name, "/data/test",
                                 DATA_SIZE_IN_MB_3)

    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, "/data/test")
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_to_start(client, std_volume_name, snapshot_name=snap2.name)

    backup_volume = client.by_id_backupVolume(std_volume_name)
    backup_volume.backupDelete(name=b1.name)

    wait_for_backup_completion(client, std_volume_name, snap2.name,
                               retry_count=600)
    wait_for_backup_delete(client, std_volume_name, b1.name)

    _, b2 = common.find_backup(client, std_volume_name, snap2.name)
    assert b2 is not None

    try:
        _, b1 = common.find_backup(client, std_volume_name, snap1.name)
    except AssertionError:
        b1 = None
    assert b1 is None

    client.create_volume(name=restore_volume_name_1, fromBackup=b2.url)

    wait_for_volume_restoration_completed(client, restore_volume_name_1)
    restore_volume_1 = wait_for_volume_detached(client, restore_volume_name_1)
    assert len(restore_volume_1.replicas) == 3

    restore_pod_name_1 = restore_volume_name_1 + "-pod"
    restore_pv_name_1 = restore_volume_name_1 + "-pv"
    restore_pvc_name_1 = restore_volume_name_1 + "-pvc"
    restore_pod_1 = pod_make(name=restore_pod_name_1)
    create_pv_for_volume(client, core_api, restore_volume_1, restore_pv_name_1)
    create_pvc_for_volume(client, core_api, restore_volume_1,
                          restore_pvc_name_1)
    restore_pod_1['spec']['volumes'] = [create_pvc_spec(restore_pvc_name_1)]
    create_and_wait_pod(core_api, restore_pod_1)

    md5sum2 = get_pod_data_md5sum(core_api, restore_pod_name_1, "/data/test")

    assert std_md5sum2 == md5sum2


def test_backup_lock_creation_during_deletion(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test backup locks
    Context:
    To test the locking mechanism that utilizes the backupstore,
    to prevent the following case of concurrent operations.
    - prevent backup creation during backup deletion

    steps:
    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data (DATA_SIZE_IN_MB_2) to the pod volume and get the md5sum.
    4. Take a backup.
    5. Wait for the backup to be completed.
    6. Delete the backup.
    7. Create another backup of the same volume.
    8. Wait for the delete backup to be completed.
    8. Wait for the backup to be completed.
    9. Assert there is 1 backup in the backup store.
    """
    backupstore_cleanup(client)
    std_volume_name = volume_name + "-std"

    std_pod_name, _, _, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
            data_size_in_mb=DATA_SIZE_IN_MB_1)
    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    _, b1 = common.find_backup(client, std_volume_name, snap1.name)

    write_pod_volume_random_data(core_api, std_pod_name,
                                 "/data/test2", DATA_SIZE_IN_MB_1)

    backup_volume = client.by_id_backupVolume(std_volume_name)
    backup_volume.backupDelete(name=b1.name)

    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)

    wait_for_backup_delete(client, volume_name, b1.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name)

    try:
        _, b1 = common.find_backup(client, std_volume_name, snap1.name)
    except AssertionError:
        b1 = None
    assert b1 is None
    _, b2 = common.find_backup(client, std_volume_name, snap2.name)


@pytest.mark.skip(reason="This test takes more than 20 mins to run")  # NOQA
def test_backup_lock_restoration_during_deletion(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test backup locks
    Context:
    To test the locking mechanism that utilizes the backupstore,
    to prevent the following case of concurrent operations.
    - prevent backup restoration during backup deletion

    steps:
    1. Create a volume, then create the corresponding PV, PVC and Pod.
    2. Wait for the pod running and the volume healthy.
    3. Write data to the pod volume and get the md5sum.
    4. Take a backup.
    5. Wait for the backup to be completed.
    6. Write more data (1.5 Gi) to the volume and take another backup.
    7. Wait for the 2nd backup to be completed.
    8. Delete the 2nd backup.
    9. Without waiting for the backup deletion completion, restore the 1st
       backup from the backup store.
    10. Verify the restored volume become faulted.
    11. Wait for the 2nd backup deletion and assert the count of the backups
       with 1 in the backup store.
    """
    backupstore_cleanup(client)
    std_volume_name = volume_name + "-std"
    restore_volume_name = volume_name + "-restore"
    std_pod_name, _, _, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
            volume_size=str(3*Gi), data_size_in_mb=DATA_SIZE_IN_MB_1)
    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    std_volume.snapshotBackup(name=snap1.name)
    backup_volume = client.by_id_backupVolume(std_volume_name)
    _, b1 = common.find_backup(client, std_volume_name, snap1.name)

    write_pod_volume_random_data(core_api, std_pod_name,
                                 "/data/test2", 1500)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name,
                               retry_count=1200)
    _, b2 = common.find_backup(client, std_volume_name, snap2.name)

    backup_volume.backupDelete(name=b2.name)

    client.create_volume(name=restore_volume_name, fromBackup=b1.url)
    wait_for_volume_detached(client, restore_volume_name)
    restore_volume = client.by_id_volume(restore_volume_name)
    assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_FAULTED

    wait_for_backup_delete(client, volume_name, b2.name)

    _, b1 = common.find_backup(client, std_volume_name, snap1.name)
    assert b1 is not None

    try:
        _, b2 = common.find_backup(client, std_volume_name, snap2.name)
    except AssertionError:
        b2 = None
    assert b2 is None


@pytest.mark.coretest  # NOQA
def test_allow_volume_creation_with_degraded_availability(client, volume_name):  # NOQA
    """
    Test Allow Volume Creation with Degraded Availability (API)

    Requirement:
    1. Set `allow-volume-creation-with-degraded-availability` to true.
    2. `node-level-soft-anti-affinity` to false.

    Steps:
    (degraded availablity)
    1. Disable scheduling for node 2 and 3.
    2. Create a volume with three replicas.
        1. Volume should be `ready` after creation and `Scheduled` is true.
        2. One replica schedule succeed. Two other replicas failed scheduling.
    3. Enable the scheduling of node 2.
        1. One additional replica of the volume will become scheduled.
        2. The other replica is still failed to schedule.
        3. Scheduled condition is still true.
    4. Attach the volume.
        1. After the volume is attached, scheduled condition become false.
    5. Write data to the volume.
    6. Detach the volume.
        1. Scheduled condition should become true.
    7. Reattach the volume to verify the data.
        1. Scheduled condition should become false.
    8. Enable the scheduling for the node 3.
    9. Wait for the scheduling condition to become true.
    10. Detach and reattach the volume to verify the data.
    """
    # enable volume create with degraded availability
    degraded_availability_setting = \
        client.by_id_setting(common.SETTING_DEGRADED_AVAILABILITY)
    client.update(degraded_availability_setting, value="true")

    # disable node level soft anti-affinity
    replica_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_soft_anti_affinity_setting, value="false")

    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # disable node 2 and 3 to schedule to node 1
    client.update(node2, allowScheduling=False)
    client.update(node3, allowScheduling=False)

    # create volume
    volume = create_and_check_volume(client, volume_name, num_of_replicas=3)
    assert volume.ready
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "True"

    # check only 1 replica scheduled successfully
    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name],
                                      expect_success=1, expect_fail=2,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)

    # enable node 2 to schedule to node 1 and 2
    client.update(node2, allowScheduling=True)

    # check 2 replicas scheduled successfully
    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name, node2.name],
                                      expect_success=2, expect_fail=1,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)

    volume = client.by_id_volume(volume_name)
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "True"

    # attach volume
    self_host = get_self_host_id()
    volume.attach(hostId=self_host)
    volume = common.wait_for_volume_degraded(client, volume_name)
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "False"

    data = write_volume_random_data(volume, {})

    # detach volume
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "True"

    # re-attach volume to verify the data
    volume.attach(hostId=self_host)
    volume = common.wait_for_volume_degraded(client, volume_name)
    check_volume_data(volume, data)
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "False"

    # enable node 3 to schedule to node 1, 2 and 3
    client.update(node3, allowScheduling=True)
    common.wait_for_volume_condition_scheduled(client, volume_name,
                                               "status", "True")

    # detach and re-attach the volume to verify the data
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=self_host)
    volume = common.wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data)


@pytest.mark.coretest  # NOQA
def test_allow_volume_creation_with_degraded_availability_error(client, volume_name):  # NOQA
    """
    Test Allow Volume Creation with Degraded Availability (API)

    Requirement:
    1. Set `allow-volume-creation-with-degraded-availability` to true.
    2. `node-level-soft-anti-affinity` to false.

    Steps:
    (no availability)
    1. Disable all nodes' scheduling.
    2. Create a volume with three replicas.
        1. Volume should be NotReady after creation.
        2. Scheduled condition should become false.
    3. Attaching the volume should result in error.
    4. Enable one node's scheduling.
        1. Volume should become Ready soon.
        2. Scheduled condition should become true.
    5. Attach the volume. Write data. Detach and reattach to verify the data.
    """
    # enable volume create with degraded availability
    degraded_availability_setting = \
        client.by_id_setting(common.SETTING_DEGRADED_AVAILABILITY)
    client.update(degraded_availability_setting, value="true")

    # disable node level soft anti-affinity
    replica_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_soft_anti_affinity_setting, value="false")

    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # disable node 1, 2 and 3 to make 0 available node
    client.update(node1, allowScheduling=False)
    client.update(node2, allowScheduling=False)
    client.update(node3, allowScheduling=False)

    # create volume
    volume = create_and_check_volume(client, volume_name, num_of_replicas=3)
    assert not volume.ready
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "False"

    # attach the volume
    self_host = get_self_host_id()
    with pytest.raises(Exception) as e:
        volume.attach(hostId=self_host)
    assert "unable to attach volume" in str(e.value)

    # enable node 1
    client.update(node1, allowScheduling=True)

    # check only 1 replica scheduled successfully
    common.wait_for_replica_scheduled(client, volume_name,
                                      to_nodes=[node1.name],
                                      expect_success=1, expect_fail=2,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)
    volume = common.wait_for_volume_status(client, volume_name,
                                           VOLUME_FIELD_READY, True)
    assert volume.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "True"

    # attach the volume and write some data
    volume.attach(hostId=self_host)
    volume = common.wait_for_volume_degraded(client, volume_name)
    data = write_volume_random_data(volume, {})

    # detach and re-attach the volume to verify the data
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=self_host)
    volume = common.wait_for_volume_degraded(client, volume_name)
    check_volume_data(volume, data)


def test_multiple_volumes_creation_with_degraded_availability(set_random_backupstore, client, core_api, apps_api, storage_class, statefulset):  # NOQA
    """
    Scenario: verify multiple volumes with degraded availability can be
              created, attached, detached, and deleted at nearly the same time.

    Given new StorageClass created with `numberOfReplicas=5`.

    When set `allow-volume-creation-with-degraded-availability` to `True`.
    And deploy this StatefulSet:
        https://github.com/longhorn/longhorn/issues/2073#issuecomment-742948726
    Then all 10 volumes are healthy in 1 minute.

    When delete the StatefulSet.
    then all 10 volumes are detached in 1 minute.

    When find and delete the PVC of the 10 volumes.
    Then all 10 volumes are deleted in 1 minute.
    """
    storage_class['parameters']['numberOfReplicas'] = "5"
    create_storage_class(storage_class)

    common.update_setting(client,
                          common.SETTING_DEGRADED_AVAILABILITY, "true")

    sts_spec = statefulset['spec']
    sts_spec['podManagementPolicy'] = "Parallel"
    sts_spec['replicas'] = 10
    sts_spec['volumeClaimTemplates'][0]['spec']['storageClassName'] = \
        storage_class['metadata']['name']
    statefulset['spec'] = sts_spec
    common.create_and_wait_statefulset(statefulset)
    pod_list = common.get_statefulset_pod_info(core_api, statefulset)
    retry_counts = int(60 / RETRY_INTERVAL)
    common.wait_for_pods_volume_state(
        client, pod_list,
        common.VOLUME_FIELD_ROBUSTNESS,
        common.VOLUME_ROBUSTNESS_HEALTHY,
        retry_counts=retry_counts
    )

    apps_api.delete_namespaced_stateful_set(
        name=statefulset['metadata']['name'],
        namespace=statefulset['metadata']['namespace'],
        body=k8sclient.V1DeleteOptions()
    )
    common.wait_for_pods_volume_state(
        client, pod_list,
        common.VOLUME_FIELD_STATE,
        common.VOLUME_STATE_DETACHED,
        retry_counts=retry_counts
    )

    for p in pod_list:
        common.delete_and_wait_pvc(core_api, p['pvc_name'],
                                   retry_counts=retry_counts)
    common.wait_for_pods_volume_delete(client, pod_list,
                                       retry_counts=retry_counts)


def test_allow_volume_creation_with_degraded_availability_restore(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod, pod_make):  # NOQA
    """
    Test Allow Volume Creation with Degraded Availability (Restore)

    Requirement:
    1. Set `allow-volume-creation-with-degraded-availability` to true.
    2. `node-level-soft-anti-affinity` to false.
    3. `replica-replenishment-wait-interval` to 0.
    4. Create a backup of 800MB.

    Steps:
    (restore)
    1. Disable scheduling for node 2 and 3.
    2. Restore a volume with 3 replicas.
        1. The scheduled condition is true.
        2. Only node 1 replica become scheduled.
    3. Enable scheduling for node 2.
    4. Wait for the restore to complete and volume detach automatically.
       Then check the scheduled condition still true.
    5. Attach and wait for the volume.
        1. Replicas scheduling to node 1 and 2 success.
           Replica scheduling to node 3 fail.
        2. The scheduled condition becomes false.
        3. Verify the data.
    """
    # enable volume create with degraded availability
    degraded_availability_setting = \
        client.by_id_setting(common.SETTING_DEGRADED_AVAILABILITY)
    client.update(degraded_availability_setting, value="true")

    # disable node level soft anti-affinity
    replica_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_soft_anti_affinity_setting, value="false")

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value="0")

    # create a backup
    backupstore_cleanup(client)

    data_path = "/data/test"
    src_vol_name = generate_volume_name()
    _, _, _, src_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, src_vol_name,
            data_path=data_path, data_size_in_mb=common.DATA_SIZE_IN_MB_4)

    src_vol = client.by_id_volume(src_vol_name)
    src_snap = create_snapshot(client, src_vol_name)
    src_vol.snapshotBackup(name=src_snap.name)
    wait_for_backup_completion(client, src_vol_name, src_snap.name,
                               retry_count=600)
    _, backup = find_backup(client, src_vol_name, src_snap.name)

    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # disable node 2 and 3 to schedule to node 1
    client.update(node2, allowScheduling=False)
    client.update(node3, allowScheduling=False)

    # restore volume
    dst_vol_name = generate_volume_name()
    client.create_volume(name=dst_vol_name, size=str(1*Gi),
                         numberOfReplicas=3, fromBackup=backup.url)
    common.wait_for_volume_replica_count(client, dst_vol_name, 3)
    common.wait_for_volume_restoration_start(client, dst_vol_name, backup.name)
    common.wait_for_volume_degraded(client, dst_vol_name)

    # check only 1 replica scheduled successfully
    common.wait_for_replica_scheduled(client, dst_vol_name,
                                      to_nodes=[node1.name],
                                      expect_success=1,
                                      expect_fail=2,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)

    # Enable node 2 to schedule to node 1, 2
    client.update(node2, allowScheduling=True)

    # wait to complete restore
    common.wait_for_volume_restoration_completed(client, dst_vol_name)
    dst_vol = common.wait_for_volume_detached(client, dst_vol_name)
    assert dst_vol.conditions[VOLUME_CONDITION_SCHEDULED]['status'] == "True"

    # attach the volume
    create_pv_for_volume(client, core_api, dst_vol, dst_vol_name)
    create_pvc_for_volume(client, core_api, dst_vol, dst_vol_name)

    dst_pod_name = dst_vol_name + "-pod"
    pod['metadata']['name'] = dst_vol_name + "-pod"
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': dst_vol_name,
        },
    }]
    create_and_wait_pod(core_api, pod)
    # check 2 replica scheduled successfully
    dst_vol = common.wait_for_replica_scheduled(client, dst_vol_name,
                                                to_nodes=[node1.name,
                                                          node2.name],
                                                expect_success=2,
                                                expect_fail=1,
                                                chk_vol_healthy=False,
                                                chk_replica_running=False)
    wait_for_volume_condition_scheduled(client, dst_vol_name,
                                        "status", "False")

    # verify the data
    dst_md5sum = get_pod_data_md5sum(core_api, dst_pod_name, data_path)
    assert src_md5sum == dst_md5sum


def test_allow_volume_creation_with_degraded_availability_dr(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod, pod_make):  # NOQA
    """
    Test Allow Volume Creation with Degraded Availability (Restore)

    Requirement:
    1. Set `allow-volume-creation-with-degraded-availability` to true.
    2. `node-level-soft-anti-affinity` to false.
    3. Create a backup of 800MB.

    Steps:
    (DR volume)
    1. Disable scheduling for node 2 and 3.
    2. Create a DR volume from backup with 3 replicas.
        1. The scheduled condition is false.
        2. Only node 1 replica become scheduled.
    3. Enable scheduling for node 2 and 3.
        1. Replicas scheduling to node 1, 2, 3 success.
        2. Wait for restore progress to complete.
        3. The scheduled condition becomes true.
    4. Activate, attach the volume, and verify the data.
    """
    # enable volume create with degraded availability
    degraded_availability_setting = \
        client.by_id_setting(common.SETTING_DEGRADED_AVAILABILITY)
    client.update(degraded_availability_setting, value="true")

    # disable node level soft anti-affinity
    replica_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_soft_anti_affinity_setting, value="false")

    # create a backup
    backupstore_cleanup(client)

    data_path = "/data/test"
    src_vol_name = generate_volume_name()
    _, _, _, src_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, src_vol_name,
            data_path=data_path, data_size_in_mb=common.DATA_SIZE_IN_MB_4)

    src_vol = client.by_id_volume(src_vol_name)
    src_snap = create_snapshot(client, src_vol_name)
    src_vol.snapshotBackup(name=src_snap.name)
    wait_for_backup_completion(client, src_vol_name, src_snap.name,
                               retry_count=600)
    _, backup = find_backup(client, src_vol_name, src_snap.name)

    nodes = client.list_node()
    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    # disable node 2 and 3 to schedule to node 1
    client.update(node2, allowScheduling=False)
    client.update(node3, allowScheduling=False)

    # create DR volume
    dst_vol_name = generate_volume_name()
    dst_vol = client.create_volume(name=dst_vol_name, size=str(1*Gi),
                                   numberOfReplicas=3,
                                   fromBackup=backup.url,
                                   frontend="",
                                   standby=True)
    common.wait_for_volume_replica_count(client, dst_vol_name, 3)
    wait_for_volume_restoration_start(client, dst_vol_name, backup.name)
    wait_for_volume_condition_scheduled(client, dst_vol_name,
                                        "status", "False")

    # check only 1 replica scheduled successfully
    common.wait_for_replica_scheduled(client, dst_vol_name,
                                      to_nodes=[node1.name],
                                      expect_success=1,
                                      expect_fail=2,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)

    # Enable node 2, 3 to schedule to node 1,2,3
    client.update(node2, allowScheduling=True)
    client.update(node3, allowScheduling=True)

    common.wait_for_replica_scheduled(client, dst_vol_name,
                                      to_nodes=[node1.name,
                                                node2.name,
                                                node3.name],
                                      expect_success=3,
                                      chk_vol_healthy=False,
                                      chk_replica_running=False)
    common.monitor_restore_progress(client, dst_vol_name)

    wait_for_volume_condition_scheduled(client, dst_vol_name,
                                        "status", "True")

    # activate the volume
    activate_standby_volume(client, dst_vol_name)

    # attach the volume
    dst_vol = client.by_id_volume(dst_vol_name)
    create_pv_for_volume(client, core_api, dst_vol, dst_vol_name)
    create_pvc_for_volume(client, core_api, dst_vol, dst_vol_name)

    dst_pod_name = dst_vol_name + "-pod"
    pod['metadata']['name'] = dst_vol_name + "-pod"
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': dst_vol_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    # verify the data
    dst_md5sum = get_pod_data_md5sum(core_api, dst_pod_name, data_path)
    assert src_md5sum == dst_md5sum


def test_cleanup_system_generated_snapshots(client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test Cleanup System Generated Snapshots

    1. Enabled 'Auto Cleanup System Generated Snapshot'.
    2. Create a volume and attach it to a node.
    3. Write some data to the volume and get the checksum of the data.
    4. Delete a random replica to trigger a system generated snapshot.
    5. Repeat Step 3 for 3 times, and make sure only one snapshot is left.
    6. Check the data with the saved checksum.
    """

    pod_name, _, _, md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, volume_name)

    volume = client.by_id_volume(volume_name)

    for i in range(3):
        replica_name = volume["replicas"][i]["name"]
        volume.replicaRemove(name=replica_name)
        wait_for_volume_degraded(client, volume_name)
        wait_for_volume_healthy(client, volume_name)

        volume = client.by_id_volume(volume_name)
        # For the below assertion, the number of snapshots is compared with 2
        # as the list of snapshot have the volume-head too.
        assert len(volume.snapshotList()) == 2

    read_md5sum1 = get_pod_data_md5sum(core_api, pod_name, "/data/test")
    assert md5sum1 == read_md5sum1


def test_volume_toomanysnapshots_condition(client, core_api, volume_name):  # NOQA
    """
    Test Volume TooManySnapshots Condition

    1. Create a volume and attach it to a node.
    2. Check the 'TooManySnapshots' condition is False.
    3. Writing data to this volume and meanwhile taking 100 snapshots.
    4. Check the 'TooManySnapshots' condition is True.
    5. Take one more snapshot to make sure snapshots works fine.
    6. Delete 2 snapshots, and check the 'TooManySnapshots' condition is
       False.
    """
    volume = create_and_check_volume(client, volume_name)
    self_hostId = get_self_host_id()
    volume = volume.attach(hostId=self_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    snap = {}
    max_count = 100
    for i in range(max_count):
        write_volume_random_data(volume, {})

        count = i + 1
        snap[count] = create_snapshot(client, volume_name)

        if count < max_count:
            volume = client.by_id_volume(volume_name)
            assert volume.conditions.TooManySnapshots.status == "False"
        else:
            wait_for_volume_condition_toomanysnapshots(client, volume_name,
                                                       "status", "True")

    snap[max_count + 1] = create_snapshot(client, volume_name)
    wait_for_volume_condition_toomanysnapshots(client, volume_name,
                                               "status", "True")

    volume = client.by_id_volume(volume_name)
    volume.snapshotDelete(name=snap[100].name)
    volume.snapshotDelete(name=snap[99].name)

    volume.snapshotPurge()
    volume = wait_for_snapshot_purge(client, volume_name,
                                     snap[100].name, snap[99].name)

    wait_for_volume_condition_toomanysnapshots(client, volume_name,
                                               "status", "False")


def prepare_data_volume_metafile(client, core_api, volume_name, csi_pv, pvc, pod, pod_make, data_path, test_writing_data=False, writing_data_path="/data/writing_data_file"):  # NOQA
    """
    Prepare volume and snapshot for volume metafile testing

    Setup:

    1. Create a pod using Longhorn volume
    2. Write some data to the volume then get the md5sum
    3. Create a snapshot
    4. Delete the pod and wait for the volume detached
    5. Pick up a replica on this host and get the replica data path
    """
    # create the pod with pv, pvc and write some data
    test_pod_name, _, test_pvc_name, data_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, volume_name,
            data_path=data_path)

    pod['metadata']['name'] = test_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': test_pvc_name,
        },
    }]

    snap1 = create_snapshot(client, volume_name)

    # choose the replica that is on this host
    volume = client.by_id_volume(volume_name)
    host_id = get_self_host_id()
    for replica in volume.replicas:
        if replica.hostId == host_id:
            break

    assert replica is not None, f'hostID: {host_id}, volume replica: {replica}'

    # get the volume metadata file path
    replica_data_path = replica.dataPath
    volume_meta_file = replica_data_path + "/volume.meta"

    if test_writing_data:
        # create random data to the pod in the background
        command = 'dd if=/dev/urandom of=' + writing_data_path + ' bs=1M' +\
                  ' count=' + str(common.DATA_SIZE_IN_MB_4) + ' &'
        exec_command_in_pod(core_api, command, test_pod_name, 'default')
    else:
        # make the volume detached
        delete_and_wait_pod(core_api, test_pod_name)
        wait_for_volume_detached(client, volume_name)

    return snap1, volume_meta_file, test_pod_name, data_md5sum1


def check_volume_and_snapshot_after_corrupting_volume_metadata_file(client, core_api, volume_name, pod, test_pod_name, data_path1, data_md5sum1, data_path2, snap): # NOQA
    """
    Test volume I/O and take/delete a snapshot
    """

    # recreate the pod and check if the volume will become healthy
    create_and_wait_pod(core_api, pod)
    volume = wait_for_volume_healthy(client, volume_name)

    # check if the data is not corrupted
    res_data_md5sum1 = get_pod_data_md5sum(core_api, test_pod_name, data_path1)
    assert data_md5sum1 == res_data_md5sum1

    # test that r/w is ok after recovering the volume metadata file
    write_pod_volume_random_data(core_api, test_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_1)
    get_pod_data_md5sum(core_api, test_pod_name, data_path2)

    # test that making/deleting a snapshot is ok
    # after recovering the volume metadata file
    create_snapshot(client, volume_name)
    # 1 snap1 1 snap2 1 volume-head
    wait_for_snapshot_count(volume, 3)
    volume.snapshotDelete(name=snap.name)
    # 1 snap2 1 volume-head
    wait_for_snapshot_count(volume, 2)


def test_volume_metafile_deleted(client, core_api, volume_name, csi_pv, pvc, pod, pod_make):  # NOQA
    """
    Scenario:

    Test volume should still work when the volume meta file is removed
    in the replica data path.

    Steps:

    1. Delete volume meta file in this replica data path
    2. Recreate the pod and wait for the volume attached
    3. Check if the volume is Healthy after the volume attached
    4. Check volume data
    5. Check if the volume still works fine by r/w data and
       creating/removing snapshots
    """
    data_path1 = "/data/file1"
    data_path2 = "/data/file2"

    snap1, volume_meta_file, test_pod_name, data_md5sum1 = \
        prepare_data_volume_metafile(client,
                                     core_api,
                                     volume_name,
                                     csi_pv,
                                     pvc,
                                     pod,
                                     pod_make,
                                     data_path1)

    # delete the volume metadata file of the volume on this host
    command = ["rm", "-f", volume_meta_file]
    subprocess.check_call(command)

    # test volume functionality
    check_volume_and_snapshot_after_corrupting_volume_metadata_file(
        client,
        core_api,
        volume_name,
        pod,
        test_pod_name,
        data_path1,
        data_md5sum1,
        data_path2, snap1
    )


def test_volume_metafile_empty(client, core_api, volume_name, csi_pv, pvc, pod, pod_make):  # NOQA
    """
    Scenario:

    Test volume should still work when there is an invalid volume meta file
    in the replica data path.

    Steps:

    1. Remove the content of the volume meta file in this replica data path
    2. Recreate the pod and wait for the volume attached
    3. Check if the volume is Healthy after the volume attached
    4. Check volume data
    5. Check if the volume still works fine by r/w data and
       creating/removing snapshots
    """
    data_path1 = "/data/file1"
    data_path2 = "/data/file2"

    snap1, volume_meta_file, test_pod_name, data_md5sum1 = \
        prepare_data_volume_metafile(client,
                                     core_api,
                                     volume_name,
                                     csi_pv,
                                     pvc,
                                     pod,
                                     pod_make,
                                     data_path1)

    # empty the volume metadata file of the volume on this host
    command = ["truncate", "--size", "0", volume_meta_file]
    subprocess.check_call(command)

    # test volume functionality
    check_volume_and_snapshot_after_corrupting_volume_metadata_file(
        client,
        core_api,
        volume_name,
        pod,
        test_pod_name,
        data_path1,
        data_md5sum1,
        data_path2,
        snap1
    )


def test_volume_metafile_deleted_when_writing_data(client, core_api, volume_name, csi_pv, pvc, pod, pod_make):  # NOQA
    """
    Scenario:

    While writing data, test volume should still work
    when the volume meta file is deleted in the replica data path.

    Steps:

    1. Create a pod using Longhorn volume
    2. Delete volume meta file in this replica data path
    3. Recreate the pod and wait for the volume attached
    4. Check if the volume is Healthy after the volume attached
    5. Check volume data
    6. Check if the volume still works fine by r/w data and
       creating/removing snapshots
    """
    data_path1 = "/data/file1"
    data_path2 = "/data/file2"

    snap1, volume_meta_file, test_pod_name, data_md5sum1 = \
        prepare_data_volume_metafile(client,
                                     core_api,
                                     volume_name,
                                     csi_pv,
                                     pvc,
                                     pod,
                                     pod_make,
                                     data_path1,
                                     test_writing_data=True)

    # delete the volume metadata file of the volume on this host
    command = ["rm", "-f", volume_meta_file]
    subprocess.check_call(command)

    # make the volume detached and metafile should be reconstructed.
    delete_and_wait_pod(core_api, test_pod_name)
    wait_for_volume_detached(client, volume_name)

    # test volume functionality
    check_volume_and_snapshot_after_corrupting_volume_metadata_file(
        client,
        core_api,
        volume_name,
        pod,
        test_pod_name,
        data_path1,
        data_md5sum1,
        data_path2,
        snap1
    )


def test_expand_pvc_with_size_round_up(client, core_api, volume_name):  # NOQA
    """
    test expand longhorn volume with pvc

    1. Create LHV,PV,PVC with size '1Gi'
    2. Attach, write data, and detach
    3. Expand volume size to '2000000000/2G' and
        check if size round up '2000683008/1908Mi'
    4. Attach, write data, and detach
    5. Expand volume size to '2Gi' and check if size is '2147483648'
    6. Attach, write data, and detach
    """

    static_sc_name = "longhorn"
    setting = client.by_id_setting(SETTING_DEFAULT_LONGHORN_STATIC_SC)
    setting = client.update(setting, value=static_sc_name)
    assert setting.value == static_sc_name

    volume = create_and_check_volume(client, volume_name, 2, str(1 * Gi))
    create_pv_for_volume(client, core_api, volume, volume_name)
    create_pvc_for_volume(client, core_api, volume, volume_name)

    self_hostId = get_self_host_id()
    volume.attach(hostId=self_hostId, disableFrontend=False)
    volume = wait_for_volume_healthy(client, volume_name)
    test_data = write_volume_random_data(volume)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)

    volume.expand(size="2000000000")
    wait_for_volume_expansion(client, volume_name)
    wait_for_volume_detached(client, volume_name)

    for i in range(DEFAULT_POD_TIMEOUT):
        claim = core_api.read_namespaced_persistent_volume_claim(
            name=volume_name, namespace='default')
        if claim.spec.resources.requests['storage'] == "2000683008" and \
                claim.status.capacity['storage'] == "1908Mi":
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert claim.spec.resources.requests['storage'] == "2000683008"
    assert claim.status.capacity['storage'] == "1908Mi"

    volume = client.by_id_volume(volume_name)
    assert volume.size == "2000683008"
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)

    self_hostId = get_self_host_id()
    volume.attach(hostId=self_hostId, disableFrontend=False)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, test_data, False)
    test_data = write_volume_random_data(volume)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)

    volume.expand(size=str(2 * Gi))
    wait_for_volume_expansion(client, volume_name)
    wait_for_volume_detached(client, volume_name)

    for i in range(DEFAULT_POD_TIMEOUT):
        claim = core_api.read_namespaced_persistent_volume_claim(
            name=volume_name, namespace='default')
        if claim.spec.resources.requests['storage'] == "2147483648" and \
                claim.status.capacity['storage'] == "2Gi":
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert claim.spec.resources.requests['storage'] == "2147483648"
    assert claim.status.capacity['storage'] == "2Gi"

    volume = client.by_id_volume(volume_name)
    assert volume.size == "2147483648"
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)

    self_hostId = get_self_host_id()
    volume.attach(hostId=self_hostId, disableFrontend=False)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, test_data, False)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


def test_workload_with_fsgroup(core_api, statefulset):  # NOQA
    """
    1. Deploy a StatefulSet workload that uses Longhorn volume and has
       securityContext set:
       ```
        securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
        ```
       See
       https://github.com/longhorn/longhorn/issues/2964#issuecomment-910117570
       for an example.
    2. Wait for the workload pod to be running
    3. Exec into the workload pod, cd into the mount point of the volume.
    4. Verify that the mount point has correct filesystem permission (e.g.,
       running `ls -l` on the mount point should return the permission in
       the format ****rw****
    5. Verify that we can read/write files.
    """
    statefulset_name = 'statefulset-non-root-access'
    pod_name = statefulset_name + '-0'

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['replicas'] = 1
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = 'longhorn'
    statefulset['spec']['template']['spec']['securityContext'] = {
        'runAsUser': 1000,
        'runAsGroup': 1000,
        'fsGroup': 1000
    }

    create_and_wait_statefulset(statefulset)

    write_pod_volume_random_data(core_api, pod_name, "/data/test",
                                 DATA_SIZE_IN_MB_1)
    get_pod_data_md5sum(core_api, pod_name, "/data/test")


def test_backuptarget_available_during_engine_image_not_ready(client, apps_api):  # NOQA
    """
    Test backup target available during engine image not ready

    1. Set backup target URL to S3 and NFS respectively
    2. Set poll interval to 0 and 300 respectively
    3. Scale down the engine image DaemonSet
    4. Check engine image in deploying state
    5. Configures backup target during engine image in not ready state
    6. Check backup target status.available=false
    7. Scale up the engine image DaemonSet
    8. Check backup target status.available=true
    9. Reset backup target setting
    10. Check backup target status.available=false
    """
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        url = ""
        cred_secret = ""
        if common.is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            url = backupsettings[0]
            cred_secret = backupsettings[1]
        elif common.is_backupTarget_nfs(backupstore):
            url = backupstore
            cred_secret = ""
        else:
            raise NotImplementedError

        poll_intervals = ["0", "300"]
        for poll_interval in poll_intervals:
            set_backupstore_poll_interval(client, poll_interval)

            default_img = common.get_default_engine_image(client)
            ds_name = "engine-image-" + default_img.name

            # Scale down the engine image DaemonSet
            daemonset = apps_api.read_namespaced_daemon_set(
                name=ds_name, namespace='longhorn-system')
            daemonset.spec.template.spec.node_selector = {'foo': 'bar'}
            apps_api.patch_namespaced_daemon_set(
                name=ds_name, namespace='longhorn-system', body=daemonset)

            # Check engine image in deploying state
            common.wait_for_engine_image_state(
                client, default_img.name, "deploying")
            deploying = False
            for _ in range(RETRY_COUNTS):
                default_img = client.by_id_engine_image(default_img.name)
                if not any(default_img.nodeDeploymentMap.values()):
                    deploying = True
                    break
                time.sleep(RETRY_INTERVAL)
            assert deploying is True

            # Set valid backup target during
            # the engine image in not ready state
            set_backupstore_url(client, url)
            set_backupstore_credential_secret(client, cred_secret)
            common.wait_for_backup_target_available(client, False)

            # Scale up the engine image DaemonSet
            body = [{"op": "remove",
                     "path": "/spec/template/spec/nodeSelector/foo"}]
            apps_api.patch_namespaced_daemon_set(
                name=ds_name, namespace='longhorn-system', body=body)
            common.wait_for_backup_target_available(client, True)

            # Sleep 1 second to prevent the same time
            # of BackupTarget CR spec.SyncRequestedAt
            time.sleep(1)

            # Reset backup store setting
            reset_backupstore_setting(client)
            common.wait_for_backup_target_available(client, False)


@pytest.mark.skipif('s3' not in BACKUPSTORE, reason='This test is only applicable for s3')  # NOQA
def test_aws_iam_role_arn(client, core_api):  # NOQA
    """
    Test AWS IAM Role ARN

    1. Set backup target to S3
    2. Check longhorn manager and aio instance manager Pods
       without 'iam.amazonaws.com/role' annotation
    3. Add AWS_IAM_ROLE_ARN to secret
    4. Check longhorn manager and aio instance manager Pods
       with 'iam.amazonaws.com/role' annotation
       and matches to AWS_IAM_ROLE_ARN in secret
    5. Update AWS_IAM_ROLE_ARN from secret
    6. Check longhorn manager and aio instance manager Pods
       with 'iam.amazonaws.com/role' annotation
       and matches to AWS_IAM_ROLE_ARN in secret
    7. Remove AWS_IAM_ROLE_ARN from secret
    8. Check longhorn manager and aio instance manager Pods
       without 'iam.amazonaws.com/role' annotation
    """
    set_backupstore_s3(client)

    lh_label = 'app=longhorn-manager'
    im_label = 'longhorn.io/instance-manager-type=aio'
    anno_key = 'iam.amazonaws.com/role'
    secret_name = backupstore_get_secret(client)

    common.wait_for_pod_annotation(
        core_api, lh_label, anno_key, None)
    common.wait_for_pod_annotation(
        core_api, im_label, anno_key, None)

    # Add secret key AWS_IAM_ROLE_ARN value test-aws-iam-role-arn
    secret = core_api.read_namespaced_secret(
        name=secret_name, namespace='longhorn-system')
    secret.data['AWS_IAM_ROLE_ARN'] = 'dGVzdC1hd3MtaWFtLXJvbGUtYXJu'
    core_api.patch_namespaced_secret(
        name=secret_name, namespace='longhorn-system', body=secret)

    common.wait_for_pod_annotation(
        core_api, lh_label, anno_key, 'test-aws-iam-role-arn')
    common.wait_for_pod_annotation(
        core_api, im_label, anno_key, 'test-aws-iam-role-arn')

    # Update secret key AWS_IAM_ROLE_ARN value test-aws-iam-role-arn-2
    secret = core_api.read_namespaced_secret(
        name=secret_name, namespace='longhorn-system')
    secret.data['AWS_IAM_ROLE_ARN'] = 'dGVzdC1hd3MtaWFtLXJvbGUtYXJuLTI='
    core_api.patch_namespaced_secret(
        name=secret_name, namespace='longhorn-system', body=secret)

    common.wait_for_pod_annotation(
        core_api, lh_label, anno_key, 'test-aws-iam-role-arn-2')
    common.wait_for_pod_annotation(
        core_api, im_label, anno_key, 'test-aws-iam-role-arn-2')

    # Remove secret key AWS_IAM_ROLE_ARN
    body = [{"op": "remove", "path": "/data/AWS_IAM_ROLE_ARN"}]
    core_api.patch_namespaced_secret(
        name=secret_name, namespace='longhorn-system', body=body)

    common.wait_for_pod_annotation(
        core_api, lh_label, anno_key, None)
    common.wait_for_pod_annotation(
        core_api, im_label, anno_key, None)


@pytest.mark.coretest   # NOQA
def test_restore_basic(set_random_backupstore, client, core_api, volume_name, pod):  # NOQA
    """
    Steps:
    1. Create a volume and attach to a pod.
    2. Write some data into the volume and compute the checksum m1.
    3. Create a backup say b1.
    4. Write some more data into the volume and compute the checksum m2.
    5. Create a backup say b2.
    6. Delete all the data from the volume.
    7. Write some more data into the volume and compute the checksum m3.
    8. Create a backup say b3.
    9. Restore backup b1 and verify the data with m1.
    10. Restore backup b2 and verify the data with m1 and m2.
    11. Restore backup b3 and verify the data with m3.
    12. Delete the backup b2.
    13. restore the backup b3 and verify the data with m3.
    """

    test_pv_name = "pv-" + volume_name
    test_pvc_name = "pvc-" + volume_name
    test_pod_name = "pod-" + volume_name

    volume = create_and_check_volume(client, volume_name, size=str(1 * Gi))
    create_pv_for_volume(client, core_api, volume, test_pv_name)
    create_pvc_for_volume(client, core_api, volume, test_pvc_name)
    pod['metadata']['name'] = test_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': test_pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)
    wait_for_volume_healthy(client, volume_name)

    # Write 1st data and take backup
    backup_volume, backup1, data_checksum_1 = \
        create_backup_from_volume_attached_to_pod(client, core_api,
                                                  volume_name, test_pod_name,
                                                  data_path='/data/test1')

    # Write 2nd data and take backup
    backup_volume, backup2, data_checksum_2 = \
        create_backup_from_volume_attached_to_pod(client, core_api,
                                                  volume_name, test_pod_name,
                                                  data_path='/data/test2')

    # Remove test1 and test2 files
    command = 'rm /data/test1 /data/test2'
    exec_command_in_pod(core_api, command, test_pod_name, 'default')

    # Write 3rd data and take backup
    backup_volume, backup3, data_checksum_3 = \
        create_backup_from_volume_attached_to_pod(client, core_api,
                                                  volume_name, test_pod_name,
                                                  data_path='/data/test3')

    delete_and_wait_pod(core_api, test_pod_name)

    # restore 1st backup and assert with data_checksum_1
    restored_data_checksum1, output, restore_pod_name = \
        restore_backup_and_get_data_checksum(client, core_api, backup1, pod,
                                             file_name='test1')
    assert data_checksum_1 == restored_data_checksum1['test1']

    delete_and_wait_pod(core_api, restore_pod_name)

    # restore 2nd backup and assert with data_checksum_1 and data_checksum_2
    restored_data_checksum2, output, restore_pod_name = \
        restore_backup_and_get_data_checksum(client, core_api, backup2, pod)
    assert data_checksum_1 == restored_data_checksum2['test1']
    assert data_checksum_2 == restored_data_checksum2['test2']

    delete_and_wait_pod(core_api, restore_pod_name)

    # restore 3rd backup and assert with data_checksum_3
    restored_data_checksum3, output, restore_pod_name = \
        restore_backup_and_get_data_checksum(client, core_api, backup3, pod,
                                             file_name='test3',
                                             command=r"ls /data | grep 'test1\|test2'")  # NOQA
    assert data_checksum_3 == restored_data_checksum3['test3']
    assert output == ''

    delete_and_wait_pod(core_api, restore_pod_name)

    # Delete the 2nd backup
    delete_backup(client, backup_volume.name, backup2.name)

    # restore 3rd backup again
    restored_data_checksum3, output, restore_pod_name = \
        restore_backup_and_get_data_checksum(client, core_api, backup3, pod,
                                             file_name='test3',
                                             command=r"ls /data | grep 'test1\|test2'")  # NOQA
    assert data_checksum_3 == restored_data_checksum3['test3']
    assert output == ''


@pytest.mark.coretest   # NOQA
def test_default_storage_class_syncup(core_api, request):  # NOQA
    """
    Steps:
    1. Record the current Longhorn-StorageClass-related ConfigMap
       `longhorn-storageclass`.
    2. Modify the default Longhorn StorageClass `longhorn`.
       e.g., update `reclaimPolicy` from `Delete` to `Retain`.
    3. Verify that the change is reverted immediately and the manifest is the
       same as the record in ConfigMap `longhorn-storageclass`.
    4. Delete the default Longhorn StorageClass `longhorn`.
    5. Verify that the StorageClass is recreated immediately with the manifest
       the same as the record in ConfigMap `longhorn-storageclass`.
    6. Modify the content of ConfigMap `longhorn-storageclass`.
    7. Verify that the modifications will be applied to the default Longhorn
       StorageClass `longhorn` immediately.
    8. Revert the modifications of the ConfigMaps. Then wait for the
       StorageClass sync-up.
    """
    def edit_configmap_allow_vol_exp(allow_exp):
        """
        allow_exp : bool, set allowVolumeExpansion
        """
        config_map = core_api.read_namespaced_config_map(
                                                "longhorn-storageclass",
                                                LONGHORN_NAMESPACE)
        config_map_data = yaml.safe_load(config_map.data["storageclass.yaml"])
        config_map_data["allowVolumeExpansion"] = allow_exp
        config_map.data["storageclass.yaml"] = yaml.dump(config_map_data)
        core_api.patch_namespaced_config_map("longhorn-storageclass",
                                             LONGHORN_NAMESPACE,
                                             config_map)

        for i in range(RETRY_COMMAND_COUNT):
            try:
                longhorn_storage_class = storage_api.read_storage_class(
                                                     "longhorn")
                assert longhorn_storage_class.allow_volume_expansion is allow_exp # NOQA
                break
            except Exception as e:
                print(e)
            finally:
                time.sleep(RETRY_INTERVAL)
        longhorn_storage_class = storage_api.read_storage_class("longhorn")
        assert longhorn_storage_class.allow_volume_expansion is allow_exp

    def finalizer():

        edit_configmap_allow_vol_exp(True)

    request.addfinalizer(finalizer)

    # step 1
    storage_api = common.get_storage_api_client()
    config_map = core_api.read_namespaced_config_map("longhorn-storageclass",
                                                     LONGHORN_NAMESPACE)
    config_map_data = yaml.safe_load(config_map.data["storageclass.yaml"])

    # step 2
    longhorn_storage_class = storage_api.read_storage_class("longhorn")
    storage_class_data = \
        yaml.safe_load(longhorn_storage_class.
                       metadata.
                       annotations["longhorn.io/last-applied-configmap"])
    storage_class_data["reclaimPolicy"] = "Retain"
    longhorn_storage_class.\
        metadata.annotations["longhorn.io/last-applied-configmap"] =\
        yaml.dump(storage_class_data)

    storage_api.patch_storage_class("longhorn", longhorn_storage_class)

    # step 3
    for i in range(RETRY_COMMAND_COUNT):
        try:
            longhorn_storage_class = storage_api.read_storage_class("longhorn")
            storage_class_data = \
                yaml.safe_load(longhorn_storage_class.
                               metadata.
                               annotations["longhorn.io/last-applied-configmap"]) # NOQA
            if storage_class_data["reclaimPolicy"] == \
                    config_map_data["reclaimPolicy"]:
                break
        except Exception as e:
            print(e)
        finally:
            time.sleep(RETRY_INTERVAL)

    assert storage_class_data["reclaimPolicy"] == \
        config_map_data["reclaimPolicy"]

    # step 4
    for i in range(RETRY_COMMAND_COUNT):
        try:
            storage_api.delete_storage_class("longhorn")
            for item in storage_api.list_storage_class().items:
                assert item.metadata.name != "longhorn"
            break
        except Exception as e:
            print(e)
        finally:
            time.sleep(RETRY_INTERVAL)

    # step 5
    storage_class_recreated = False
    for i in range(RETRY_COMMAND_COUNT):
        for item in storage_api.list_storage_class().items:
            if item.metadata.name == "longhorn":
                storage_class_recreated = True
                break
        time.sleep(RETRY_INTERVAL)
    assert storage_class_recreated is True

    # step 6, 7
    edit_configmap_allow_vol_exp(False)

    # step 8 in finalizer


@pytest.mark.coretest   # NOQA
def test_snapshot_prune(client, volume_name, backing_image=""):  # NOQA
    """
    Test removing the snapshot directly behinds the volume head would trigger
    snapshot prune. Snapshot pruning means removing the overlapping part from
    the snapshot based on the volume head content.


    1.  Create a volume and attach to the node
    2.  Generate and write data `snap1_data`, then create `snap1`
    3.  Generate and write data `snap2_data` with the same offset.
    4.  Mark `snap1` as removed.
        Make sure volume's data didn't change.
        But all data of the `snap1` will be pruned.
    5.  Detach and expand the volume, then wait for the expansion done.
        This will implicitly create a new snapshot `snap2`.
    6.  Attach the volume.
        Make sure there is a system snapshot with the old size.
    7.  Generate and write data `snap3_data` which is partially overlapped with
       `snap2_data`, plus one extra data chunk in the expanded part.
    8.  Mark `snap2` as removed then do snapshot purge.
        Make sure volume's data didn't change.
        But the overlapping part of `snap2` will be pruned.
    9.  Create `snap3`.
    10. Do snapshot purge for the volume. Make sure `snap2` will be removed.
    11. Generate and write data `snap4_data` which has no overlapping with
        `snap3_data`.
    12. Mark `snap3` as removed.
        Make sure volume's data didn't change.
        But there is no change for `snap3`.
    13. Create `snap4`.
    14. Generate and write data `snap5_data`, then create `snap5`.
    15. Detach and reattach the volume in maintenance mode.
    16. Make sure the volume frontend is still `blockdev` but disabled
    17. Revert to `snap4`
    18. Detach and reattach the volume with frontend enabled
    19. Make sure volume's data is correct.
    20. List snapshot. Make sure `volume-head` is now `snap4`'s child
    """
    snapshot_prune_test(client, volume_name, backing_image)


def snapshot_prune_test(client, volume_name, backing_image):  # NOQA
    # For this test, the fiemap size should not greater than 1Mi
    fiemap_max_size = 4 * Ki
    snap_data_size_in_mb = 4
    volume = create_and_check_volume(client, volume_name,
                                     backing_image=backing_image)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)
    volume_endpoint = get_volume_endpoint(volume)

    # Prepare and write snap1_data
    snap1_offset = 1
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap1_offset, snap_data_size_in_mb)
    snap1_before = create_snapshot(client, volume_name)

    # Prepare and write snap2_data,
    # which would completely overwrite snap1 content.
    snap2_offset = 1
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap2_offset, snap_data_size_in_mb)
    cksum_before = get_device_checksum(volume_endpoint)

    # All data in snap1 should be pruned.
    volume.snapshotDelete(name=snap1_before.name)
    volume.snapshotPurge()
    volume = wait_for_snapshot_purge(client, volume_name, snap1_before.name)
    snap1_after = volume.snapshotGet(name=snap1_before.name)
    volume_head1 = volume.snapshotGet(name=VOLUME_HEAD_NAME)
    snap1_after_size = int(snap1_after.size)
    cksum_after = get_device_checksum(volume_endpoint)
    assert snap1_after.removed
    assert snap1_after_size == 0
    assert cksum_before == cksum_after

    # Expansion will implicitly created a system snapshot `snap2`
    offline_expand_attached_volume(client, volume_name)
    volume = client.by_id_volume(volume_name)
    for snap in volume.snapshotList(volume=volume_name):
        # In the future, there may be an automatic purge operation
        # after expansion
        if snap.name == snap1_before.name:
            assert snap.name == snap1_before.name
            assert snap.removed
            assert VOLUME_HEAD_NAME not in snap.children.keys()
            continue
        if snap.name != VOLUME_HEAD_NAME:
            snap2_before = snap
            assert not snap.usercreated
            assert snap.size == volume_head1.size
            assert snap.parent == snap1_before.name
            assert VOLUME_HEAD_NAME in snap.children.keys()
            continue
    assert snap2_before
    snap2_before_size = int(snap2_before.size)

    # Prepare and write snap3_data,
    # which would partially overwrite snap2 content, plus one extra data chunk
    # in the expanded part.
    snap3_offset1 = random.randrange(snap2_offset,
                                     snap2_offset + snap_data_size_in_mb, 1)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap3_offset1, snap_data_size_in_mb)
    snap3_offset2 = random.randrange(
        int(SIZE)/Mi + snap_data_size_in_mb,
        int(EXPAND_SIZE)/Mi - snap_data_size_in_mb, 1)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap3_offset2, snap_data_size_in_mb)
    cksum_before = get_device_checksum(volume_endpoint)

    # Pruning snap2 as well as coalescing snap1 with snap2
    volume.snapshotDelete(name=snap2_before.name)
    volume.snapshotPurge()
    volume = wait_for_snapshot_purge(client, volume_name, snap2_before.name)
    snap2_after = volume.snapshotGet(name=snap2_before.name)
    snap2_after_size = int(snap2_after.size)
    cksum_after = get_device_checksum(volume_endpoint)
    assert snap2_after.removed
    assert snap2_before_size >= snap2_after_size - snap1_after_size - \
           fiemap_max_size + \
           (snap2_offset + snap_data_size_in_mb - snap3_offset1) * Mi

    assert cksum_before == cksum_after

    snap3_before = create_snapshot(client, volume_name)
    snap3_before_size = int(snap3_before.size)

    # Prepare and write snap4_data which has no overlapping part with snap3.
    snap4_offset = random.randrange(snap3_offset1 + snap_data_size_in_mb,
                                    int(SIZE)/Mi + snap_data_size_in_mb, 1)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap4_offset, snap_data_size_in_mb)
    cksum_before = get_device_checksum(volume_endpoint)
    # Pruning snap3 then coalescing snap2 with snap3
    volume.snapshotDelete(name=snap3_before.name)
    volume.snapshotPurge()
    volume = wait_for_snapshot_purge(client, volume_name, snap3_before.name)
    snap3_after = volume.snapshotGet(name=snap3_before.name)
    snap3_after_size = int(snap3_after.size)
    cksum_after = get_device_checksum(volume_endpoint)
    assert snap3_after.removed
    assert snap3_before_size >= snap3_after_size - snap2_after_size - \
           fiemap_max_size
    assert cksum_before == cksum_after

    snap4 = create_snapshot(client, volume_name)

    # We don't care the exact content of snap5
    snap5_offset = random.randrange(
        0, int(EXPAND_SIZE)/Mi - snap_data_size_in_mb, 1)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap5_offset, snap_data_size_in_mb)
    create_snapshot(client, volume_name)

    # Prepare to do revert
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=lht_hostId, disableFrontend=True)
    volume = common.wait_for_volume_healthy_no_frontend(client, volume_name)
    assert volume.disableFrontend is True
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV
    check_volume_endpoint(volume)
    # Reverting to a removed snapshot should fail
    with pytest.raises(Exception):
        volume.snapshotRevert(name=snap3_after.name)
    # Reverting to snap4 should succeed
    volume.snapshotRevert(name=snap4.name)
    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume.disableFrontend is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    cksum_revert = get_device_checksum(volume_endpoint)
    assert cksum_before == cksum_revert

    cleanup_volume(client, volume)


@pytest.mark.coretest   # NOQA
def test_snapshot_prune_and_coalesce_simultaneously(client, volume_name, backing_image=""):  # NOQA
    """
    Test the prune for the snapshot directly behinds the volume head would be
    handled after all snapshot coalescing done.


    1. Create a volume and attach to the node
    2. Generate and write 1st data chunk `snap1_data`, then create `snap1`
    3. Generate and write 2nd data chunk `snap2_data`, then create `snap2`
    4. Generate and write 3rd data chunk `snap3_data`, then create `snap3`
    5. Generate and write 4th data chunk `snap4_data`, then create `snap4`
    6. Overwrite all existing data chunks in the volume head.
    7. Mark all snapshots as `Removed`,
       then start snapshot purge and wait for complete.
    8. List snapshot.
       Make sure there are only 2 snapshots left: `volume-head` and `snap4`.
       And `snap4` is an empty snapshot.
    9. Make sure volume's data is correct.
    """
    snapshot_prune_and_coalesce_simultaneously(
        client, volume_name, backing_image)


def snapshot_prune_and_coalesce_simultaneously(client, volume_name, backing_image):  # NOQA
    snap_data_size_in_mb = 2
    volume = create_and_check_volume(client, volume_name,
                                     backing_image=backing_image)

    lht_hostId = get_self_host_id()
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)
    volume_endpoint = get_volume_endpoint(volume)

    # Take snapshots4 without overlapping
    write_volume_dev_random_mb_data(
        volume_endpoint, 0*snap_data_size_in_mb, snap_data_size_in_mb)
    snap1 = create_snapshot(client, volume_name)

    write_volume_dev_random_mb_data(
        volume_endpoint, 1*snap_data_size_in_mb, snap_data_size_in_mb)
    snap2 = create_snapshot(client, volume_name)

    write_volume_dev_random_mb_data(
        volume_endpoint, 2*snap_data_size_in_mb, snap_data_size_in_mb)
    snap3 = create_snapshot(client, volume_name)

    write_volume_dev_random_mb_data(
        volume_endpoint, 3*snap_data_size_in_mb, snap_data_size_in_mb)
    snap4 = create_snapshot(client, volume_name)

    # Overwrite the existing data in the volume head
    write_volume_dev_random_mb_data(
        volume_endpoint, 0*snap_data_size_in_mb, 4*snap_data_size_in_mb)
    cksum_before = get_device_checksum(volume_endpoint)
    volume_head_before = volume.snapshotGet(name=VOLUME_HEAD_NAME)

    # Simultaneous snapshot coalescing & pruning
    volume.snapshotDelete(name=snap1.name)
    volume.snapshotDelete(name=snap2.name)
    volume.snapshotDelete(name=snap3.name)
    volume.snapshotDelete(name=snap4.name)
    volume.snapshotPurge()
    wait_for_snapshot_purge(client, volume_name, snap1.name)
    wait_for_snapshot_purge(client, volume_name, snap2.name)
    wait_for_snapshot_purge(client, volume_name, snap3.name)
    wait_for_snapshot_purge(client, volume_name, snap4.name)

    # List and validate snap info
    volume = client.by_id_volume(volume_name)
    snaps = volume.snapshotList(volume=volume_name)
    assert len(snaps) == 2
    for snap in snaps:
        if snap.name == VOLUME_HEAD_NAME:
            assert snap.size == volume_head_before.size
            assert snap.parent == snap4.name
        else:
            assert snap.name == snap4.name
            assert int(snap.size) == 0
            assert snap.parent == ""
            assert VOLUME_HEAD_NAME in snap.children.keys()
            continue

    # Verify the data
    cksum_after = get_device_checksum(volume_endpoint)
    assert cksum_after == cksum_before


def prepare_space_usage_for_rebuilding_only_volume(client): # NOQA
    """
    1. Create a 7Gi volume and attach to the node.
    2. Make a filesystem then mount this volume.
    3. Make this volume as a disk of the node, and disable the scheduling for
       the default disk.
    """
    disk_volname = "vol-disk"
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    extra_disk_path = create_host_disk(client, disk_volname,
                                       str(7 * Gi), lht_hostId)

    extra_disk = {"path": extra_disk_path, "allowScheduling": True}
    update_disks = get_update_disks(node.disks)
    update_disks["extra-disk"] = extra_disk
    node = update_node_disks(client, node.name, disks=update_disks,
                             retry=True)
    node = common.wait_for_disk_update(client, lht_hostId,
                                       len(update_disks))

    for fsid, disk in iter(node.disks.items()):
        if disk.path != extra_disk_path:
            disk.allowScheduling = False
            update_disks = get_update_disks(node.disks)
            update_node_disks(client, node.name, disks=update_disks,
                              retry=True)
            node = wait_for_disk_status(client, node.name,
                                        fsid,
                                        "allowScheduling", False)

            break


def test_space_usage_for_rebuilding_only_volume(client, volume_name, request):  # NOQA
    """
    Test case: the normal scenario
    1. Prepare a 7Gi volume as a node disk.
    2. Create a new volume with 3Gi spec size.
    3. Write 3Gi data (using `dd`) to the volume.
    4. Take a snapshot then mark this snapshot as Removed.
       (this snapshot won't be deleted immediately.)
    5. Write 3Gi data (using `dd`) to the volume again.
    6. Delete a random replica to trigger the rebuilding.
    7. Wait for the rebuilding complete. And verify the volume actual size
       won't be greater than 2x of the volume spec size.
    8. Delete the volume.
    """
    prepare_space_usage_for_rebuilding_only_volume(client)

    lht_hostId = get_self_host_id()
    volume = create_and_check_volume(client, volume_name, size=str(3 * Gi))
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    snap_offset = 1
    volume_endpoint = get_volume_endpoint(volume)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap_offset, 3000, 5)

    snap2 = create_snapshot(client, volume_name)
    volume.snapshotDelete(name=snap2.name)
    volume.snapshotPurge()
    wait_for_snapshot_purge(client, volume_name, snap2.name)

    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap_offset, 3000, 5)

    for r in volume.replicas:
        if r.hostId != lht_hostId:
            volume.replicaRemove(name=r.name)
            break

    wait_for_volume_degraded(client, volume_name)
    wait_for_rebuild_start(client, volume_name)
    wait_for_rebuild_complete(client, volume_name, RETRY_BACKUP_COUNTS)
    volume = client.by_id_volume(volume_name)

    actual_size = int(volume.controllers[0].actualSize)
    spec_size = int(volume.size)

    assert actual_size/spec_size <= 2


def test_space_usage_for_rebuilding_only_volume_worst_scenario(client, volume_name, request):  # NOQA
    """
    Test case: worst scenario
    1. Prepare a 7Gi volume as a node disk.
    2. Create a new volume with 2Gi spec size.
    3. Write 2Gi data (using `dd`) to the volume.
    4. Take a snapshot then mark this snapshot as Removed.
       (this snapshot won't be deleted immediately.)
    5. Write 2Gi data (using `dd`) to the volume again.
    6. Delete a random replica to trigger the rebuilding.
    7. Write 2Gi data once the rebuilding is trigger (new replica is created).
    8. Wait for the rebuilding complete. And verify the volume actual size
       won't be greater than 3x of the volume spec size.
    9. Delete the volume.
    """
    prepare_space_usage_for_rebuilding_only_volume(client)

    lht_hostId = get_self_host_id()
    volume = create_and_check_volume(client, volume_name, size=str(2 * Gi))
    volume.attach(hostId=lht_hostId)
    volume = common.wait_for_volume_healthy(client, volume_name)

    snap_offset = 1
    volume_endpoint = get_volume_endpoint(volume)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap_offset, 2000)
    snap1 = create_snapshot(client, volume_name)
    volume.snapshotDelete(name=snap1.name)
    volume.snapshotPurge()
    wait_for_snapshot_purge(client, volume_name, snap1.name)

    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap_offset, 2000)

    for r in volume.replicas:
        if r.hostId != lht_hostId:
            volume.replicaRemove(name=r.name)
            break

    wait_for_volume_degraded(client, volume_name)
    wait_for_rebuild_start(client, volume_name)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap_offset, 2000)

    wait_for_rebuild_complete(client, volume_name)
    volume = client.by_id_volume(volume_name)

    actual_size = int(volume.controllers[0].actualSize)
    spec_size = int(volume.size)
    assert actual_size/spec_size <= 3


def backup_failed_cleanup(client, core_api, volume_name, volume_size,  # NOQA
                          failed_backup_ttl="3"):  # NOQA
    """
    Setup the failed backup cleanup
    """
    bt_poll_interval = "60"

    # set backupstore poll interval to 60 sec
    set_backupstore_poll_interval(client, bt_poll_interval)

    # set failed backup time to live, default: 3 min, disabled: 0
    failed_backup_ttl_setting = client.by_id_setting(SETTING_FAILED_BACKUP_TTL)
    new_failed_backup_ttl_setting = client.update(
        failed_backup_ttl_setting, value=failed_backup_ttl)
    assert new_failed_backup_ttl_setting.value == failed_backup_ttl

    backupstore_cleanup(client)

    # create a volume
    vol = create_and_check_volume(client, volume_name,
                                  num_of_replicas=2, size=str(volume_size))

    # attach the volume
    vol.attach(hostId=get_self_host_id())
    vol = wait_for_volume_healthy(client, volume_name)

    # create a snapshot and
    # a successful backup to make sure the backup volume created
    snap = create_snapshot(client, volume_name)
    vol.snapshotBackup(name=snap.name)

    # write some data to the volume
    volume_endpoint = get_volume_endpoint(vol)

    # Take snapshots4 without overlapping
    data_size = volume_size/Mi
    write_volume_dev_random_mb_data(
        volume_endpoint, 0, data_size)

    # create a snapshot and a backup
    snap = create_snapshot(client, volume_name)
    vol.snapshotBackup(name=snap.name)

    # check backup status is in an InProgress state
    _, backup = find_backup(client, volume_name, snap.name)
    backup_id = backup.id
    backup_name = backup.name

    def backup_inprogress_predicate(b):
        return b.id == backup_id and "InProgress" in b.state
    common.wait_for_backup_state(client, volume_name,
                                 backup_inprogress_predicate)

    # crash all replicas of the volume
    try:
        crash_replica_processes(client, core_api, volume_name)
    except AssertionError:
        crash_replica_processes(client, core_api, volume_name)

    # backup status should be in an Error state and with an error message
    def backup_failure_predicate(b):
        return b.id == backup_id and "Error" in b.state and b.error != ""
    common.wait_for_backup_state(client, volume_name,
                                 backup_failure_predicate)

    return backup_name


@pytest.mark.coretest  # NOQA
def test_backup_failed_enable_auto_cleanup(set_random_backupstore,  # NOQA
                                        client, core_api, volume_name):  # NOQA
    """
    Test the failed backup would be automatically deleted.

    1.   Set the default setting `backupstore-poll-interval` to 60 (seconds)
    2.   Set the default setting `failed-backup-ttl` to 3 (minutes)
    3.   Create a volume and attach to the current node
    4.   Create a empty backup for creating the backup volume
    5.   Write some data to the volume
    6.   Create a backup of the volume
    7.   Crash all replicas
    8.   Wait and check if the backup failed
    9.   Wait and check if the backup was deleted automatically
    10.  Cleanup
    """
    backup_name = backup_failed_cleanup(client, core_api, volume_name, 1024*Mi)

    # wait in 5 minutes for automatic failed backup cleanup
    wait_for_backup_delete(client, volume_name, backup_name)


@pytest.mark.coretest  # NOQA
def test_backup_failed_disable_auto_cleanup(set_random_backupstore,  # NOQA
                                        client, core_api, volume_name):  # NOQA
    """
    Test the failed backup would be automatically deleted.

    1.    Set the default setting `backupstore-poll-interval` to 60 (seconds)
    2.    Set the default setting `failed-backup-ttl` to 0
    3.    Create a volume and attach to the current node
    4.    Create a empty backup for creating the backup volume
    5.    Write some data to the volume
    6.    Create a backup of the volume
    7.    Crash all replicas
    8.    Wait and check if the backup failed
    9.    Wait and check if the backup was not deleted.
    10.   Cleanup
    """
    backup_name = backup_failed_cleanup(client, core_api, volume_name, 1024*Mi,
                                        failed_backup_ttl="0")

    # wait for 5 minutes to check if the failed backup exists
    try:
        wait_for_backup_delete(client, volume_name, backup_name)
        assert False, "backup " + backup_name + " for volume " \
                      + volume_name + " is deleted"
    except AssertionError:
        pass


@pytest.mark.parametrize(
    "access_mode,overridden_restored_access_mode",
    [
        pytest.param("rwx", "rwo"),
        pytest.param("rwo", "rwx")
    ],
)
def test_backup_volume_restore_with_access_mode(core_api, # NOQA
                                                set_random_backupstore, # NOQA
                                                client, # NOQA
                                                access_mode, # NOQA
                                       overridden_restored_access_mode): # NOQA
    """
    Test the backup w/ the volume access mode, then restore a volume w/ the
     original access mode or being overridden.

    1. Prepare a healthy volume
    2. Create a backup for the volume
    3. Restore a volume from the backup w/o specifying the access mode
       => Validate the access mode should be the same the volume
    4. Restore a volume from the backup w/ specifying the access mode
       => Validate the access mode should be the same as the specified
    """
    # Step 1
    test_volume_name = generate_volume_name()
    client.create_volume(name=test_volume_name,
                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                         numberOfReplicas=2,
                         accessMode=access_mode,
                         migratable=True if access_mode == "rwx" else False)
    wait_for_volume_creation(client, test_volume_name)
    volume = wait_for_volume_detached(client, test_volume_name)
    volume.attach(hostId=common.get_self_host_id())
    volume = common.wait_for_volume_healthy(client, test_volume_name)

    # Step 2
    _, b, _, _ = create_backup(client, test_volume_name)

    # Step 3
    volume_name_ori_access_mode = test_volume_name + '-default-access'
    client.create_volume(name=volume_name_ori_access_mode,
                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                         numberOfReplicas=2,
                         fromBackup=b.url)
    volume_ori_access_mode = client.by_id_volume(volume_name_ori_access_mode)
    assert volume_ori_access_mode.accessMode == access_mode

    # Step 4
    volume_name_sp_access_mode = test_volume_name + '-specified-access'
    client.create_volume(name=volume_name_sp_access_mode,
                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                         numberOfReplicas=2,
                         accessMode=overridden_restored_access_mode,
                         fromBackup=b.url)
    volume_sp_access_mode = client.by_id_volume(volume_name_sp_access_mode)
    assert volume_sp_access_mode.accessMode == overridden_restored_access_mode


def test_delete_backup_during_restoring_volume(set_random_backupstore, client):  # NOQA
    """
    Test delete backup during restoring volume

    Context:

    The volume robustness should be faulted if the backup was deleted during
    restoring the volume.

    1. Given create volume v1 and attach to a node
       And write data 150M to volume v1
    2. When create a backup of volume v1
       And wait for that backup is completed
       And restore a volume v2 from volume v1 backup
       And delete the backup immediately
    3. Then volume v2 "robustness" should be "faulted"
       And "status" of volume restore condition should be "False",
       And "reason" of volume restore condition should be "RestoreFailure"
    """
    # Step 1
    vol_v1_name = "vol-v1"
    vol_v1 = create_and_check_volume(client, vol_v1_name, size=str(512 * Mi))
    vol_v1.attach(hostId=get_self_host_id())
    vol_v1 = wait_for_volume_healthy(client, vol_v1_name)

    vol_v1_endpoint = get_volume_endpoint(vol_v1)
    write_volume_dev_random_mb_data(vol_v1_endpoint, 1, 150)

    # Step 2
    bv, b, snap2, data = create_backup(client, vol_v1_name)

    vol_v2_name = "vol-v2"
    client.create_volume(name=vol_v2_name,
                         size=str(512 * Mi),
                         numberOfReplicas=3,
                         fromBackup=b.url)

    delete_backup(client, bv.name, b.name)
    volume = wait_for_volume_status(client, vol_v1_name,
                                    "lastBackup", "")
    assert volume.lastBackupAt == ""

    # Step 3
    wait_for_volume_faulted(client, vol_v2_name)
    wait_for_volume_condition_restore(client, vol_v2_name,
                                      "status", "False")
    wait_for_volume_condition_restore(client, vol_v2_name,
                                      "reason", "RestoreFailure")


@pytest.mark.parametrize("fs_type", [FS_TYPE_EXT4, FS_TYPE_XFS])  # NOQA
def test_filesystem_trim(client, fs_type):  # NOQA
    """
    Test the filesystem in the volume can be trimmed correctly.

    1.    Create a volume with option `unmapMarkSnapChainRemoved` enabled,
          then attach to the current node.
    2.    Make a filesystem and write file0 into the fs, calculate the
          checksum, then take snap0.
    3.    Write file21 and calculate the checksum. Then take snap21.
    4.    Unmount then reattach the volume without frontend. Revert the volume
          to snap0.
    5.    Reattach and mount the volume.
    6.    Write file11. Then take snap11.
    7.    Write file12. Then take snap12.
    8.    Write file13. Then remove file0, file11, file12, and file13.
          Verify the snapshots and volume head size are not shrunk.
    9.    Do filesystem trim (via Longhorn API or cmdline).
          Verify that:
          1. snap11 and snap12 are marked as removed.
          2. snap11, snap12, and volume head size are shrunk.
    10.   Disable option `unmapMarkSnapChainRemoved` for the volume.
    11.   Write file14. Then take snap14.
    12.   Write file15. Then remove file14 and file15.
          Verify that:
          1. snap14 is not marked as removed and its size is not changed.
          2. volume head size is shrunk.
    13.   Unmount and reattach the volume. Then revert to snap21.
    14.   Reattach and mount the volume. Verify the file0 and file21.
    15.   Cleanup.
    """
    test_volume_name = generate_volume_name()
    client.create_volume(name=test_volume_name,
                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                         numberOfReplicas=2,
                         unmapMarkSnapChainRemoved="enabled")
    wait_for_volume_creation(client, test_volume_name)
    volume = wait_for_volume_detached(client, test_volume_name)

    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    common.wait_for_volume_healthy(client, test_volume_name)

    dev_path = os.path.join("/dev/longhorn", test_volume_name)
    mnt_path = os.path.join("/tmp", "mnt-"+test_volume_name)

    mount_cmd = ["mount", dev_path, mnt_path]
    umount_cmd = ["umount", mnt_path]
    findmnt_cmd = ["findmnt", dev_path]
    trim_cmd = ["fstrim", mnt_path]
    if fs_type == FS_TYPE_EXT4:
        subprocess.check_call(["mkfs.ext4", dev_path])
    elif fs_type == FS_TYPE_XFS:
        subprocess.check_call(["mkfs.xfs", dev_path])
    else:
        raise Exception("unexpected filesystem type")
    subprocess.check_call(["mkdir", "-p", mnt_path])
    subprocess.check_call(mount_cmd)
    subprocess.check_call(findmnt_cmd)
    subprocess.check_call(["sync"])

    volume = client.by_id_volume(test_volume_name)

    file0_path = os.path.join(mnt_path, "file0")
    write_volume_dev_random_mb_data(file0_path, 0, 100)
    subprocess.check_call(["sync"])
    file0_cksum_origin = get_volume_dev_mb_data_md5sum(file0_path, 0, 100)
    snap0_origin = create_snapshot(client, test_volume_name)

    file21_path = os.path.join(mnt_path, "file21")
    write_volume_dev_random_mb_data(file21_path, 0, 100)
    subprocess.check_call(["sync"])
    file21_cksum_origin = get_volume_dev_mb_data_md5sum(file21_path, 0, 100)
    snap21_origin = create_snapshot(client, test_volume_name)

    subprocess.check_call(umount_cmd)
    volume.detach()
    volume = wait_for_volume_detached(client, test_volume_name)
    volume.attach(hostId=host_id, disableFrontend=True)
    volume = common.wait_for_volume_healthy_no_frontend(
        client, test_volume_name)
    volume.snapshotRevert(name=snap0_origin.name)

    volume.detach()
    volume = wait_for_volume_detached(client, test_volume_name)
    volume.attach(hostId=host_id)
    common.wait_for_volume_healthy(client, test_volume_name)
    volume = wait_for_volume_option_trim_auto_removing_snapshots(
        client, test_volume_name, True)
    subprocess.check_call(mount_cmd)
    subprocess.check_call(findmnt_cmd)
    subprocess.check_call(["sync"])

    file11_path = os.path.join(mnt_path, "file11")
    write_volume_dev_random_mb_data(file11_path, 0, 100)
    subprocess.check_call(["sync"])
    snap11_origin = create_snapshot(client, test_volume_name)

    file12_path = os.path.join(mnt_path, "file12")
    write_volume_dev_random_mb_data(file12_path, 0, 100)
    subprocess.check_call(["sync"])
    snap12_origin = create_snapshot(client, test_volume_name)

    file13_path = os.path.join(mnt_path, "file13")
    write_volume_dev_random_mb_data(file13_path, 0, 100)
    subprocess.check_call(["sync"])

    # Step 8.
    # Remove files. Then verify the snapshots before the filesystem trim.
    subprocess.check_call(["rm",
                           file0_path, file11_path, file12_path, file13_path])
    subprocess.check_call(["sync"])

    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap0_origin.name].name == snap0_origin.name
    assert snapMap[snap0_origin.name].removed is False
    assert snapMap[snap0_origin.name].size == snap0_origin.size
    assert snapMap[snap0_origin.name].parent == ""

    assert snapMap[snap21_origin.name].name == snap21_origin.name
    assert snapMap[snap21_origin.name].removed is False
    assert snapMap[snap21_origin.name].size == snap21_origin.size
    assert snapMap[snap21_origin.name].parent == snap0_origin.name

    assert snapMap[snap11_origin.name].name == snap11_origin.name
    assert snapMap[snap11_origin.name].removed is False
    assert snapMap[snap11_origin.name].size == snap11_origin.size
    assert snapMap[snap11_origin.name].parent == snap0_origin.name

    assert snapMap[snap12_origin.name].name == snap12_origin.name
    assert snapMap[snap12_origin.name].removed is False
    assert snapMap[snap12_origin.name].size == snap12_origin.size
    assert snapMap[snap12_origin.name].parent == snap11_origin.name

    assert snapMap[VOLUME_HEAD_NAME].name == VOLUME_HEAD_NAME
    assert int(snapMap[VOLUME_HEAD_NAME].size) >= 100 * Mi
    assert snapMap[VOLUME_HEAD_NAME].parent == snap12_origin.name
    volume_head1 = snapMap[VOLUME_HEAD_NAME]

    # Sometimes the current mounting will lose track of the removed file
    #  mapping info. It's better to remount the filesystem before trim.
    subprocess.check_call(umount_cmd)
    subprocess.check_call(mount_cmd)
    subprocess.check_call(findmnt_cmd)
    # Step 9. Verify the snapshots after the filesystem trim.
    subprocess.check_call(trim_cmd)

    volume = client.by_id_volume(test_volume_name)
    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap0_origin.name].name == snap0_origin.name
    assert snapMap[snap0_origin.name].removed is False
    assert snapMap[snap0_origin.name].size == snap0_origin.size
    assert snapMap[snap0_origin.name].parent == ""

    assert snapMap[snap21_origin.name].name == snap21_origin.name
    assert snapMap[snap21_origin.name].removed is False
    assert snapMap[snap21_origin.name].size == snap21_origin.size
    assert snapMap[snap21_origin.name].parent == snap0_origin.name

    assert snapMap[snap11_origin.name].name == snap11_origin.name
    assert snapMap[snap11_origin.name].removed is True
    assert int(snapMap[snap11_origin.name].size) <= \
           int(snap11_origin.size) - 100 * Mi
    assert snapMap[snap11_origin.name].parent == snap0_origin.name

    assert snapMap[snap12_origin.name].name == snap12_origin.name
    assert snapMap[snap12_origin.name].removed is True
    assert int(snapMap[snap12_origin.name].size) <= \
           int(snap12_origin.size) - 100 * Mi
    assert snapMap[snap12_origin.name].parent == snap11_origin.name

    # Volume head may record some extra meta info after the file removal.
    # Hence the size it reduced may be smaller than 100Mi
    assert snapMap[VOLUME_HEAD_NAME].name == VOLUME_HEAD_NAME
    assert int(snapMap[VOLUME_HEAD_NAME].size) <= \
           int(volume_head1.size) - 50 * Mi
    assert snapMap[VOLUME_HEAD_NAME].parent == snap12_origin.name

    volume = client.by_id_volume(test_volume_name)
    volume.updateUnmapMarkSnapChainRemoved(
        unmapMarkSnapChainRemoved="disabled")
    wait_for_volume_option_trim_auto_removing_snapshots(
        client, test_volume_name, False)

    file14_path = os.path.join(mnt_path, "file14")
    write_volume_dev_random_mb_data(file14_path, 0, 100)
    subprocess.check_call(["sync"])
    snap14_origin = create_snapshot(client, test_volume_name)

    file15_path = os.path.join(mnt_path, "file15")
    write_volume_dev_random_mb_data(file15_path, 0, 100)
    subprocess.check_call(["sync"])

    subprocess.check_call(["rm",
                           file14_path, file15_path])
    subprocess.check_call(["sync"])

    volume = client.by_id_volume(test_volume_name)
    snapshots = volume.snapshotList()
    snap_map = {}
    for snap in snapshots:
        snap_map[snap.name] = snap

    assert snap_map[snap14_origin.name].name == snap14_origin.name
    assert snap_map[snap14_origin.name].removed is False
    assert snap_map[snap14_origin.name].size == snap14_origin.size
    assert snap_map[snap14_origin.name].parent == snap12_origin.name

    assert snap_map[VOLUME_HEAD_NAME].name == VOLUME_HEAD_NAME
    assert int(snap_map[VOLUME_HEAD_NAME].size) >= 100 * Mi
    assert snap_map[VOLUME_HEAD_NAME].parent == snap14_origin.name
    volume_head2 = snap_map[VOLUME_HEAD_NAME]

    # Sometimes the current mounting will lose track of the removed file
    #  mapping info. It's better to remount the filesystem before trim.
    subprocess.check_call(umount_cmd)
    subprocess.check_call(mount_cmd)
    subprocess.check_call(findmnt_cmd)
    # Step 12. Verify the snapshots after the filesystem trim.
    subprocess.check_call(trim_cmd)

    volume = client.by_id_volume(test_volume_name)
    snapshots = volume.snapshotList()
    snap_map = {}
    for snap in snapshots:
        snap_map[snap.name] = snap

    assert snap_map[snap14_origin.name].name == snap14_origin.name
    assert snap_map[snap14_origin.name].removed is False
    assert int(snap_map[snap14_origin.name].size) <= \
           int(snap14_origin.size) - 100 * Mi
    assert snap_map[snap14_origin.name].parent == snap12_origin.name

    # Volume head may record some extra meta info after the file removal.
    # Hence the size it reduced may be smaller than 100Mi
    assert snap_map[VOLUME_HEAD_NAME].name == VOLUME_HEAD_NAME
    assert int(snap_map[VOLUME_HEAD_NAME].size) <= \
           int(volume_head2.size) - 50 * Mi
    assert snap_map[VOLUME_HEAD_NAME].parent == snap14_origin.name

    subprocess.check_call(umount_cmd)
    volume.detach()
    volume = wait_for_volume_detached(client, test_volume_name)
    volume.attach(hostId=host_id, disableFrontend=True)
    volume = common.wait_for_volume_healthy_no_frontend(
        client, test_volume_name)
    volume.snapshotRevert(name=snap21_origin.name)

    volume.detach()
    volume = wait_for_volume_detached(client, test_volume_name)
    volume.attach(hostId=host_id)
    common.wait_for_volume_healthy(client, test_volume_name)
    subprocess.check_call(mount_cmd)
    subprocess.check_call(findmnt_cmd)
    subprocess.check_call(["sync"])

    file0_cksum = get_volume_dev_mb_data_md5sum(file0_path, 0, 100)
    assert file0_cksum_origin == file0_cksum
    file21_cksum = get_volume_dev_mb_data_md5sum(file21_path, 0, 100)
    assert file21_cksum_origin == file21_cksum

    subprocess.check_call(umount_cmd)
    subprocess.check_call(["rm", "-rf", mnt_path])

    client.delete(volume)
    wait_for_volume_delete(client, test_volume_name)


@pytest.mark.skip(reason="TODO")
def test_backuptarget_invalid(): # NOQA
    """
    Related issue :
    https://github.com/longhorn/longhorn/issues/1249

    This test case does not cover the UI test mentioned in the related issue's
    test steps."

    Setup
    - Give an incorrect value to Backup target.

    Given
    - Create a volume, attach it to a workload, write data into the volume.

    When
    - Create a backup by a manifest yaml file

    Then
    - Backup will be failed and the backup state is Error.
    """
    pass


@pytest.mark.volume_backup_restore   # NOQA
def test_volume_backup_and_restore_with_lz4_compression_method(client, set_random_backupstore, volume_name):  # NOQA
    """
    Scenario: test volume backup and restore with different compression methods

    Issue: https://github.com/longhorn/longhorn/issues/5189

    Given setup Backup Compression Method is "lz4"
    And setup backup concurrent limit is "4"
    And setup restore concurrent limit is "4"

    When create a volume and attach to the current node
    And get the volume's details
    Then verify the volume's compression method is "lz4"

    Then Create a backup of volume
    And Write volume random data
    Then restore the backup to a new volume
    And Attach the new volume and verify the data integrity
    Then Detach the volume and delete the backup
    And Wait for the restored volume's `lastBackup` to be cleaned
    (due to remove the backup)
    And Delete the volume
    """
    common.update_setting(client, common.SETTING_BACKUP_COMPRESSION_METHOD,
                          BACKUP_COMPRESSION_METHOD_LZ4)
    common.update_setting(client, common.SETTING_BACKUP_CONCURRENT_LIMIT, "4")
    common.update_setting(client, common.SETTING_RESTORE_CONCURRENT_LIMIT, "4")
    backup_test(client, volume_name, SIZE,
                compression_method=BACKUP_COMPRESSION_METHOD_LZ4)


@pytest.mark.volume_backup_restore   # NOQA
def test_volume_backup_and_restore_with_gzip_compression_method(client, set_random_backupstore, volume_name):  # NOQA
    """
    Scenario: test volume backup and restore with different compression methods

    Issue: https://github.com/longhorn/longhorn/issues/5189

    Given setup Backup Compression Method is "gzip"
    And setup backup concurrent limit is "4"
    And setup restore concurrent limit is "4"

    When create a volume and attach to the current node
    And get the volume's details
    Then verify the volume's compression method is "gzip"

    Then Create a backup of volume
    And Write volume random data
    Then restore the backup to a new volume
    And Attach the new volume and verify the data integrity
    And Detach the volume and delete the backup
    And Wait for the restored volume's `lastBackup` to be cleaned
    (due to remove the backup)
    And Delete the volume
    """
    common.update_setting(client, common.SETTING_BACKUP_COMPRESSION_METHOD,
                          BACKUP_COMPRESSION_METHOD_GZIP)
    common.update_setting(client, common.SETTING_BACKUP_CONCURRENT_LIMIT, "4")
    common.update_setting(client, common.SETTING_RESTORE_CONCURRENT_LIMIT, "4")
    backup_test(client, volume_name, SIZE,
                compression_method=BACKUP_COMPRESSION_METHOD_GZIP)


@pytest.mark.volume_backup_restore   # NOQA
def test_volume_backup_and_restore_with_none_compression_method(client, set_random_backupstore, volume_name):  # NOQA
    """
    Scenario: test volume backup and restore with different compression methods

    Issue: https://github.com/longhorn/longhorn/issues/5189

    Given setup Backup Compression Method is "none"
    And setup backup concurrent limit is "4"
    And setup restore concurrent limit is "4"

    When create a volume and attach to the current node
    And get the volume's details
    Then verify the volume's compression method is "none"

    Then Create a backup of volume
    And Write volume random data
    Then restore the backup to a new volume
    And Attach the new volume and verify the data integrity
    And Detach the volume and delete the backup
    And Wait for the restored volume's `lastBackup` to be cleaned
    (due to remove the backup)
    And Delete the volume
    """
    common.update_setting(client, common.SETTING_BACKUP_COMPRESSION_METHOD,
                          BACKUP_COMPRESSION_METHOD_NONE)
    common.update_setting(client, common.SETTING_BACKUP_CONCURRENT_LIMIT, "4")
    common.update_setting(client, common.SETTING_RESTORE_CONCURRENT_LIMIT, "4")
    backup_test(client, volume_name, SIZE,
                compression_method=BACKUP_COMPRESSION_METHOD_NONE)
