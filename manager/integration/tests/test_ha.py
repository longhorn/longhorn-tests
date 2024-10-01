import pytest
import common
import time
import random
import subprocess
import os

from common import client, core_api, volume_name  # NOQA
from common import sts_name, statefulset, storage_class  # NOQA
from common import DATA_SIZE_IN_MB_1, DATA_SIZE_IN_MB_2, DATA_SIZE_IN_MB_3
from common import DATA_SIZE_IN_MB_4, Ki
from common import check_volume_data, cleanup_volume, create_and_check_volume
from common import delete_replica_processes, crash_replica_processes
from common import get_self_host_id, check_volume_endpoint
from common import wait_for_snapshot_purge, write_volume_random_data
from common import create_snapshot, DIRECTORY_PATH
from common import check_block_device_size
from common import generate_random_data
from common import wait_for_rebuild_complete
from common import disable_auto_salvage # NOQA
from common import pod_make, pod, csi_pv, pvc  # NOQA
from common import create_pv_for_volume, create_pvc_for_volume
from common import create_pvc_spec, create_pvc, create_and_wait_pod
from common import wait_and_get_pv_for_pvc, expand_and_wait_for_pvc
from common import create_storage_class
from common import write_pod_volume_random_data
from common import wait_for_volume_healthy, wait_for_volume_degraded
from common import get_pod_data_md5sum
from common import wait_for_pod_remount, delete_and_wait_pod
from common import wait_for_rebuild_start, get_update_disks
from common import prepare_pod_with_data_in_mb
from common import wait_for_backup_completion, find_backup
from common import wait_for_volume_creation, wait_for_volume_detached
from common import wait_for_volume_restoration_start
from common import wait_for_backup_restore_completed
from common import wait_for_volume_restoration_completed
from common import check_volume_last_backup
from common import activate_standby_volume
from common import create_backup, get_backupstores
from common import wait_for_volume_faulted
from common import wait_for_volume_delete
from common import SETTING_AUTO_SALVAGE
from common import SETTING_BACKUP_TARGET
from common import wait_for_volume_condition_restore
from common import crash_engine_process_with_sigkill
from common import wait_for_volume_healthy_no_frontend
from common import exec_instance_manager
from common import SIZE, VOLUME_RWTEST_SIZE, Gi
from common import RETRY_COUNTS, RETRY_INTERVAL, RETRY_INTERVAL_LONG
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL
from common import write_pod_volume_data
from common import read_volume_data
from common import VOLUME_FIELD_ROBUSTNESS, VOLUME_ROBUSTNESS_DEGRADED
from common import VOLUME_ROBUSTNESS_HEALTHY
from common import wait_for_volume_expansion, wait_for_dr_volume_expansion
from common import wait_for_volume_replica_count, wait_for_replica_failed
from common import settings_reset # NOQA
from common import set_node_tags, set_node_scheduling # NOQA
from common import SETTING_DISABLE_REVISION_COUNTER
from common import make_deployment_with_pvc # NOQA
from common import get_apps_api_client, create_and_wait_deployment
from common import wait_delete_pod
from common import wait_pod, exec_command_in_pod
from common import RETRY_EXEC_COUNTS, RETRY_EXEC_INTERVAL, RETRY_COUNTS_SHORT
from common import get_volume_running_replica_cnt
from common import update_node_disks
from common import LONGHORN_NAMESPACE
from common import get_volume_endpoint
from common import copy_file_to_volume_dev_mb_data
from common import write_volume_dev_random_mb_data
from common import get_volume_dev_mb_data_md5sum
from common import restart_and_wait_ready_engine_count
from common import wait_for_deployed_engine_image_count
from common import wait_for_volume_current_image
from common import wait_for_engine_image_ref_count
from common import SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT
from common import update_setting
from common import wait_for_backup_volume_backing_image_synced
from common import RETRY_COMMAND_COUNT
from common import wait_for_snapshot_count
from common import DEFAULT_BACKUP_COMPRESSION_METHOD
from common import wait_for_tainted_node_engine_image_undeployed
from common import wait_for_replica_count

from backupstore import set_random_backupstore # NOQA
from backupstore import backupstore_cleanup
from backupstore import backupstore_delete_random_backup_block
from backupstore import backupstore_wait_for_lock_expiration
from backupstore import backupstore_s3  # NOQA

from test_node import create_host_disk
from test_scheduling import get_host_replica
from test_basic import backupstore_test
from node import taint_non_current_node

SMALL_RETRY_COUNTS = 30
BACKUPSTORE = get_backupstores()

REPLICA_FAILURE_MODE_CRASH = "replica_failure_mode_crash"
REPLICA_FAILURE_MODE_DELETE = "replica_failure_mode_delete"

@pytest.mark.coretest   # NOQA
def test_ha_simple_recovery(client, volume_name):  # NOQA
    """
    [HA] Test recovering from one replica failure

    1. Create volume and attach to the current node
    2. Write `data` to the volume.
    3. Remove one of the replica using Longhorn API
    4. Wait for a new replica to be rebuilt.
    5. Check the volume data
    """
    ha_simple_recovery_test(client, volume_name, SIZE)


def ha_simple_recovery_test(client, volume_name, size, backing_image=""):  # NOQA
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=2,
                                     size=size,
                                     backing_image=backing_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    ha_rebuild_replica_test(client, volume_name)

    cleanup_volume(client, volume)


def ha_rebuild_replica_test(client, volname):   # NOQA
    volume = client.by_id_volume(volname)
    check_volume_endpoint(volume)

    assert len(volume.replicas) == 2
    replica0 = volume.replicas[0]
    assert replica0.name != ""

    replica1 = volume.replicas[1]
    assert replica1.name != ""

    data = write_volume_random_data(volume)

    volume = volume.replicaRemove(name=replica0.name)

    # wait until we saw a replica starts rebuilding
    new_replica_found = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volname)
        for r in v.replicas:
            if r.name != replica0.name and \
                    r.name != replica1.name:
                new_replica_found = True
                break
        if new_replica_found:
            break
        time.sleep(RETRY_INTERVAL)
    wait_for_rebuild_complete(client, volname)
    assert new_replica_found

    volume = wait_for_volume_healthy(client, volname)

    volume = client.by_id_volume(volname)
    assert volume.state == common.VOLUME_STATE_ATTACHED
    assert volume.robustness == common.VOLUME_ROBUSTNESS_HEALTHY
    assert len(volume.replicas) >= 2

    found = False
    for replica in volume.replicas:
        if replica.name == replica1.name:
            found = True
            break
    assert found

    check_volume_data(volume, data)


@pytest.mark.coretest   # NOQA
def test_ha_salvage(client, core_api, volume_name, disable_auto_salvage):  # NOQA
    """
    [HA] Test salvage when volume faulted
    TODO
    The test cases should cover the following four cases:
    1. Manual salvage with revision counter enabled.
    2. Manual salvage with revision counter disabled.
    3. Auto salvage with revision counter enabled.
    4. Auto salvage with revision counter enabled.

    Setting: Disable auto salvage

    Case 1: Delete all replica processes using instance manager

    1. Create volume and attach to the current node
    2. Write `data` to the volume.
    3. Crash all the replicas using Instance Manager API
        1. Cannot do it using Longhorn API since a. it will delete data, b. the
    last replica is not allowed to be deleted
    4. Make sure volume detached automatically and changed into `faulted` state
    5. Make sure both replicas reports `failedAt` timestamp.
    6. Salvage the volume
    7. Verify that volume is in `detached` `unknown` state. No longer `faulted`
    8. Verify that all the replicas' `failedAt` timestamp cleaned.
    9. Attach the volume and check `data`

    Case 2: Crash all replica processes

    Same steps as Case 1 except on step 3, use SIGTERM to crash the processes

    Setting: Enabled auto salvage.

    Case 3: Revision counter disabled.

    1. Set 'Automatic salvage' to true.
    2. Set 'Disable Revision Counter' to true.
    3. Create a volume with 3 replicas.
    4. Attach the volume to a node and write some data to it and save the
    checksum.
    5. Delete all replica processes using instance manager or
    crash all replica processes using SIGTERM.
    6. Wait for volume to `faulted`, then `healthy`.
    7. Verify all 3 replicas are reused successfully.
    8. Check the data in the volume and make sure it's the same as the
    checksum saved on step 5.

    Case 4: Revision counter enabled.

    1. Set 'Automatic salvage' to true.
    2. Set 'Disable Revision Counter' to false.
    4. Create a volume with 3 replicas.
    5. Attach the volume to a node and write some data to it and save the
    checksum.
    6. Delete all replica processes using instance manager or
    crash all replica processes using SIGTERM.
    7. Wait for volume to `faulted`, then `healthy`.
    8. Verify there are 3 replicas, they are all from previous replicas.
    9. Check the data in the volume and make sure it's the same as the
    checksum saved on step 5.

    """
    ha_salvage_test(client, core_api, volume_name)


def ha_salvage_test(client, core_api, # NOQA
                    volume_name, backing_image=""):  # NOQA

    # Setting Disable auto salvage
    # Case 1: Delete all replica processes using instance manager

    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="false")
    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "false"

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=2,
                                     backing_image=backing_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    delete_replica_processes(client, core_api, volume_name)

    volume = wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume = wait_for_volume_detached(client, volume_name)
    volume = common.wait_for_volume_faulted(client, volume_name)

    volume.salvage(names=[replica0_name, replica1_name])
    volume = client.by_id_volume(volume_name)

    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume = wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)

    # Setting Disable auto salvage
    # Case 2: Crash all replica processes
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="false")
    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "false"

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=2,
                                     backing_image=backing_image)
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    crash_replica_processes(client, core_api, volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume = common.wait_for_volume_detached(client, volume_name)
    volume = common.wait_for_volume_faulted(client, volume_name)

    volume.salvage(names=[replica0_name, replica1_name])
    volume = client.by_id_volume(volume_name)

    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume = wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)

    # Setting: Enabled auto salvage.
    # Case 3: Revision counter disabled.

    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="true")
    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "true"

    disable_revision_counter_setting = \
        client.by_id_setting(SETTING_DISABLE_REVISION_COUNTER)
    setting = client.update(disable_revision_counter_setting, value="true")
    assert setting.name == SETTING_DISABLE_REVISION_COUNTER
    assert setting.value == "true"

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3,
                                     backing_image=backing_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 3
    orig_replica_names = []
    for replica in volume.replicas:
        orig_replica_names.append(replica.name)

    data = write_volume_random_data(volume)

    crash_replica_processes(client, core_api, volume_name)
    # This is a workaround, since in some case it's hard to
    # catch faulted volume status
    common.wait_for_volume_status(client, volume_name,
                                  common.VOLUME_FIELD_STATE,
                                  'attaching')

    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    for replica in volume.replicas:
        assert replica.name in orig_replica_names

    check_volume_data(volume, data)
    cleanup_volume(client, volume)

    # Setting: Enabled auto salvage.
    # Case 4: Revision counter enabled.

    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="true")
    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "true"

    disable_revision_counter_setting = \
        client.by_id_setting("disable-revision-counter")
    setting = client.update(disable_revision_counter_setting, value="false")
    assert setting.name == "disable-revision-counter"
    assert setting.value == "false"

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3,
                                     backing_image=backing_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 3
    orig_replica_names = []
    for replica in volume.replicas:
        orig_replica_names.append(replica.name)

    data = write_volume_random_data(volume)

    crash_replica_processes(client, core_api, volume_name)
    # This is a workaround, since in some case it's hard to
    # catch faulted volume status
    common.wait_for_volume_status(client, volume_name,
                                  common.VOLUME_FIELD_STATE,
                                  'attaching')

    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""
    assert volume.replicas[2].failedAt == ""

    check_volume_data(volume, data)
    cleanup_volume(client, volume)

# https://github.com/rancher/longhorn/issues/253
def test_ha_backup_deletion_recovery(set_random_backupstore, client, volume_name):  # NOQA
    """
    [HA] Test deleting the restored snapshot and rebuild

    Backupstore: all

    1. Create volume and attach it to the current node.
    2. Write `data` to the volume and create snapshot `snap2`
    3. Backup `snap2` to create a backup.
    4. Create volume `res_volume` from the backup. Check volume `data`.
    5. Check snapshot chain, make sure `backup_snapshot` exists.
    6. Delete the `backup_snapshot` and purge snapshots.
    7. After purge complete, delete one replica to verify rebuild works.

    FIXME: Needs improvement, e.g. rebuild when no snapshot is deleted for
    restored backup.
    """
    ha_backup_deletion_recovery_test(client, volume_name, SIZE)


def ha_backup_deletion_recovery_test(client, volume_name, size, backing_image=""):  # NOQA
    client.create_volume(name=volume_name, size=size, numberOfReplicas=2,
                         backingImage=backing_image)
    volume = wait_for_volume_detached(client, volume_name)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    data = write_volume_random_data(volume)
    snap2 = create_snapshot(client, volume_name)
    create_snapshot(client, volume_name)

    volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, volume_name, snap2.name)
    if backing_image != "":
        wait_for_backup_volume_backing_image_synced(
            client, volume_name, backing_image
        )

    _, b = find_backup(client, volume_name, snap2.name)

    res_name = common.generate_volume_name()
    res_volume = client.create_volume(name=res_name, size=size,
                                      numberOfReplicas=2,
                                      fromBackup=b.url)
    res_volume = wait_for_volume_restoration_completed(
        client, res_name)
    res_volume = wait_for_volume_detached(client, res_name)
    res_volume = res_volume.attach(hostId=host_id)
    res_volume = wait_for_volume_healthy(client, res_name)
    check_volume_data(res_volume, data)

    snapshots = res_volume.snapshotList()
    # only the backup snapshot + volume-head
    assert len(snapshots) == 2
    backup_snapshot = ""
    for snap in snapshots:
        if snap.name != "volume-head":
            backup_snapshot = snap.name
    assert backup_snapshot != ""

    create_snapshot(client, res_name)
    snapshots = res_volume.snapshotList()
    assert len(snapshots) == 3

    res_volume.snapshotDelete(name=backup_snapshot)
    res_volume.snapshotPurge()
    res_volume = wait_for_snapshot_purge(client, res_name,
                                         backup_snapshot)

    snapshots = res_volume.snapshotList()
    assert len(snapshots) == 2

    ha_rebuild_replica_test(client, res_name)

    res_volume = res_volume.detach()
    res_volume = wait_for_volume_detached(client, res_name)

    client.delete(res_volume)
    wait_for_volume_delete(client, res_name)


# https://github.com/rancher/longhorn/issues/415
def test_ha_prohibit_deleting_last_replica(client, volume_name):  # NOQA
    """
    Test prohibiting deleting the last replica

    1. Create volume with one replica and attach to the current node.
    2. Try to delete the replica. It should error out

    FIXME: Move out of test_ha.py
    """
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=1)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 1
    replica0 = volume.replicas[0]

    with pytest.raises(Exception) as e:
        volume.replicaRemove(name=replica0.name)
    assert "no other healthy replica available" in str(e.value)

    cleanup_volume(client, volume)


def test_ha_recovery_with_expansion(client, volume_name, request):   # NOQA
    """
    [HA] Test recovery with volume expansion

    1. Create a volume and attach it to the current node.
    2. Write a large amount of data to the volume
    3. Remove one random replica and wait for the rebuilding starts
    4. Expand the volume immediately after the rebuilding start
    5. check and wait for the volume expansion and rebuilding
    6. Write more data to the volume
    7. Remove another replica of volume
    8. Wait volume to start rebuilding and complete
    9. Check the data intacty
    """
    original_size = str(3 * Gi)
    expand_size = str(4 * Gi)
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=2,
                                     size=original_size)

    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2
    replica0 = volume.replicas[0]
    assert replica0.name != ""
    replica1 = volume.replicas[1]
    assert replica1.name != ""

    volume_path = get_volume_endpoint(volume)
    tmp_file_path = "/tmp/test-ha-recovery-during-expansion-data1"

    def finalizer():
        exec_cmd = ["rm", "-rf", tmp_file_path]
        subprocess.check_output(exec_cmd)

    request.addfinalizer(finalizer)

    # Step 2: prepare data then copy it into the volume
    write_volume_dev_random_mb_data(
        tmp_file_path, 0, DATA_SIZE_IN_MB_4*3)
    cksum1 = get_volume_dev_mb_data_md5sum(
        tmp_file_path, 0, DATA_SIZE_IN_MB_4*3)
    copy_file_to_volume_dev_mb_data(
        tmp_file_path, volume_path, 0, 0, DATA_SIZE_IN_MB_4*3)

    # Step 3: Trigger volume rebuilding first
    volume.replicaRemove(name=replica0.name)
    wait_for_rebuild_start(client, volume_name)
    # Step 4: Then trigger volume expansion immediately
    volume.expand(size=expand_size)
    # Step 5: Wait for volume expansion & rebuilding
    wait_for_volume_expansion(client, volume.name)
    wait_for_rebuild_complete(client, volume.name)
    volume = client.by_id_volume(volume_name)
    check_block_device_size(volume, int(expand_size))

    write_volume_dev_random_mb_data(
        tmp_file_path, 0, DATA_SIZE_IN_MB_4)
    cksum2 = get_volume_dev_mb_data_md5sum(
        tmp_file_path, 0, DATA_SIZE_IN_MB_4)
    copy_file_to_volume_dev_mb_data(
        tmp_file_path, volume_path, 0, 1024, DATA_SIZE_IN_MB_4)

    # Step 7 & 8: Trigger volume rebuilding again after expansion
    volume.replicaRemove(name=replica1.name)
    wait_for_rebuild_start(client, volume_name)
    wait_for_rebuild_complete(client, volume.name)

    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2
    volume = client.by_id_volume(volume_name)
    check_block_device_size(volume, int(expand_size))

    volume_cksum1 = get_volume_dev_mb_data_md5sum(
        volume_path, 0, DATA_SIZE_IN_MB_4*3)
    assert cksum1 == volume_cksum1
    volume_cksum2 = get_volume_dev_mb_data_md5sum(
        volume_path, 1024, DATA_SIZE_IN_MB_4*3)
    assert cksum2 == volume_cksum2

    cleanup_volume(client, volume)


def wait_pod_for_remount_request(client, core_api, volume_name, pod_name, original_md5sum, data_path="/data/test"):  # NOQA
    try:
        # this line may fail if the recovery is too quick
        wait_for_volume_faulted(client, volume_name)
    except AssertionError:
        print("\nException waiting for volume faulted,"
              "could have missed it")

    wait_for_volume_healthy(client, volume_name)

    try:
        common.wait_for_pod_phase(core_api, pod_name, pod_phase="Pending")
    except AssertionError:
        print("\nException waiting for pod pending,"
              "could have missed it")
    common.wait_for_pod_phase(core_api, pod_name, pod_phase="Running")

    wait_for_pod_remount(core_api, pod_name)

    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert md5sum == original_md5sum


def test_salvage_auto_crash_all_replicas(client, core_api, storage_class, sts_name, statefulset):  # NOQA
    """
    [HA] Test automatic salvage feature by crashing all the replicas

    Case #1: crash all replicas
    1. Create StorageClass and StatefulSet.
    2. Write random data to the pod and get the md5sum.
    3. Run `sync` command inside the pod to make sure data flush to the volume.
    4. Crash all replica processes using SIGTERM.
    5. Wait for volume to `faulted`, then `healthy`.
    6. Wait for K8s to terminate the pod and statefulset to bring pod to
       `Pending`, then `Running`.
    7. Check volume path exist in the pod.
    8. Check md5sum of the data in the pod.
    Case #2: crash one replica and then crash all replicas
    9. Crash one of the replica.
    10. Try to wait for rebuild start and the rebuilding replica running.
    11. Crash all the replicas.
    12. Make sure volume and pod recovers.
    13. Check md5sum of the data in the pod.

    FIXME: Step 5 is only a intermediate state, maybe no way to get it for sure
    """

    # Case #1
    vol_name, pod_name, md5sum = common.prepare_statefulset_with_data_in_mb(
        client, core_api, statefulset, sts_name, storage_class)
    crash_replica_processes(client, core_api, vol_name)
    wait_pod_for_remount_request(client, core_api, vol_name, pod_name, md5sum)

    # Case #2
    volume = client.by_id_volume(vol_name)
    replica0 = volume.replicas[0]

    crash_replica_processes(client, core_api, vol_name, [replica0])

    volume = wait_for_volume_healthy(client, vol_name)
    replicas = []
    for r in volume.replicas:
        if r.running is True:
            replicas.append(r)

    crash_replica_processes(client, core_api, vol_name, replicas)

    wait_pod_for_remount_request(client, core_api, vol_name, pod_name, md5sum)


def test_rebuild_failure_with_intensive_data(client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test rebuild failure with intensive data writing

    1. Create PV/PVC/POD with livenss check
    2. Create volume and wait for pod to start
    3. Write data to `/data/test1` inside the pod and get `original_checksum_1`
    4. Write data to `/data/test2` inside the pod and get `original_checksum_2`
    5. Find running replicas of the volume
    6. Crash one of the running replicas.
    7. Wait for the replica rebuild to start
    8. Crash the replica which is sending data to the rebuilding replica
    9. Wait for volume to finish two rebuilds and become healthy
    10. Check md5sum for both data location
    """

    data_path_1 = "/data/test1"
    data_path_2 = "/data/test2"
    pod_name, pv_name, pvc_name, original_md5sum_1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, volume_name,
            volume_size=str(2*Gi),
            data_path=data_path_1, data_size_in_mb=DATA_SIZE_IN_MB_4)
    create_snapshot(client, volume_name)
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path_2, DATA_SIZE_IN_MB_4)
    original_md5sum_2 = get_pod_data_md5sum(core_api, pod_name, data_path_2)

    volume = client.by_id_volume(volume_name)
    replicas = []
    for r in volume.replicas:
        if r.running:
            replicas.append(r)
        else:
            volume.replicaRemove(name=r.name)
    assert len(replicas) == 3
    random.shuffle(replicas)
    # Trigger rebuild
    crash_replica_processes(client, core_api, volume_name, [replicas[0]])
    wait_for_volume_degraded(client, volume_name)
    # Trigger rebuild failure by
    # crashing the replica which is sending data to the rebuilding replica
    from_replica_name, _ = wait_for_rebuild_start(client, volume_name)
    for r in replicas:
        if r.name == from_replica_name:
            from_replica = r
    assert from_replica
    crash_replica_processes(client, core_api, volume_name, [from_replica])
    wait_for_volume_healthy(client, volume_name)
    md5sum_1 = get_pod_data_md5sum(core_api, pod_name, data_path_1)
    assert original_md5sum_1 == md5sum_1
    md5sum_2 = get_pod_data_md5sum(core_api, pod_name, data_path_2)
    assert original_md5sum_2 == md5sum_2


def test_rebuild_replica_and_from_replica_on_the_same_node(client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test the corner case that the from-replica and the rebuilding replica
    are on the same node

    Test prerequisites:
      - set Replica Node Level Soft Anti-Affinity disabled

    1. Disable the setting replica-soft-anti-affinity.
    2. Set replica replenishment wait interval to an appropriate value.
    3. Create a pod with Longhorn volume and wait for pod to start
    4. Write data to `/data/test` inside the pod and get `original_checksum`
    5. Disable scheduling for all nodes except for one.
    6. Find running replicas of the volume
    7. Crash 2 running replicas.
    8. Wait for the replica rebuild to start.
    9. Check if the rebuilding replica is one of the crashed replica,
       and this reused replica is rebuilt on the only available node.
    10. Check md5sum for the written data
    """

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")
    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value="600")

    data_path = "/data/test"
    pod_name, pv_name, pvc_name, original_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, volume_name,
            volume_size=str(2*Gi),
            data_path=data_path, data_size_in_mb=2*Gi)

    volume = client.by_id_volume(volume_name)
    original_replicas = volume.replicas
    assert len(original_replicas) == 3

    available_node_name = original_replicas[0].hostId
    nodes = client.list_node()
    assert len(nodes) > 0
    for node in nodes:
        if node.name == available_node_name:
            continue
        node = set_node_scheduling(client, node, allowScheduling=False)
        common.wait_for_node_update(client, node.id,
                                    "allowScheduling", False)

    # Trigger rebuild
    crash_replica_processes(client, core_api, volume_name,
                            [original_replicas[0], original_replicas[1]])
    wait_for_volume_degraded(client, volume_name)
    from_replica_name, rebuilding_replica_name = \
        wait_for_rebuild_start(client, volume_name)
    assert from_replica_name != rebuilding_replica_name
    assert from_replica_name == original_replicas[2].name
    assert rebuilding_replica_name == original_replicas[0].name

    # Wait for volume healthy and
    # check if the failed replica on the only available node is reused.
    wait_for_rebuild_complete(client, volume_name)
    volume = wait_for_volume_degraded(client, volume_name)
    assert volume.robustness == "degraded"
    for r in volume.replicas:
        if r.name == rebuilding_replica_name:
            assert r.hostId == available_node_name

    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert original_md5sum == md5sum


def test_rebuild_with_restoration(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make): # NOQA
    """
    [HA] Test if the rebuild is disabled for the restoring volume.

    This is similar to test_single_replica_restore_failure and
    test_single_replica_unschedulable_restore_failure. In this version, a
    replica is deleted. We expect a new replica to be rebuilt in its place and
    the restore to complete.

    1. Setup a random backupstore.
    2. Do cleanup for the backupstore.
    3. Create a pod with a volume and wait for pod to start.
    4. Write data to the pod volume and get the md5sum.
    5. Create a backup for the volume.
    6. Restore a volume from the backup.
    7. Wait for the volume restore start.
    8. Delete one replica during the restoration.
    9. Wait for the restoration complete and the volume detached.
    10. Check if the replica is rebuilt.
    11. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    12. Check if the restored volume is state `Healthy`
        after the attachment.
    13. Check md5sum of the data in the restored volume.
    14. Do cleanup.
    """
    restore_with_replica_failure(client, core_api, volume_name, csi_pv, pvc,
                                 pod_make, False, False,
                                 REPLICA_FAILURE_MODE_DELETE)


def test_rebuild_with_inc_restoration(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if the rebuild is disabled for the DR volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to `/data/test1` inside the pod and get the md5sum.
    4. Create the 1st backup for the volume.
    5. Create a DR volume based on the backup
       and wait for the init restoration complete.
    6. Write more data to the original volume then create the 2nd backup.
    7. Delete one replica and trigger incremental restore simultaneously.
    8. Wait for the inc restoration complete and the volume becoming Healthy.
    9. Activate the DR volume.
    10. Create PV/PVC/Pod for the activated volume
        and wait for the pod start.
    11. Check if the restored volume is state `healthy`
        after the attachment.
    12. Check md5sum of the data in the activated volume.
    13. Do cleanup.
    """
    update_setting(client, common.SETTING_DEGRADED_AVAILABILITY, "false")

    std_volume_name = volume_name + "-std"
    data_path1 = "/data/test1"
    std_pod_name, std_pv_name, std_pvc_name, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
            volume_size=str(2*Gi),
            data_path=data_path1, data_size_in_mb=DATA_SIZE_IN_MB_2)

    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    bv, b1 = find_backup(client, std_volume_name, snap1.name)

    dr_volume_name = volume_name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(2*Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_4)
    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, data_path2)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name)
    bv, b2 = find_backup(client, std_volume_name, snap2.name)

    # Trigger rebuild during the incremental restoration
    wait_for_volume_restoration_start(client, dr_volume_name, b2.name)
    dr_volume = client.by_id_volume(dr_volume_name)
    for r in dr_volume.replicas:
        failed_replica = r.name
        break
    assert failed_replica
    dr_volume.replicaRemove(name=failed_replica)
    client.list_backupVolume()

    wait_for_volume_degraded(client, dr_volume_name)

    # Wait for the rebuild start
    running_replica_count = 0
    for i in range(RETRY_COUNTS):
        running_replica_count = 0
        dr_volume = client.by_id_volume(dr_volume_name)
        for r in dr_volume.replicas:
            if r['running'] and not r['failedAt']:
                running_replica_count += 1
        if running_replica_count == 3:
            break
        time.sleep(RETRY_INTERVAL)
    assert running_replica_count == 3

    # Wait for inc restoration & rebuild complete
    wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    check_volume_last_backup(client, dr_volume_name, b2.name)

    activate_standby_volume(client, dr_volume_name)
    wait_for_volume_detached(client, dr_volume_name)

    dr_pod_name = dr_volume_name + "-pod"
    dr_pv_name = dr_volume_name + "-pv"
    dr_pvc_name = dr_volume_name + "-pvc"
    dr_pod = pod_make(name=dr_pod_name)
    create_pv_for_volume(client, core_api, dr_volume, dr_pv_name)
    create_pvc_for_volume(client, core_api, dr_volume, dr_pvc_name)
    dr_pod['spec']['volumes'] = [create_pvc_spec(dr_pvc_name)]
    create_and_wait_pod(core_api, dr_pod)

    dr_volume = client.by_id_volume(dr_volume_name)
    assert dr_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_HEALTHY

    md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path1)
    assert std_md5sum1 == md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert std_md5sum2 == md5sum2

    # cleanup
    backupstore_cleanup(client)


def test_inc_restoration_with_multiple_rebuild_and_expansion(set_random_backupstore, client, core_api, volume_name, storage_class, csi_pv, pvc, pod_make): # NOQA
    """
    [HA] Test if the rebuild is disabled for the DR volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to the volume and get the md5sum.
    4. Create the 1st backup for the volume.
    5. Create a DR volume based on the backup
       and wait for the init restoration complete.
    6. Shutdown the pod and wait for the std volume detached.
    7. Offline expand the std volume and wait for expansion complete.
    8. Re-launch a pod for the std volume.
    9. Write more data to the std volume. Make sure there is data in the
       expanded part.
    10. Create the 2nd backup and wait for the backup creation complete.
    11. For the DR volume, delete one replica and trigger incremental restore
        simultaneously.
    12. Wait for the inc restoration complete and the volume becoming Healthy.
    13. Check the DR volume size and snapshot info. Make sure there is only
        one snapshot in the volume.
    14. Online expand the std volume and wait for expansion complete.
    15. Write data to the std volume then create the 3rd backup.
    16. Trigger the inc restore then re-verify the snapshot info.
    17. Activate the DR volume.
    18. Create PV/PVC/Pod for the activated volume
        and wait for the pod start.
    19. Check if the restored volume is state `healthy`
        after the attachment.
    20. Check md5sum of the data in the activated volume.
    21. Crash one random replica. Then verify the rebuild still works fine for
        the activated volume.
    22. Do cleanup.
    """
    update_setting(client, common.SETTING_DEGRADED_AVAILABILITY, "false")
    create_storage_class(storage_class)

    original_size = 1 * Gi
    std_pod_name = 'std-pod-for-dr-expansion-and-rebuilding'
    std_pvc_name = "pvc-" + std_pod_name
    pvc['metadata']['name'] = std_pvc_name
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    pvc['spec']['resources']['requests']['storage'] = \
        str(original_size)
    create_pvc(pvc)

    std_pod_manifest = pod_make(name=std_pod_name)
    std_pod_manifest['spec']['volumes'] = [create_pvc_spec(std_pvc_name)]
    create_and_wait_pod(core_api, std_pod_manifest)

    std_pv = wait_and_get_pv_for_pvc(core_api, std_pvc_name)
    assert std_pv.status.phase == "Bound"
    std_volume_name = std_pv.spec.csi.volume_handle
    std_volume = wait_for_volume_healthy(client, std_volume_name)

    # Create the 1st backup.
    data_path1 = "/data/test1"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path1, DATA_SIZE_IN_MB_4)
    std_md5sum1 = get_pod_data_md5sum(core_api, std_pod_name, data_path1)

    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client,
                               std_volume_name,
                               snap1.name,
                               retry_count=600)
    bv, b1 = find_backup(client, std_volume_name, snap1.name)

    # Create the DR volume
    dr_volume_name = volume_name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    # Step 7: Do offline expansion for the std volume.
    delete_and_wait_pod(core_api, std_pod_name)
    wait_for_volume_detached(client, std_volume_name)
    expand_size1 = 2 * Gi
    expand_and_wait_for_pvc(core_api, pvc, expand_size1)
    wait_for_volume_expansion(client, std_volume_name)
    std_volume = wait_for_volume_detached(client, std_volume_name)
    assert std_volume.size == str(expand_size1)

    # Re-launch the pod
    create_and_wait_pod(core_api, std_pod_manifest)
    wait_for_volume_healthy(client, std_volume_name)

    # Step 9:
    # When the total writen data size is more than 1Gi, there must be data in
    # the expanded part.
    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_4)
    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, data_path2)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume = client.by_id_volume(std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name,
                               retry_count=600)
    bv, b2 = find_backup(client, std_volume_name, snap2.name)

    # Step 11:
    # Pick up a random replica and fail it.
    # Then trigger rebuild and the incremental restoration
    dr_volume = client.by_id_volume(dr_volume_name)
    for r in dr_volume.replicas:
        failed_replica = r.name
        break
    assert failed_replica
    dr_volume.replicaRemove(name=failed_replica)
    client.list_backupVolume()

    # Wait for the rebuild start
    wait_for_volume_degraded(client, dr_volume_name)
    running_replica_count = 0
    for i in range(RETRY_COUNTS):
        running_replica_count = 0
        dr_volume = client.by_id_volume(dr_volume_name)
        for r in dr_volume.replicas:
            if r['running'] and not r['failedAt']:
                running_replica_count += 1
        if running_replica_count == 3:
            break
        time.sleep(RETRY_INTERVAL)
    assert running_replica_count == 3

    # Wait for inc restoration & rebuild complete
    wait_for_dr_volume_expansion(client, dr_volume_name, str(expand_size1))
    wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    check_volume_last_backup(client, dr_volume_name, b2.name)

    # Verify the snapshot info
    dr_volume = client.by_id_volume(dr_volume_name)
    assert dr_volume.size == str(expand_size1)
    wait_for_snapshot_count(dr_volume, 2, count_removed=True)
    snapshots = dr_volume.snapshotList(volume=dr_volume_name)
    for snap in snapshots:
        if snap["name"] != "volume-head":
            assert snap["name"] == "expand-" + str(expand_size1)
            assert not snap["usercreated"]
            assert "volume-head" in snap["children"]

    # Step 14: Do online expansion for the std volume.
    expand_size2 = 3 * Gi
    expand_and_wait_for_pvc(core_api, pvc, expand_size2)
    wait_for_volume_expansion(client, std_volume_name)

    # Step 15:
    # When the total writen data size is more than 2Gi, there must be data in
    # the 2nd expanded part.
    data_path3 = "/data/test3"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path3, DATA_SIZE_IN_MB_4)
    std_md5sum3 = get_pod_data_md5sum(core_api, std_pod_name, data_path3)
    # Then create the 3rd backup for the std volume
    snap3 = create_snapshot(client, std_volume_name)
    std_volume = client.by_id_volume(std_volume_name)
    std_volume.snapshotBackup(name=snap3.name)
    wait_for_backup_completion(client, std_volume_name, snap3.name)
    bv, b3 = find_backup(client, std_volume_name, snap3.name)

    # Step 16:
    # Trigger the restoration for the DR volume.
    client.list_backupVolume()
    check_volume_last_backup(client, dr_volume_name, b3.name)
    wait_for_dr_volume_expansion(client, dr_volume_name, str(expand_size2))
    # Then re-verify the snapshot info
    dr_volume = client.by_id_volume(dr_volume_name)
    assert dr_volume.size == str(expand_size2)
    wait_for_snapshot_count(dr_volume, 2, count_removed=True)
    snapshots = dr_volume.snapshotList(volume=dr_volume_name)
    for snap in snapshots:
        if snap["name"] != "volume-head":
            assert snap["name"] == "expand-" + str(expand_size2)
            assert not snap["usercreated"]
            assert "volume-head" in snap["children"]

    activate_standby_volume(client, dr_volume_name)
    wait_for_volume_detached(client, dr_volume_name)

    dr_pod_name = dr_volume_name + "-pod"
    dr_pv_name = dr_volume_name + "-pv"
    dr_pvc_name = dr_volume_name + "-pvc"
    dr_pod = pod_make(name=dr_pod_name)
    create_pv_for_volume(client, core_api, dr_volume, dr_pv_name)
    create_pvc_for_volume(client, core_api, dr_volume, dr_pvc_name)
    dr_pod['spec']['volumes'] = [create_pvc_spec(dr_pvc_name)]
    create_and_wait_pod(core_api, dr_pod)
    dr_volume = wait_for_volume_healthy(client, dr_volume_name)

    md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path1)
    assert std_md5sum1 == md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert std_md5sum2 == md5sum2
    md5sum3 = get_pod_data_md5sum(core_api, dr_pod_name, data_path3)
    assert std_md5sum3 == md5sum3

    failed_replica = dr_volume.replicas[0]
    crash_replica_processes(client, core_api, dr_volume_name,
                            replicas=[failed_replica],
                            wait_to_fail=False)
    wait_for_volume_degraded(client, dr_volume_name)
    wait_for_volume_healthy(client, dr_volume_name)

    # Check if the activated volume still works fine after the rebuild
    write_pod_volume_data(core_api, dr_pod_name, 'longhorn-integration-test',
                          filename='test4')
    read_data = read_volume_data(core_api, dr_pod_name, 'test4')
    assert read_data == 'longhorn-integration-test'

    # cleanup
    backupstore_cleanup(client)


@pytest.mark.coretest  # NOQA
def test_single_replica_failed_during_engine_start(client, core_api, volume_name, csi_pv, pvc, pod):  # NOQA
    """
    Test if the volume still works fine when there is
    an invalid replica/backend in the engine starting phase.

    Prerequisite:
    Setting "replica-replenishment-wait-interval" is 0

    1. Create a pod using Longhorn volume.
    2. Write some data to the volume then get the md5sum.
    3. Create a snapshot.
    4. Repeat step2 and step3 for 3 times then there should be 3 snapshots.
    5. Randomly pick up a replica and
       manually messing up the snapshot meta file.
    6. Delete the pod and wait for the volume detached.
    7. Recreate the pod and wait for the volume attached.
    8. Check if the volume is Degraded and
       if the chosen replica is ERR once the volume attached.
    9. Wait for volume rebuild and volume becoming Healthy.
    10. Check volume data.
    11. Check if the volume still works fine by
        r/w data and creating/removing snapshots.
    """
    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value="0")

    pv_name = "pv-" + volume_name
    pvc_name = "pvc-" + volume_name
    pod_name = "pod-" + volume_name
    volume_size = str(1 * Gi)

    csi_pv['metadata']['name'] = pv_name
    csi_pv['spec']['csi']['volumeHandle'] = volume_name
    csi_pv['spec']['capacity']['storage'] = volume_size
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['volumeName'] = pv_name
    pvc['spec']['resources']['requests']['storage'] = volume_size
    pvc['spec']['storageClassName'] = ''

    create_and_check_volume(client, volume_name, size=volume_size)
    core_api.create_persistent_volume(csi_pv)
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': pvc_name,
        },
    }]

    create_and_wait_pod(core_api, pod)
    wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    data_path1 = "/data/file1"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path1, DATA_SIZE_IN_MB_1)
    data_md5sum1 = get_pod_data_md5sum(core_api, pod_name, data_path1)
    snap1 = volume.snapshotCreate()

    data_path2 = "/data/file2"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path2, DATA_SIZE_IN_MB_1)
    data_md5sum2 = get_pod_data_md5sum(core_api, pod_name, data_path2)
    snap2 = volume.snapshotCreate()

    data_path3 = "/data/file3"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path3, DATA_SIZE_IN_MB_1)
    data_md5sum3 = get_pod_data_md5sum(core_api, pod_name, data_path3)
    snap3 = volume.snapshotCreate()

    volume = client.by_id_volume(volume_name)
    host_id = get_self_host_id()

    for replica in volume.replicas:
        if replica.hostId == host_id:
            break

    replica_data_path = replica.dataPath
    replica_name = replica.name
    snap2_meta_file = replica_data_path + \
        "/volume-snap-" + \
        snap2.name + ".img.meta"

    command = ["dd", "if=/dev/zero",
               "of="+snap2_meta_file,
               "count=" + str(100)]
    subprocess.check_call(command)

    delete_and_wait_pod(core_api, pod_name)
    wait_for_volume_detached(client, volume_name)

    create_and_wait_pod(core_api, pod)
    wait_for_volume_degraded(client, volume_name)
    wait_for_replica_failed(client, volume_name, replica_name)

    wait_for_volume_healthy(client, volume_name)

    res_data_md5sum1 = get_pod_data_md5sum(core_api, pod_name, data_path1)
    assert data_md5sum1 == res_data_md5sum1

    res_data_md5sum2 = get_pod_data_md5sum(core_api, pod_name, data_path2)
    assert data_md5sum2 == res_data_md5sum2

    res_data_md5sum3 = get_pod_data_md5sum(core_api, pod_name, data_path3)
    assert data_md5sum3 == res_data_md5sum3

    data_path4 = "/data/file4"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path4, DATA_SIZE_IN_MB_1)
    data_md5sum4 = get_pod_data_md5sum(core_api, pod_name, data_path4)

    res_data_md5sum4 = get_pod_data_md5sum(core_api, pod_name, data_path4)
    assert data_md5sum4 == res_data_md5sum4

    snap4 = volume.snapshotCreate()

    snapshots = volume.snapshotList()
    for snap in snapshots:
        if snap.usercreated is False and snap.name != "volume-head":
            system_snap = snap
            break

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
    assert snapMap[snap4.name].name == snap4.name
    assert snapMap[snap4.name].parent == system_snap.name
    assert snapMap[snap4.name].removed is False

    volume.snapshotDelete(name=snap3.name)

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
    assert snapMap[snap3.name].removed is True
    assert snapMap[snap4.name].name == snap4.name
    assert snapMap[snap4.name].parent == system_snap.name
    assert len(snapMap[snap4.name].children) == 1
    assert "volume-head" in snapMap[snap4.name].children.keys()
    assert snapMap[snap4.name].removed is False


@pytest.mark.skipif('s3' not in BACKUPSTORE, reason='This test is only applicable for s3')  # NOQA
def test_restore_volume_with_invalid_backupstore(client, volume_name, backupstore_s3): # NOQA
    """
    [HA] Test if the invalid backup target will lead to to volume restore.

    1. Enable auto-salvage.
    2. Set a S3 backupstore. (Cannot use NFS server here before fixing #1295)
    3. Create a volume then a backup.
    4. Invalidate the target URL.
       (e.g.: s3://backupbucket-invalid@us-east-1/backupstore-invalid)
    5. Restore a volume from the backup should return error.
       (The fromBackup fields of the volume create API should consist of
       the invalid target URL and the valid backup volume info)
    6. Check restore volume not created.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    _, b, _, _ = create_backup(client, volume_name)

    res_name = "res-" + volume_name
    invalid_backup_target_url = \
        "s3://backupbucket-invalid@us-east-1/backupstore-invalid"

    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    backup_target_setting = client.update(backup_target_setting,
                                          value=invalid_backup_target_url)

    # make fromBackup URL consistent to the the invalid target URL
    url = invalid_backup_target_url + b.url.split("?")[1]
    with pytest.raises(Exception) as e:
        client.create_volume(name=res_name,
                             fromBackup=url)
    assert "unable to create volume" in str(e.value)

    volumes = client.list_volume()
    for v in volumes:
        assert v.name != res_name


def test_all_replica_restore_failure(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if all replica restore failure will lead to the restore volume
    becoming Faulted, and if the auto salvage feature is disabled for
    the faulted restore volume.

    1. Enable auto-salvage.
    2. Set the a random backupstore.
    3. Do cleanup for the backupstore.
    4. Create a pod with a volume and wait for pod to start.
    5. Write data to the pod volume and get the md5sum.
    6. Create a backup for the volume.
    7. Randomly delete some data blocks of the backup, which will lead to
       all replica restore failures later.
    8. Restore a volume from the backup.
    9. Wait for the volume restore in progress by checking if:
       9.1. `volume.restoreStatus` shows the related restore info.
       9.2. `volume.conditions[Restore].status == True &&
            volume.conditions[Restore].reason == "RestoreInProgress"`.
       9.3. `volume.ready == false`.
    10. Wait for the restore volume Faulted.
    11. Check if `volume.conditions[Restore].status == False &&
        volume.conditions[Restore].reason == "RestoreFailure"`.
    12. Check if `volume.ready == false`.
    13. Make sure auto-salvage is not triggered even the feature is enabled.
    14. Verify if PV/PVC cannot be created from Longhorn.
    15. Verify the faulted volume cannot be attached to a node.
    16. Verify this faulted volume can be deleted.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    backupstore_cleanup(client)

    prepare_pod_with_data_in_mb(
        client, core_api, csi_pv, pvc, pod_make, volume_name)

    snap = create_snapshot(client, volume_name)

    volume = client.by_id_volume(volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    _, b = find_backup(client, volume_name, snap.name)

    backupstore_delete_random_backup_block(client, core_api, volume_name)

    res_name = "res-" + volume_name
    res_volume = client.create_volume(name=res_name,
                                      fromBackup=b.url)

    wait_for_volume_condition_restore(client, res_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, res_name,
                                      "reason", "RestoreInProgress")

    res_volume = client.by_id_volume(res_name)
    assert res_volume.ready is False

    wait_for_volume_faulted(client, res_name)
    wait_for_volume_detached(client, res_name)

    res_volume = client.by_id_volume(res_name)
    assert res_volume.conditions['Restore'].status == "False"
    assert res_volume.conditions['Restore'].reason == "RestoreFailure"
    assert res_volume.ready is False
    assert res_volume.state == "detached"
    assert hasattr(res_volume, 'pvCreate') is False
    assert hasattr(res_volume, 'pvcCreate') is False
    with pytest.raises(Exception) as e:
        res_volume.attach(hostId=get_self_host_id())
    assert "unable to attach volume" in str(e.value)

    client.delete(res_volume)
    wait_for_volume_delete(client, res_name)


def test_single_replica_restore_failure(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if one replica restore failure will lead to the restore volume
    becoming Degraded, and if the restore volume is still usable after
    the failure.

    This is similar to test_rebuild_with_restoration and
    test_single_replica_unschedulable_restore_failure. In this version, a
    replica is crashed. We expect the crashed replica to be rebuilt and the
    restore to complete.

    1. Setup a random backupstore.
    2. Do cleanup for the backupstore.
    3. Create a pod with a volume and wait for pod to start.
    4. Write data to the pod volume and get the md5sum.
    5. Create a backup for the volume.
    6. Restore a volume from the backup.
    7. Wait for the volume restore start.
    8. Crash one replica during the restoration.
    9. Wait for the restoration complete and the volume detached.
    10. Check if the replica is rebuilt.
    11. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    12. Check if the restored volume is state `Healthy`
        after the attachment.
    13. Check md5sum of the data in the restored volume.
    14. Do cleanup.
    """
    restore_with_replica_failure(client, core_api, volume_name, csi_pv, pvc,
                                 pod_make, False, False,
                                 REPLICA_FAILURE_MODE_CRASH)


def test_single_replica_unschedulable_restore_failure(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make): # NOQA
    """
    [HA] Test if the restore can complete if a restoring replica is killed
    while it is ongoing and cannot be recovered.

    This is similar to test_rebuild_with_restoration and
    test_single_replica_restore_failure. In this version, a replica is crashed
    and not allowed to recover. However, we enable
    allow-volume-creation-with-degraded-availability, so we expect the restore
    to complete anyway.

    1. Setup a random backupstore.
    2. Do cleanup for the backupstore.
    3. Enable allow-volume-creation-with-degraded-availability (to allow
       restoration to complete without all replicas).
    4. Create a pod with a volume and wait for pod to start.
    5. Write data to the pod volume and get the md5sum.
    6. Create a backup for the volume.
    7. Restore a volume from the backup.
    8. Wait for the volume restore start.
    9. Disable replica rebuilding (to ensure the killed replica cannot
       recover).
    10. Crash one replica during the restoration.
    11. Wait for the restoration complete and the volume detached.
    12. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    13. Check if the restored volume is state `Healthy`
        after the attachment.
    14. Check md5sum of the data in the restored volume.
    15. Do cleanup.
    """
    restore_with_replica_failure(client, core_api, volume_name, csi_pv, pvc,
                                 pod_make, True, True,
                                 REPLICA_FAILURE_MODE_CRASH)

def test_dr_volume_with_restore_command_error(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    Test if Longhorn can capture and handle the restore command error
    rather than the error triggered the data restoring.

    1. Set a random backupstore.
    2. Create a volume, then create the corresponding PV, PVC and Pod.
    3. Write data to the pod volume and get the md5sum
       after the pod running.
    4. Create the 1st backup.
    5. Create a DR volume from the backup.
    6. Wait for the DR volume restore complete.
    7. Create a non-empty directory `volume-delta-<last backup name>.img`
       in one replica directory of the DR volume. This will fail the
       restore command call later.
    8. Write data to the original volume then create the 2nd backup.
    9. Wait for incremental restore complete.
       Then verify the DR volume is Degraded
       and there is one failed replica.
    10. Verify the failed replica will be reused for rebuilding
        (restore actually).
    11. Activate the DR volume and wait for it complete.
    12. Create PV/PVC/Pod for the activated volume.
    13. Validate the volume content.
    14. Verify Writing data to the activated volume is fine.
    """
    update_setting(client, common.SETTING_DEGRADED_AVAILABILITY, "false")

    std_volume_name = volume_name + "-std"
    data_path1 = "/data/test1"
    std_pod_name, std_pv_name, std_pvc_name, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
            data_path=data_path1, data_size_in_mb=DATA_SIZE_IN_MB_1)

    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    bv, b1 = find_backup(client, std_volume_name, snap1.name)

    dr_volume_name = volume_name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_volume_restoration_start(client, dr_volume_name, b1.name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    dr_volume = client.by_id_volume(dr_volume_name)
    # Will hack into the replica directory, create a non-empty directory
    # in the special path. (This path will be reserved for the restore.)
    # Then the following inc restore should fail.
    failed_replica = dr_volume.replicas[0]
    cmd = "mkdir -p " + "/host" + failed_replica.dataPath + "/volume-delta-" +\
          dr_volume.controllers[0].lastRestoredBackup + ".img/random-dir"
    exec_instance_manager(core_api,
                          failed_replica.instanceManagerName, cmd)

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_1)
    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, data_path2)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name)
    bv, b2 = find_backup(client, std_volume_name, snap2.name)

    # Wait for the incremental restoration triggered then complete.
    client.list_backupVolume()
    check_volume_last_backup(client, dr_volume_name, b2.name)
    wait_for_volume_restoration_start(client, dr_volume_name, b2.name)

    dr_volume = wait_for_volume_degraded(client, dr_volume_name)
    verified = False
    for r in dr_volume.replicas:
        if r.name == failed_replica.name:
            assert not r['running']
            assert r['failedAt'] != ""
            verified = True
        else:
            assert r['running']
            assert r['failedAt'] == ""
    assert verified

    wait_for_backup_restore_completed(client, dr_volume_name, b2.name)

    dr_volume = wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    verified = False
    for r in dr_volume.replicas:
        assert r['running']
        assert r['failedAt'] == ""
        if r.name == failed_replica.name:
            verified = True
    assert verified

    activate_standby_volume(client, dr_volume_name)
    dr_volume = wait_for_volume_detached(client, dr_volume_name)

    dr_pod_name = dr_volume_name + "-pod"
    dr_pv_name = dr_volume_name + "-pv"
    dr_pvc_name = dr_volume_name + "-pvc"
    dr_pod = pod_make(name=dr_pod_name)
    create_pv_for_volume(client, core_api, dr_volume, dr_pv_name)
    create_pvc_for_volume(client, core_api, dr_volume, dr_pvc_name)
    dr_pod['spec']['volumes'] = [create_pvc_spec(dr_pvc_name)]
    create_and_wait_pod(core_api, dr_pod)

    md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path1)
    assert std_md5sum1 == md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert std_md5sum2 == md5sum2

    backupstore_cleanup(client)


def test_engine_crash_for_restore_volume(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test volume can successfully retry restoring after
    the engine crashes unexpectedly.

    1. Setup a random backupstore.
    2. Create volume and start the pod.
    3. Write random data to the pod volume and get the md5sum.
    4. Create a backup for the volume.
    5. Restore a new volume from the backup.
    6. Crash the engine during the restore.
    7. Wait for the volume detaching.
    8. Wait for the volume reattached.
    9. Verify if
      9.1. `volume.ready == false`.
      9.2. `volume.conditions[Restore].status == True &&
            volume.conditions[Restore].reason == "RestoreInProgress"`.
    10. Wait for the volume restore complete and detached.
    11. Recreate a pod for the restored volume and wait for the pod start.
    12. Check the data md5sum for the restored data.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    backupstore_cleanup(client)

    data_path = "/data/test"

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    data_size_in_mb=DATA_SIZE_IN_MB_4,
                                    data_path=data_path)

    volume = client.by_id_volume(volume_name)
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name,
                               retry_count=600)
    bv, b = find_backup(client, volume_name, snap.name)

    res_name = "res-" + volume_name

    client.create_volume(name=res_name, fromBackup=b.url)
    wait_for_volume_condition_restore(client, res_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, res_name,
                                      "reason", "RestoreInProgress")

    # Check if the restore volume is auto reattached then continue
    # restoring data.
    crash_engine_process_with_sigkill(client, core_api, res_name)
    # From https://github.com/longhorn/longhorn/issues/4309#issuecomment-1197897496 # NOQA
    # The complete state transition would be like:
    # detaching -> detached -> attaching -> attached -> restore -> detached .
    # Now the state change too fast, script eventually caught final detach
    # So temporaly comment out below line of code
    # wait_for_volume_detached(client, res_name)

    res_volume = wait_for_volume_healthy_no_frontend(client, res_name)
    assert res_volume.ready is False
    assert res_volume.restoreRequired
    client.list_backupVolume()
    wait_for_volume_condition_restore(client, res_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, res_name,
                                      "reason", "RestoreInProgress")

    wait_for_volume_restoration_completed(client, res_name)
    wait_for_volume_condition_restore(client, res_name,
                                      "status", "False")
    res_volume = wait_for_volume_detached(client, res_name)
    assert res_volume.ready is True

    res_pod_name = res_name + "-pod"
    pv_name = res_name + "-pv"
    pvc_name = res_name + "-pvc"

    create_pv_for_volume(client, core_api, res_volume, pv_name)
    create_pvc_for_volume(client, core_api, res_volume, pvc_name)

    res_pod = pod_make(name=res_pod_name)
    res_pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, res_pod)

    res_volume = client.by_id_volume(res_name)
    assert res_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_HEALTHY

    res_md5sum = get_pod_data_md5sum(core_api, res_pod_name, data_path)
    assert md5sum == res_md5sum

    # cleanup the backupstore so we don't impact other tests
    # since we only crashed the engine and not the replica
    # we don't need to wait for lock expiration, since the replica
    # process will remove the lock
    backupstore_cleanup(client)


def test_engine_crash_for_dr_volume(set_random_backupstore, client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test DR volume can be recovered after
    the engine crashes unexpectedly.

    1. Setup a random backupstore.
    2. Create volume and start the pod.
    3. Write random data to the pod volume and get the md5sum.
    4. Create a backup for the volume.
    5. Create a DR volume from the backup.
    6. Wait for the DR volume init restore complete.
    7. Wait more data to the original volume and get the md5sum
    8. Create the 2nd backup for the original volume.
    9. Wait for the incremental restore triggered
       after the 2nd backup creation.
    10. Crash the DR volume engine process during the incremental restore.
    11. Wait for the DR volume detaching.
    12. Wait for the DR volume reattached.
    13. Verify the DR volume:
      13.1. `volume.ready == false`.
      13.2. `volume.conditions[Restore].status == True &&
            volume.conditions[Restore].reason == "RestoreInProgress"`.
      13.3. `volume.standby == true`
    14. Activate the DR volume and wait for detached.
    15. Create a pod for the restored volume and wait for the pod start.
    16. Check the data md5sum for the DR volume.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    backupstore_cleanup(client)

    data_path = "/data/test"
    pod_name, pv_name, pvc_name, md5sum1 = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    data_size_in_mb=DATA_SIZE_IN_MB_1,
                                    data_path=data_path)
    snap1 = create_snapshot(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, volume_name, snap1.name)
    bv, b1 = find_backup(client, volume_name, snap1.name)

    dr_volume_name = volume_name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_volume_restoration_start(client, dr_volume_name, b1.name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path2, DATA_SIZE_IN_MB_3)
    md5sum2 = get_pod_data_md5sum(core_api, pod_name, data_path2)
    snap2 = create_snapshot(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client,
                               volume_name,
                               snap2.name,
                               retry_count=600)
    bv, b2 = find_backup(client, volume_name, snap2.name)

    # Trigger the inc restore then crash the engine process immediately.
    client.list_backupVolume()
    wait_for_volume_restoration_start(client, dr_volume_name, b2.name)
    crash_engine_process_with_sigkill(client, core_api, dr_volume_name)
    # From https://github.com/longhorn/longhorn/issues/4309#issuecomment-1197897496 # NOQA
    # The complete state transition would be like:
    # detaching -> detached -> attaching -> attached -> restore -> detached .
    # Now the state change too fast, script eventually caught final detach
    # So temporaly comment out below line of code
    # wait_for_volume_detached(client, dr_volume_name)

    # Check if the DR volume is auto reattached then continue
    # restoring data.
    dr_volume = wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    assert dr_volume.ready is False
    assert dr_volume.restoreRequired
    client.list_backupVolume()
    wait_for_volume_condition_restore(client, dr_volume_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, dr_volume_name,
                                      "reason", "RestoreInProgress")
    wait_for_backup_restore_completed(client, dr_volume_name, b2.name)

    activate_standby_volume(client, dr_volume_name)
    wait_for_volume_detached(client, dr_volume_name)
    wait_for_volume_condition_restore(client, dr_volume_name,
                                      "status", "False")
    dr_volume = wait_for_volume_detached(client, dr_volume_name)
    assert dr_volume.ready is True

    dr_pod_name = dr_volume_name + "-pod"
    pv_name = dr_volume_name + "-pv"
    pvc_name = dr_volume_name + "-pvc"

    create_pv_for_volume(client, core_api, dr_volume, pv_name)
    create_pvc_for_volume(client, core_api, dr_volume, pvc_name)

    dr_pod = pod_make(name=dr_pod_name)
    dr_pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, dr_pod)

    dr_volume = client.by_id_volume(dr_volume_name)
    assert dr_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_HEALTHY

    dr_md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path)
    assert md5sum1 == dr_md5sum1
    dr_md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert md5sum2 == dr_md5sum2


def test_volume_reattach_after_engine_sigkill(client, core_api, storage_class, sts_name, statefulset):  # NOQA
    """
    [HA] Test if the volume can be reattached after using SIGKILL
    to crash the engine process

    1. Create StorageClass and StatefulSet.
    2. Write random data to the pod and get the md5sum.
    3. Crash the engine process by SIGKILL in the engine manager.
    4. Wait for volume to `faulted`, then `healthy`.
    5. Wait for K8s to terminate the pod and statefulset to bring pod to
       `Pending`, then `Running`.
    6. Check volume path exist in the pod.
    7. Check md5sum of the data in the pod.
    8. Check new data written to the volume is successful.
    """
    vol_name, pod_name, md5sum = \
        common.prepare_statefulset_with_data_in_mb(
            client, core_api, statefulset, sts_name, storage_class)

    crash_engine_process_with_sigkill(client, core_api, vol_name)

    wait_pod_for_remount_request(client, core_api, vol_name, pod_name, md5sum)

    write_pod_volume_data(core_api, pod_name, 'longhorn-integration-test',
                          filename='test2')
    read_data = read_volume_data(core_api, pod_name, 'test2')

    assert read_data == 'longhorn-integration-test'


def test_rebuild_after_replica_file_crash(client, volume_name): # NOQA
    """
    [HA] Test replica rebuild should be triggered if any crashes happened.

    1. Create a longhorn volume with replicas.
    2. Write random data to the volume and get the md5sum.
    3. Remove file `volume-head-000.img` from one of the replicas.
    4. Wait replica rebuild to be triggered.
    5. Verify the old replica containing the crashed file will be reused.
    6. Read the data from the volume and verify the md5sum.
    """
    replica_count = 3
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=replica_count)
    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    data = write_volume_random_data(volume)

    replica = None
    for rep in volume.replicas:
        if rep["hostId"] == host_id:
            replica = rep
            break
    assert replica is not None

    volume_head_file_path = replica["dataPath"] + "/volume-head-000.img"

    exec_cmd = ["rm", volume_head_file_path]

    try:
        subprocess.check_output(exec_cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)

    wait_for_volume_degraded(client, volume_name)
    wait_for_rebuild_complete(client, volume_name)
    wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    reused_replica = None
    for rep in volume.replicas:
        if rep["name"] == replica["name"]:
            reused_replica = rep
            break

    assert reused_replica["running"] is True
    assert reused_replica["mode"] == "RW"
    assert not reused_replica["failedAt"]

    check_volume_data(volume, data)


def test_extra_replica_cleanup(client, volume_name, settings_reset): # NOQA
    """
    Test extra failed to scheduled replica cleanup
    when no eviction requested

    1. Make sure 'Replica Node Level Soft Anti-Affinity' is disabled.
    2. Create a volume with 3 replicas.
    3. Attach the volume to a node and write some data to it and
    save the checksum.
    4. Increase the volume replica number to 4.
    5. Volume should show failed to schedule and an extra stop replica.
    6. Decrease the volume replica nubmer to 3.
    7. Volume should show healthy and the extra failed to scheduled replica
    should be removed.
    8. Check the data in the volume and make sure it's same as the chechsum.
    """
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

    host_id = get_self_host_id()
    volume = create_and_check_volume(client, volume_name, num_of_replicas=3)

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    data = write_volume_random_data(volume)
    volume = volume.updateReplicaCount(replicaCount=4)
    wait_for_volume_replica_count(client, volume_name, 4)

    volume = client.by_id_volume(volume_name)

    err_replica = None
    for replica in volume.replicas:
        if replica.running is False:
            err_replica = replica
            break

    assert err_replica is not None
    assert err_replica.running is False
    assert err_replica.mode == ""

    volume = volume.updateReplicaCount(replicaCount=3)
    wait_for_volume_replica_count(client, volume_name, 3)

    volume = client.by_id_volume(volume_name)
    wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)


def test_disable_replica_rebuild(client, volume_name):  # NOQA
    """
    Test disable replica rebuild

    1. Disable node scheduling on node-2 and node-3. To make sure
    replica scheduled on node-1.
    2. Set 'Concurrent Replica Rebuild Per Node Limit' to 0.
    3. Create a volume with 1 replica and attach it to node-1.
    4. Enable scheduling on node-2 and node-3. Set node-1 scheduling to
    'Disable' and 'Enable' eviction on node-1.
    5. Wait for 30 seconds, and check no eviction happen.
    6. 'Enable' node-1 scheduling and 'Disable' node-1 eviction.
    7. Detach the volume and update data locality to 'best-effort'.
    8. Attach the volume to node-2, and wait for 30 seconds, and check
    no data locality happen.
    9. Detach the volume and update data locality to 'disable'.
    10. Attach the volume to node-2 and update the replica number to 2.
    11. Wait for 30 seconds, and no new replica scheduled and volume is
    at 'degraded' state.
    12. Set 'Concurrent Replica Rebuild Per Node Limit' to 5, and wait for
    replica rebuild and volume becomes 'healthy' state with 2 replicas.
    13. Set 'Concurrent Replica Rebuild Per Node Limit' to 0, delete one
    replica.
    14. Wait for 30 seconds, no rebuild should get triggered. The volume
    should stay in 'degraded' state with 1 replica.
    15. Set 'Concurrent Replica Rebuild Per Node Limit' to 5, and wait for
    replica rebuild and volume becomes 'healthy' state with 2 replicas.
    16. Clean up the volume.
    """
    # Step1
    node_1, node_2, node_3 = client.list_node()
    client.update(node_2, allowScheduling=False)
    client.update(node_3, allowScheduling=False)

    # Step2
    concurrent_replica_rebuild_per_node_limit = \
        client.by_id_setting("concurrent-replica-rebuild-per-node-limit")

    client.update(concurrent_replica_rebuild_per_node_limit, value="0")

    # Step3
    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=1)
    volume = wait_for_volume_detached(client, volume_name)
    volume = volume.attach(hostId=node_1.name)
    volume = wait_for_volume_healthy(client, volume_name)

    # Step4
    client.update(node_1, allowScheduling=False)
    client.update(node_1, evictionRequested=True)
    client.update(node_2, allowScheduling=True)
    client.update(node_3, allowScheduling=True)

    # Step5
    for _ in range(RETRY_EXEC_COUNTS):
        node1_r_cnt = common.get_host_replica_count(
            client, volume_name, node_1.name, chk_running=True)

        assert node1_r_cnt == 1
        time.sleep(RETRY_INTERVAL_LONG)

    # Step6
    client.update(node_1, evictionRequested=False)
    client.update(node_1, allowScheduling=True)

    # Step7
    volume = wait_for_volume_healthy(client, volume_name)
    volume.detach(hostId=node_1.name)
    volume = wait_for_volume_detached(client, volume_name)
    volume.updateDataLocality(dataLocality="best-effort")

    # Step8
    volume = volume.attach(hostId=node_2.name)
    for _ in range(RETRY_EXEC_COUNTS):
        node2_r_cnt = common.get_host_replica_count(
            client, volume_name, node_2.name, chk_running=True)

        assert node2_r_cnt == 0
        time.sleep(RETRY_INTERVAL_LONG)

    # Step9
    volume.detach(hostId=node_2.name)
    volume = wait_for_volume_detached(client, volume_name)
    volume.updateDataLocality(dataLocality="disabled")

    # Step10
    volume = volume.attach(hostId=node_2.name)
    volume = wait_for_volume_healthy(client, volume_name)
    volume.updateReplicaCount(replicaCount=2)

    # Step11
    for _ in range(RETRY_EXEC_COUNTS):
        assert get_volume_running_replica_cnt(client, volume_name) == 1
        time.sleep(RETRY_INTERVAL_LONG)

    # Step12
    client.update(concurrent_replica_rebuild_per_node_limit, value="5")
    volume = wait_for_volume_healthy(client, volume_name)
    assert get_volume_running_replica_cnt(client, volume_name) == 2

    # Step13
    client.update(concurrent_replica_rebuild_per_node_limit, value="0")
    host_replica = get_host_replica(volume, host_id=node_1.name)
    volume.replicaRemove(name=host_replica.name)
    for _ in range(RETRY_EXEC_COUNTS):
        if get_volume_running_replica_cnt(client, volume_name) == 1:
            break
        time.sleep(RETRY_INTERVAL_LONG)

    # Step14
    for _ in range(RETRY_EXEC_COUNTS):
        assert get_volume_running_replica_cnt(client, volume_name) == 1
        time.sleep(RETRY_INTERVAL_LONG)

    # Step15
    client.update(concurrent_replica_rebuild_per_node_limit, value="5")
    volume = wait_for_volume_healthy(client, volume_name)
    assert get_volume_running_replica_cnt(client, volume_name) == 2


def test_auto_remount_with_subpath(client, core_api, storage_class, sts_name, statefulset):  # NOQA
    """
    Test Auto Remount With Subpath

    Context:

    Instead of manually finding and remounting all mount points of the volume,
    we delete the workload pod so that Kubernetes handles those works.
    This new implementation also solves the issue that remount doesn't
    support subpath (e.g. when pod use subpath in PVC).
    longhorn/longhorn#1719

    Steps:

    1. Deploy a storage class with parameter `numberOfReplicas: 1`
    2. Deploy a statefulset with `replicas: 1` and using the above storageclass
       Make sure the container in the pod template uses subpath, like this:
       ```yaml
       volumeMounts:
       - name: <PVC-NAME>
         mountPath: /data/sub
         subPath: sub
       ```
    3. exec into statefulset pod, create a file `test_data.txt`
       inside the folder `/data/sub`
    4. Delete the statefulset replica instance manager pod.
       This action simulates a network disconnection.
    5. Wait for volume `healthy`, then verify the file checksum.
    6. Repeat step #4~#5 for 3 times.
    7. Update `numberOfReplicas` to 3.
    8. Wait for replicas rebuilding finishes.
    9. Delete one of the statefulset engine instance manager pod.
    10. Wait for volume remount.
        Then verify the file checksum.
    11. Delete statefulset pod.
    12. Wait for pod recreation and volume remount.
        Then verify the file checksum.
    """
    storage_class['parameters']['numberOfReplicas'] = "1"

    statefulset['spec']['replicas'] = 1
    statefulset['spec']['selector']['matchLabels']['name'] = sts_name
    statefulset['spec']['template']['metadata']['labels']['name'] = sts_name
    statefulset['spec']['template']['spec']['containers'] = \
        [{
            'image': 'busybox:1.34.0',
            'imagePullPolicy': 'IfNotPresent',
            'name': 'sleep',
            'args': [
                '/bin/sh',
                '-c',
                'while true;do date;sleep 5; done'
            ],
            'volumeMounts': [{
                'name': 'pod-data',
                'mountPath': '/data/sub',
                'subPath': 'sub'
            }]
        }]

    data_path = "/data/sub/test_data.txt"
    vol_name, pod_name, md5sum = \
        common.prepare_statefulset_with_data_in_mb(
            client, core_api, statefulset, sts_name, storage_class,
            data_path=data_path)

    crash_count = 3
    for _ in range(crash_count):
        vol = client.by_id_volume(vol_name)
        rim_name = vol.replicas[0].instanceManagerName
        delete_and_wait_pod(core_api, rim_name,
                            namespace='longhorn-system',
                            wait=True)
        wait_for_volume_healthy(client, vol_name)
        common.wait_and_get_any_deployment_pod(core_api, sts_name)
        expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
        assert expect_md5sum == md5sum

    vol = client.by_id_volume(vol_name)
    vol.updateReplicaCount(replicaCount=3)
    wait_for_volume_replica_count(client, vol_name, 3)
    vol = wait_for_volume_healthy(client, vol_name)

    eim_name = vol.controllers[0].instanceManagerName
    delete_and_wait_pod(core_api, eim_name,
                        namespace='longhorn-system',
                        wait=True)
    wait_for_volume_healthy(client, vol_name)
    common.wait_and_get_any_deployment_pod(core_api, sts_name)
    expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert expect_md5sum == md5sum

    delete_and_wait_pod(core_api, pod_name, wait=True)
    common.wait_and_get_any_deployment_pod(core_api, sts_name)
    expect_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert expect_md5sum == md5sum


def test_reuse_failed_replica(client, core_api, volume_name): # NOQA
    """
    Steps:
    1. Set a long wait interval for
       setting `replica-replenishment-wait-interval`.
    2. Disable the setting soft node anti-affinity.
    3. Create and attach a volume. Then write data to the volume.
    4. Disable the scheduling for a node.
    5. Mess up the data of a random snapshot or the volume head for a replica.
       Then crash the replica on the node.
       --> Verify Longhorn won't create a new replica on the node
           for the volume.
    6. Update setting `replica-replenishment-wait-interval` to
       a small value.
    7. Verify Longhorn starts to create a new replica for the volume.
       Notice that the new replica scheduling will fail.
    8. Update setting `replica-replenishment-wait-interval` to
       a large value.
    9. Delete the newly created replica.
       --> Verify Longhorn won't create a new replica on the node
           for the volume.
    10. Enable the scheduling for the node.
    11. Verify the failed replica (in step 5) will be reused.
    12. Verify the volume r/w still works fine.
    """
    long_wait = 60*60
    short_wait = 3

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value=str(long_wait))

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    vol = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    vol = vol.attach(hostId=host_id)
    vol = wait_for_volume_healthy(client, volume_name)
    data = {
        'pos': 0,
        'content': generate_random_data(16*Ki),
    }
    common.write_volume_data(vol, data)

    current_host = client.by_id_node(id=host_id)
    client.update(current_host, allowScheduling=False)

    vol = client.by_id_volume(volume_name)
    assert len(vol.replicas) == 3
    other_replicas = []
    for r in vol.replicas:
        if r["hostId"] == current_host.name:
            replica_1 = r
        else:
            other_replicas.append(r)
    replica_2, replica_3 = other_replicas

    for filenames in os.listdir(replica_1.dataPath):
        if filenames.endswith(".img"):
            with open(os.path.join(replica_1.dataPath, filenames), 'w') as f:
                f.write("Longhorn is the best!")

    crash_replica_processes(client, core_api, volume_name,
                            replicas=[replica_1],
                            wait_to_fail=False)

    # We need to wait for a minute to very that
    # Longhorn doesn't create a new replica
    for i in range(SMALL_RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        current_replica_names = set([r.name for r in vol.replicas])
        assert current_replica_names == \
               {replica_1.name, replica_2.name, replica_3.name}
        time.sleep(RETRY_INTERVAL_LONG)

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value=str(short_wait))

    new_replica = None
    for i in range(RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        for r in vol.replicas:
            if r.name not in {replica_1.name, replica_2.name, replica_3.name}:
                new_replica = r
        if new_replica is not None:
            break
        time.sleep(RETRY_INTERVAL)
    assert new_replica is not None
    assert new_replica.hostId == ""

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value=str(long_wait))

    vol = client.by_id_volume(volume_name)
    vol.replicaRemove(name=new_replica.name)
    # Removing replica doesn't take effect immediately
    # Wait for Longhorn to finish removing it before process
    for i in range(RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        if len(vol.replicas) == 3:
            break
        time.sleep(RETRY_INTERVAL)
    current_replica_names = set([r.name for r in vol.replicas])
    assert current_replica_names == \
           {replica_1.name, replica_2.name, replica_3.name}

    current_host = client.by_id_node(id=host_id)
    client.update(current_host, allowScheduling=True)

    vol = wait_for_volume_healthy(client, volume_name)
    current_replica_names = set([r.name for r in vol.replicas])
    assert current_replica_names == \
           {replica_1.name, replica_2.name, replica_3.name}
    data = common.write_volume_data(vol, data)
    check_volume_data(vol, data)


def set_tags_for_node_and_its_disks(client, node, tags): # NOQA
    if len(tags) == 0:
        expected_tags = []
    else:
        expected_tags = list(tags)

    for disk_name in node.disks.keys():
        node.disks[disk_name].tags = tags
    node = update_node_disks(client, node.name, disks=node.disks)
    for disk_name in node.disks.keys():
        assert node.disks[disk_name].tags == expected_tags

    node = set_node_tags(client, node, tags)
    assert node.tags == expected_tags

    return node


def test_reuse_failed_replica_with_scheduling_check(client, core_api, volume_name): # NOQA
    """
    Steps:
    1. Set a long wait interval for
       setting `replica-replenishment-wait-interval`.
    2. Disable the setting soft node anti-affinity.
    3. Add tags for all nodes and disks.
    4. Create and attach a volume with node and disk selectors.
       Then write data to the volume.
    5. Disable the scheduling for the 2 nodes (node1 and node2).
    6. Crash the replicas on the node1 and node2.
       --> Verify Longhorn won't create new replicas on the nodes.
    7. Remove tags for node1 and the related disks.
    8. Enable the scheduling for node1 and node2.
    9. Verify the only failed replica on node2 is reused.
    10. Add the tags back for node1 and the related disks.
    11. Verify the failed replica on node1 is reused.
    12. Verify the volume r/w still works fine.
    """
    long_wait = 60*60
    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value=str(long_wait))

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    nodes = client.list_node()
    tags = ["avail"]
    for node in nodes:
        set_tags_for_node_and_its_disks(client, node, tags)

    client.create_volume(name=volume_name, size=SIZE, numberOfReplicas=3,
                         diskSelector=tags, nodeSelector=tags)
    vol = wait_for_volume_detached(client, volume_name)
    assert vol.diskSelector == tags
    assert vol.nodeSelector == tags
    vol.attach(hostId=get_self_host_id())
    vol = wait_for_volume_healthy(client, volume_name)
    data = {
        'pos': 0,
        'content': generate_random_data(16*Ki),
    }
    common.write_volume_data(vol, data)

    nodes = client.list_node()
    assert len(nodes) == 3
    node_1, node_2, node_3 = nodes
    set_node_scheduling(client, node_1, allowScheduling=False)
    set_node_scheduling(client, node_2, allowScheduling=False)

    vol = client.by_id_volume(volume_name)
    replica_1, replica_2, replica_3 = None, None, None
    for r in vol.replicas:
        if r.hostId == node_1.name:
            replica_1 = r
        elif r.hostId == node_2.name:
            replica_2 = r
        elif r.hostId == node_3.name:
            replica_3 = r
    assert replica_1 is not None and \
           replica_2 is not None and \
           replica_3 is not None

    crash_replica_processes(client, core_api,
                            volume_name,
                            replicas=[replica_1, replica_2],
                            wait_to_fail=False)

    # We need to wait for a minute to very that
    # Longhorn doesn't create a new replica
    for i in range(SMALL_RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        current_replica_names = set([r.name for r in vol.replicas])
        assert current_replica_names == \
               {replica_1.name, replica_2.name, replica_3.name}
        time.sleep(RETRY_INTERVAL_LONG)

    node_1 = set_tags_for_node_and_its_disks(client, node_1, [])

    set_node_scheduling(client, node_1, allowScheduling=True)
    set_node_scheduling(client, node_2, allowScheduling=True)

    # Wait for rebuilding to finish
    # It should take less than 1 minute since the replica is small
    time.sleep(60)

    vol = client.by_id_volume(volume_name)
    for r in vol.replicas:
        if r.name == replica_1.name:
            assert r.failedAt != "" and r.running is False
        else:
            assert r.failedAt == "" and r.running is True

    node_1 = set_tags_for_node_and_its_disks(client, node_1, tags)

    vol = wait_for_volume_healthy(client, volume_name)
    current_replica_names = set([r.name for r in vol.replicas])
    assert current_replica_names == \
           {replica_1.name, replica_2.name, replica_3.name}
    data = common.write_volume_data(vol, data)
    check_volume_data(vol, data)


def test_replica_failure_during_attaching(settings_reset, client, core_api, volume_name):  # NOQA
    """
    Steps:
    1. Set a short interval for setting replica-replenishment-wait-interval.
    2. Disable the setting soft-node-anti-affinity.
    3. Create volume1 with 1 replica. and attach it to the host node.
    4. Mount volume1 to a new mount point. then use it as an extra node disk.
    5. Disable the scheduling for the default disk of the host node,
       and make sure the extra disk is the only available disk on the node.
    6. Create and attach volume2, then write data to volume2.
    7. Detach volume2.
    8. Directly unmount volume1 and remove the related mount point directory.
       --> Verify the extra disk becomes unavailable.
    9. Attach volume2.
       --> Verify volume will be attached with state Degraded.
    10. Wait for the replenishment interval.
        --> Verify a new replica will be created but it cannot be scheduled.
    11. Enable the default disk for the host node.
    12. Wait for volume2 becoming Healthy.
    13. Verify data content and r/w capability for volume2.
    """

    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value='10')

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    volume_name_1 = volume_name
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)

    extra_disk_path = create_host_disk(client, volume_name_1, str(3 * Gi),
                                       host_id)
    extra_disk = {"path": extra_disk_path, "allowScheduling": True}

    update_disks = get_update_disks(node.disks)
    default_disk_name = next(iter(update_disks))
    update_disks["extra-disk"] = extra_disk
    update_disks[default_disk_name].allowScheduling = False

    node = update_node_disks(client, node.name, disks=update_disks)
    node = common.wait_for_disk_update(client, node.name, len(update_disks))

    volume_name_2 = volume_name + '-2'
    volume_2 = create_and_check_volume(client, volume_name_2,
                                       num_of_replicas=3,
                                       size=str(1 * Gi))
    volume_2.attach(hostId=host_id)
    volume_2 = wait_for_volume_healthy(client, volume_name_2)
    write_volume_random_data(volume_2)
    volume_2.detach()
    wait_for_volume_detached(client, volume_name_2)

    # unmount the disk
    mount_path = os.path.join(DIRECTORY_PATH, volume_name_1)
    common.umount_disk(mount_path)
    cmd = ['rm', '-r', mount_path]
    subprocess.check_call(cmd)

    volume_2 = client.by_id_volume(volume_name_2)
    volume_2.attach(hostId=host_id)
    common.wait_for_volume_status(client, volume_name_2,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_DEGRADED)

    time.sleep(10)
    wait_for_volume_replica_count(client, volume_name_2, 4)
    common.wait_for_volume_condition_scheduled(client, volume_name_2,
                                               "status", "False")
    volume_2 = client.by_id_volume(volume_name_2)
    assert volume_2.conditions.Scheduled.reason == "ReplicaSchedulingFailure"

    update_disks[default_disk_name].allowScheduling = True
    update_disks["extra-disk"]["allowScheduling"] = False

    node = update_node_disks(client, node.name, disks=update_disks)
    common.wait_for_disk_update(client, node.name, len(update_disks))

    common.wait_for_volume_status(client, volume_name_2,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_HEALTHY)

    volume_2 = client.by_id_volume(volume_name_2)
    write_volume_random_data(volume_2)

    del update_disks["extra-disk"]
    update_node_disks(client, node.name, disks=update_disks)
    common.wait_for_disk_update(client, node.name, 1)


def prepare_upgrade_image_not_fully_deployed_environment(client, excluded_nodes=[]): # NOQA
    # deploy upgrade image, wait until 2 running pods because 1 node tainted
    default_img = common.get_default_engine_image(client)
    default_img = client.by_id_engine_image(default_img.name)

    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion

    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    new_img = client.create_engine_image(image=engine_upgrade_image)
    wait_for_deployed_engine_image_count(client, new_img.name, 2,
                                         excluded_nodes)
    new_img = client.by_id_engine_image(new_img.name)

    return engine_upgrade_image, new_img


def prepare_engine_not_fully_deployed_environment(client, core_api): # NOQA
    """
    1. Taint node-1 with the taint: key=value:NoSchedule
    2. Delete the pod on node-1 of the engine image DaemonSet.
       Or delete the engine image DaemonSet and wait for Longhorn
       to automatically recreates it.
    3. Wait for the engine image CR state become deploying
    """

    taint_node_id = taint_non_current_node(client, core_api)

    restart_and_wait_ready_engine_count(client, 2)

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    # check if tainted node is marked as not deployed in `nodeDeploymentMap`.
    wait_for_tainted_node_engine_image_undeployed(client,
                                                  default_img_name,
                                                  taint_node_id)

    wait_for_deployed_engine_image_count(client, default_img_name, 2,
                                         [taint_node_id])

    return taint_node_id


def prepare_engine_not_fully_deployed_environment_with_volumes(client, core_api): # NOQA
    """
    1. Create 2 volumes, vol-1 and vol-2 with 3 replicas
    2. Taint node-1 with the taint: key=value:NoSchedule
    3. Attach vol-1 to node-1. Change the number of replicas of vol-1
       to 2. Delete the replica on node-1
    4. Delete the pod on node-1 of the engine image DaemonSet.
       Or delete the engine image DaemonSet and wait for Longhorn
       to automatically recreates it.
    5. Wait for the engine image CR state become deploying
    """

    volume1 = create_and_check_volume(client, "vol-1", size=str(3 * Gi))
    volume2 = create_and_check_volume(client, "vol-2", size=str(3 * Gi))

    taint_node_id = taint_non_current_node(client, core_api)

    volume1.attach(hostId=taint_node_id)
    volume1 = wait_for_volume_healthy(client, volume1.name)
    volume1.updateReplicaCount(replicaCount=2)

    for r in volume1.replicas:
        if r.hostId == taint_node_id:
            volume1.replicaRemove(name=r.name)
            break

    restart_and_wait_ready_engine_count(client, 2)

    volume1 = client.by_id_volume(volume1.name)
    volume2 = client.by_id_volume(volume2.name)

    return volume1, volume2, taint_node_id


def test_engine_image_miss_scheduled_perform_volume_operations(core_api, client, set_random_backupstore, volume_name): # NOQA
    """
    Test volume operations when engine image DaemonSet is miss
    scheduled

    1. Create a volume, vol-1, of 3 replicas
    2. Taint node-1 with the taint: key=value:NoSchedule
    3. Verify that we can attach, take snapshot, take a backup,
       expand, then detach vol-1
    """
    volume = create_and_check_volume(client, volume_name, size=str(3 * Gi))

    nodes = client.list_node()
    core_api.patch_node(nodes[0].id, {
        "spec": {
            "taints":
                [{"effect": "NoSchedule",
                  "key": "key",
                  "value": "value"}]
        }
    })

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    snap1_data = write_volume_random_data(volume)
    snap1 = create_snapshot(client, volume_name)

    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap1.name].name == snap1.name
    assert snapMap[snap1.name].removed is False

    backupstore_test(client, host_id, volume_name, size=str(3 * Gi),
                     compression_method=DEFAULT_BACKUP_COMPRESSION_METHOD)

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=host_id, disableFrontend=False)
    wait_for_volume_healthy(client, volume_name)

    expand_size = str(4 * Gi)
    volume.expand(size=expand_size)
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.size == expand_size
    check_block_device_size(volume, int(expand_size))
    check_volume_data(volume, snap1_data, False)


def test_engine_image_not_fully_deployed_perform_volume_operations(client, core_api, set_random_backupstore): # NOQA
    """
    Test volume operations when engine image DaemonSet is not fully
    deployed

    Prerequisite:
    Prepare system for the test by calling the method
    prepare_engine_not_fully_deployed_evnironment_with_volumes to have
    2 volumes, tainted node and not fully deployed engine.

    1. Verify that functions (snapshot, backup, detach) are working ok
       for vol-1
    2. Detach vol-1
    3. Attach vol-1 to node-1. Verify that Longhorn cannot attach vol-1 to
       node-1 since there is no engine image on node-1. The attach API call
       returns error
    4. Verify that we can attach to another node, take snapshot, take a backup,
       expand, then detach vol-1
    5. Verify that vol-2 cannot be attached to tainted nodes. The attach API
       call returns error
    6. Verify that vol-2 can attach to non-tainted node with degrade status
    """
    volume1, volume2, tainted_node_id = \
        prepare_engine_not_fully_deployed_environment_with_volumes(client,
                                                                   core_api)

    volume1 = client.by_id_volume(volume1.name)
    volume1 = wait_for_volume_healthy(client, volume1.name)

    # TODO: write data into volume1.
    # Did not do data write because volume is not attached to self host node

    # High chance get error "cannot get engine client" first time take snapshot
    for i in range(RETRY_COUNTS_SHORT):
        try:
            snap1 = create_snapshot(client, volume1.name)
            break
        except Exception:
            time.sleep(RETRY_INTERVAL_LONG)
            continue

    snapshots = volume1.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap1.name].name == snap1.name

    volume1.detach()
    volume1 = wait_for_volume_detached(client, volume1.name)

    can_not_attach = False
    try:
        volume1.attach(hostId=tainted_node_id)
    except Exception as e:
        print(e)
        can_not_attach = True

    assert can_not_attach

    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1.name)
    snap2_data = write_volume_random_data(volume1)
    snap2 = create_snapshot(client, volume1.name)
    snapshots = volume1.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    assert snapMap[snap2.name].name == snap2.name
    check_volume_data(volume1, snap2_data)

    backupstore_test(client, get_self_host_id(), volume1.name,
                     size=str(3 * Gi),
                     compression_method=DEFAULT_BACKUP_COMPRESSION_METHOD)

    expand_size = str(4 * Gi)
    volume1.expand(size=expand_size)
    wait_for_volume_expansion(client, volume1.name)
    volume1 = client.by_id_volume(volume1.name)
    assert volume1.size == expand_size
    check_block_device_size(volume1, int(expand_size))
    check_volume_data(volume1, snap2_data, False)

    can_not_attach = False
    try:
        volume2 = client.by_id_volume(volume2.name)
        volume2.attach(hostId=tainted_node_id)
    except Exception as e:
        print(e)
        can_not_attach = True

    assert can_not_attach

    volume2.attach(hostId=get_self_host_id())
    volume2 = wait_for_volume_degraded(client, volume2.name)


def test_engine_image_not_fully_deployed_perform_engine_upgrade(client, core_api): # NOQA
    """
    Test engine upgrade when engine image DaemonSet is not fully
    deployed

    Prerequisite:
    Prepare system for the test by calling the method
    prepare_engine_not_fully_deployed_evnironment_with_volumes to have
    2 volumes, tainted node and not fully deployed engine.

    1. Deploy a new engine image, new-ei
    2. Detach vol-1, verify that you can upgrade vol-1 to new-ei
    3. Detach then attach vol-1 to node-2
    4. Verify that you can live upgrade vol-1 to back to default engine image
    5. Try to upgrade vol-2 to new-ei
    6. Verify that the engineUpgrade API call returns error
    """
    volume1, volume2, tainted_node_id = \
        prepare_engine_not_fully_deployed_environment_with_volumes(client,
                                                                   core_api)

    volume1.detach()
    volume1 = wait_for_volume_detached(client, volume1.name)

    engine_upgrade_image, new_img = \
        prepare_upgrade_image_not_fully_deployed_environment(client,
                                                             [tainted_node_id])

    # expected refCount: 1 for volume + 1 for engine and number of replicas(2)
    expect_ref_count = 4
    new_img_name = new_img.name
    original_engine_image = volume1.image
    volume1.engineUpgrade(image=engine_upgrade_image)
    volume1 = wait_for_volume_current_image(client, volume1.name,
                                            engine_upgrade_image)
    new_img = wait_for_engine_image_ref_count(client,
                                              new_img_name,
                                              expect_ref_count)

    host_id = get_self_host_id()
    volume1.attach(hostId=host_id)
    volume1 = wait_for_volume_healthy(client, volume1.name)

    volume1.engineUpgrade(image=original_engine_image)
    volume1 = wait_for_volume_current_image(client, volume1.name,
                                            original_engine_image)

    new_img = wait_for_engine_image_ref_count(client,
                                              new_img_name,
                                              0)

    can_not_upgrade = False
    volume2 = client.by_id_volume(volume2.name)
    try:
        volume2.engineUpgrade(image=engine_upgrade_image)
    except Exception as e:
        can_not_upgrade = True
        print(e)
    assert can_not_upgrade


def test_engine_image_not_fully_deployed_perform_replica_scheduling(client, core_api): # NOQA
    """
    Test replicas scheduling when engine image DaemonSet is not fully
    deployed

    Prerequisite:
    Prepare system for the test by calling the method
    prepare_engine_not_fully_deployed_evnironment to have
    tainted node and not fully deployed engine.

    1. Disable the scheduling for node-2
    2. Create a volume, vol-1, with 2 replicas, attach to node-3
    3. Verify that there is one replica fail to be scheduled
    4. enable the scheduling for node-2
    5. Verify that replicas are scheduled onto node-2 and node-3
    """
    tainted_node_id = \
        prepare_engine_not_fully_deployed_environment(client, core_api)

    # node1: tainted node, node2: self host node, node3: the last one
    nodes = client.list_node()
    for node in nodes:
        if node.id == get_self_host_id():
            node2 = node
        elif node.id != tainted_node_id and node.id != get_self_host_id:
            node3 = node

    node2 = set_node_scheduling(client, node2, allowScheduling=False)
    node2 = common.wait_for_node_update(client, node2.id, "allowScheduling",
                                        False)

    volume1 = create_and_check_volume(client, "vol-1",
                                      num_of_replicas=2,
                                      size=str(3 * Gi))

    volume1.attach(hostId=node3.id)
    volume1 = wait_for_volume_degraded(client, volume1.name)

    node2 = set_node_scheduling(client, node2, allowScheduling=True)
    node2 = common.wait_for_node_update(client, node2.id,
                                        "allowScheduling", True)

    volume1 = wait_for_volume_healthy(client, volume1.name)
    on_node2 = False
    on_node3 = False
    on_taint_node = False
    for replica in volume1.replicas:
        if replica.hostId == node2.id:
            on_node2 = True
        elif replica.hostId == node3.id:
            on_node3 = True
        elif replica.hostId == tainted_node_id:
            on_taint_node = True

    assert on_node2
    assert on_node3
    assert not on_taint_node


def test_engine_image_not_fully_deployed_perform_auto_upgrade_engine(client, core_api): # NOQA
    """
    Test auto upgrade engine feature when engine image DaemonSet is
    not fully deployed

    Prerequisite:
    Prepare system for the test by calling the method
    prepare_engine_not_fully_deployed_evnironment to have
    tainted node and not fully deployed engine.

    1. Create 2 volumes vol-1 and vol-2 with 2 replicas
    2. Attach both volumes to make sure they are healthy and have 2 replicas
    4. Detach both volumes
    5. Deploy a new engine image, new-ei
    6. Upgrade vol-1 and vol-2 to the new-ei
    7. Attach vol-2 to current-node
    8. Set `Concurrent Automatic Engine Upgrade Per Node Limit` setting to 3
    9. In a 2-min retry, verify that Longhorn upgrades the engine image of
       vol-1 and vol-2.
    """
    tainted_node_id = \
        prepare_engine_not_fully_deployed_environment(client, core_api)

    volume1 = create_and_check_volume(client, "vol-1",
                                      num_of_replicas=2,
                                      size=str(3 * Gi))

    volume2 = create_and_check_volume(client, "vol-2",
                                      num_of_replicas=2,
                                      size=str(3 * Gi))

    volume1.attach(hostId=get_self_host_id())
    volume2.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1.name)
    volume2 = wait_for_volume_healthy(client, volume2.name)
    wait_for_replica_count(client, volume1.name, 2)
    wait_for_replica_count(client, volume2.name, 2)

    volume1.detach()
    volume2.detach()
    volume1 = wait_for_volume_detached(client, volume1.name)
    volume2 = wait_for_volume_detached(client, volume2.name)

    default_img = common.get_default_engine_image(client)
    # engine reference =
    # (1 volume + 1 engine + number of replicas) * volume count
    wait_for_engine_image_ref_count(client, default_img.name, 8)

    engine_upgrade_image, new_img = \
        prepare_upgrade_image_not_fully_deployed_environment(client,
                                                             [tainted_node_id])

    volume1.engineUpgrade(image=engine_upgrade_image)
    volume2.engineUpgrade(image=engine_upgrade_image)
    volume1 = wait_for_volume_current_image(client, volume1.name,
                                            engine_upgrade_image)
    volume2 = wait_for_volume_current_image(client, volume2.name,
                                            engine_upgrade_image)

    default_img = common.get_default_engine_image(client)
    wait_for_engine_image_ref_count(client, default_img.name, 0)

    volume2.attach(hostId=get_self_host_id())
    volume2 = wait_for_volume_healthy(client, volume2.name)

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    wait_for_engine_image_ref_count(client, new_img.name, 0)
    wait_for_volume_healthy(client, volume2.name)

    volume1 = client.by_id_volume(volume1.name)
    volume2 = client.by_id_volume(volume2.name)
    assert volume1.image == default_img.image
    assert volume2.image == default_img.image


def test_engine_image_not_fully_deployed_perform_dr_restoring_expanding_volume(client, core_api, set_random_backupstore): # NOQA
    """
    Test DR, restoring, expanding volumes when engine image DaemonSet
    is not fully deployed

    Prerequisite:
    Prepare system for the test by calling the method
    prepare_engine_not_fully_deployed_evnironment to have
    tainted node and not fully deployed engine.

    1. Create volume vol-1 with 2 replicas
    2. Attach vol-1 to node-2, write data and create backup
    3. Create a DR volume (vol-dr) of 2 replicas.
    4. Verify that 2 replicas are on node-2 and node-3 and the DR volume
       is attached to either node-2 or node-3.
       Let's say it is attached to node-x
    5. Taint node-x with the taint `key=value:NoSchedule`
    6. Delete the pod of engine image DeamonSet on node-x. Now, the engine
       image is missing on node-1 and node-x
    7. Verify that vol-dr is auto-attached node-y.
    8. Restore a volume from backupstore with name vol-rs and replica count
       is 1
    9. Verify that replica is on node-y and the volume successfully restored.
    10. Wait for vol-rs to finish restoring
    11. Expand vol-rs.
    12. Verify that the expansion is ok
    13. Set `Replica Replenishment Wait Interval` setting to 600
    14. Crash the replica of vol-1 on node-x. Wait for the replica to fail
    15. In a 2-min retry verify that Longhorn doesn't create new replica
       for vol-1 and doesn't reuse the failed replica on node-x
    """
    update_setting(client, common.SETTING_DEGRADED_AVAILABILITY, "false")

    tainted_node_id = \
        prepare_engine_not_fully_deployed_environment(client, core_api)

    # step 1
    volume1 = create_and_check_volume(client, "vol-1",
                                      num_of_replicas=2,
                                      size=str(1 * Gi))

    # node1: tainted node, node2: self host node, node3: the last one
    nodes = client.list_node()
    for node in nodes:
        if node.id == get_self_host_id():
            node2 = node
        elif node.id != tainted_node_id and node.id != get_self_host_id:
            node3 = node

    # step 2
    volume1 = volume1.attach(hostId=node2.id)
    volume1 = wait_for_volume_healthy(client, volume1.name)

    volume_endpoint = get_volume_endpoint(volume1)
    snap1_offset = 1
    snap_data_size_in_mb = 4
    write_volume_dev_random_mb_data(volume_endpoint,
                                    snap1_offset, snap_data_size_in_mb)

    snap = create_snapshot(client, volume1.name)
    volume1.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client,
                               volume1.name,
                               snap.name,
                               retry_count=600)
    bv, b1 = find_backup(client, volume1.name, snap.name)

    dr_volume_name = volume1.name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(1 * Gi),
                         numberOfReplicas=2, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)
    dr_volume = client.by_id_volume(dr_volume_name)

    # step 4
    on_node2 = False
    on_node3 = False
    for replica in dr_volume.replicas:
        if replica.hostId == node2.id:
            on_node2 = True
        if replica.hostId == node3.id:
            on_node3 = True

    assert on_node2
    assert on_node3

    # step 5
    node_x = dr_volume.controllers[0].hostId
    core_api.patch_node(
        node_x, {
            "spec": {
                "taints":
                    [{"effect": "NoSchedule",
                        "key": "key",
                        "value": "value"}]
            }
        })

    # step 6
    restart_and_wait_ready_engine_count(client, 1)

    # step 7
    dr_volume = wait_for_volume_degraded(client, dr_volume.name)
    assert dr_volume.controllers[0].hostId != tainted_node_id
    assert dr_volume.controllers[0].hostId != node_x

    node_running_latest_enging = dr_volume.controllers[0].hostId

    # step 8, 9 10
    res_vol_name = "vol-rs"

    client.create_volume(name=res_vol_name, numberOfReplicas=1,
                         fromBackup=b1.url)
    wait_for_volume_condition_restore(client, res_vol_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, res_vol_name,
                                      "reason", "RestoreInProgress")

    res_volume = wait_for_volume_detached(client, res_vol_name)
    res_volume = client.by_id_volume(res_vol_name)

    assert res_volume.ready is True
    assert len(res_volume.replicas) == 1
    assert res_volume.replicas[0].hostId == node_running_latest_enging

    # step 11, 12
    expand_size = str(2 * Gi)
    res_volume.expand(size=expand_size)
    wait_for_volume_expansion(client, res_volume.name)
    res_volume = wait_for_volume_detached(client, res_volume.name)
    res_volume.attach(hostId=node_running_latest_enging, disableFrontend=False)
    res_volume = wait_for_volume_healthy(client, res_volume.name)
    assert res_volume.size == expand_size

    # step 13
    replenish_wait_setting = \
        client.by_id_setting(SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL)
    client.update(replenish_wait_setting, value="600")

    # step 14
    volume1 = client.by_id_volume(volume1.name)
    for replica in volume1.replicas:
        if replica.hostId == node_x:
            crash_replica_processes(client, core_api, res_volume.name,
                                    replicas=[replica],
                                    wait_to_fail=True)

    # step 15
    volume1 = wait_for_volume_degraded(client, volume1.name)
    for i in range(RETRY_COUNTS_SHORT * 2):
        volume1 = client.by_id_volume(volume1.name)
        assert len(volume1.replicas) == 2
        for replica in volume1.replicas:
            if replica.hostId == node_x:
                assert replica.running is False
            else:
                assert replica.running is True

        time.sleep(RETRY_INTERVAL_LONG)


def test_autosalvage_with_data_locality_enabled(client, core_api, make_deployment_with_pvc, volume_name, pvc): # NOQA
    """
    This e2e test follows the manual test steps at:
    https://github.com/longhorn/longhorn/issues/2778#issue-939331805

    Preparation:
    1. Let's call the 3 nodes: node-1, node-2, node-3

    Steps:
    1. Add the tag `node-1` to `node-1`
    2. Create a volume with 1 replica, data-locality set to best-effort,
       and tag set to `node-1`
    3. Create PV/PVC from the volume.
    4. Create a pod that uses the PVC. Set node selector for the pod so that
       it will be schedule on to `node-2`. This makes sure that there is a
       failed-to-scheduled local replica
    5. Wait for the pod to be in running state.
    6. Kill the aio instance manager on `node-1`.
    7. In a 3-min retry loop, verify that Longhorn salvage the volume
       and the workload pod is restarted. Exec into the workload pod.
       Verify that read/write to the volume is ok
    8. Exec into the longhorn manager pod on `node-2`.
       Running `ss -a -n | grep :8500 | wc -l` to find the number of socket
       connections from this manager pod to instance manager pods.
       In a 2-min loop, verify that the number of socket connection is <= 20

    Cleaning up:
    1. Clean up the node tag
    """

    # Step1
    nodes = client.list_node()
    assert len(nodes) == 3
    node_1, node_2, node_3 = nodes
    tags = ["node-1"]
    node_1 = common.set_node_tags(client, node_1, tags)

    # Step2
    client.create_volume(
        name=volume_name, size=str(1 * Gi), numberOfReplicas=1,
        nodeSelector=tags, dataLocality="best-effort"
        )

    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume.nodeSelector == tags

    # Step3
    pvc_name = volume_name + "-pvc"
    create_pv_for_volume(client, core_api, volume, volume_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    # Step4
    deployment_name = volume_name + "-dep"
    deployment = make_deployment_with_pvc(deployment_name, pvc_name)
    deployment["spec"]["template"]["spec"]["nodeSelector"] \
        = {"kubernetes.io/hostname": node_2.name}

    # Step5
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    pod_names = common.get_deployment_pod_names(core_api, deployment)
    data_path = '/data/test'
    write_pod_volume_random_data(core_api,
                                 pod_names[0],
                                 data_path,
                                 DATA_SIZE_IN_MB_1)
    expected_test_data_checksum = get_pod_data_md5sum(core_api,
                                                      pod_names[0],
                                                      data_path)
    create_snapshot(client, volume_name)

    # Step6
    labels = f'longhorn.io/node={node_1["name"]}, \
               longhorn.io/instance-manager-type=aio'

    ret = core_api.list_namespaced_pod(
            namespace=LONGHORN_NAMESPACE, label_selector=labels)
    imr_name = ret.items[0].metadata.name

    delete_and_wait_pod(core_api, pod_name=imr_name,
                        namespace='longhorn-system')

    # Step7
    target_pod = \
        core_api.read_namespaced_pod(name=pod_names[0], namespace='default')
    wait_delete_pod(core_api, target_pod.metadata.uid)
    deployment_pod = common.wait_and_get_any_deployment_pod(core_api,
                                                            deployment_name)

    test_data_checksum = get_pod_data_md5sum(core_api,
                                             deployment_pod.metadata.name,
                                             data_path)

    assert expected_test_data_checksum == test_data_checksum

    # Step8
    labels = "app=longhorn-manager"
    selector = "spec.nodeName=={}".format(node_2["name"])
    ret = core_api.list_namespaced_pod(
                namespace=LONGHORN_NAMESPACE, field_selector=selector,
                label_selector=labels)

    mgr_name = ret.items[0].metadata.name

    command = 'ss -a -n | grep :8500 | wc -l'
    for i in range(RETRY_EXEC_COUNTS):
        socket_cnt = exec_command_in_pod(
            core_api, command, mgr_name, 'longhorn-system')
        assert int(socket_cnt) < 20

        time.sleep(RETRY_EXEC_INTERVAL)


def test_recovery_from_im_deletion(client, core_api, volume_name, make_deployment_with_pvc, pvc): # NOQA
    """
    Related issue :
    https://github.com/longhorn/longhorn/issues/3070

    Steps:
    1. Create a volume and PV/PVC.
    2. Create a deployment with 1 pod having below in command section on node-1
       and attach to the volume.
       command:
          - "/bin/sh"
          - "-ec"
          - |
            touch /data/test
            tail -f /data/test
    3. Wait for the pod to become healthy.
    4. Write small(100MB) data.
    5. Kill the instance-manager-e on node-1.
    6. Wait for the instance-manager-e pod to become healthy.
    7. Wait for pod to get terminated and recreated.
    8. Read and write in the pod to verify the pod is accessible.
    """

    # Step1
    client.create_volume(name=volume_name, size=str(1 * Gi))
    volume = wait_for_volume_detached(client, volume_name)
    pvc_name = volume_name + "-pvc"
    create_pv_for_volume(client, core_api, volume, volume_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    # Step2
    command = [
        "/bin/sh",
        "-ec",
        "touch /data/test\ntail -f /data/test\n"
        ]
    deployment_name = volume_name + "-dep"
    deployment = make_deployment_with_pvc(deployment_name, pvc_name)
    deployment["spec"]["template"]["spec"]["containers"][0]["command"] \
        = command

    # Step3
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    # Step4
    pod_names = common.get_deployment_pod_names(core_api, deployment)
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_names[0], test_data, filename='test')
    create_snapshot(client, volume_name)

    # Step5, 6
    volume = client.by_id_volume(volume_name)
    im_name = volume["controllers"][0]["instanceManagerName"]
    exec_cmd = ["kubectl", "delete", "pod",  im_name, "-n", LONGHORN_NAMESPACE]
    subprocess.check_output(exec_cmd)

    target_pod = \
        core_api.read_namespaced_pod(name=pod_names[0], namespace='default')
    wait_delete_pod(core_api, target_pod.metadata.uid)

    # Step7
    pod_names = common.get_deployment_pod_names(core_api, deployment)
    wait_pod(pod_names[0])

    command = 'cat /data/test'
    for i in range(RETRY_COMMAND_COUNT):
        try:
            to_be_verified_data = exec_command_in_pod(
                core_api, command, pod_names[0], 'default')
            if test_data == to_be_verified_data:
                break
        except Exception as e:
            print(e)
        finally:
            time.sleep(RETRY_INTERVAL)

    # Step8
    assert test_data == to_be_verified_data


def restore_with_replica_failure(client, core_api, volume_name, csi_pv, # NOQA
                                 pvc, pod_make, # NOQA
                                 allow_degraded_availability,
                                 disable_rebuild, replica_failure_mode):
    """
    restore_with_replica_failure is reusable by a number of similar tests.
    In general, it attempts a volume restore, kills one of the restoring
    replicas, and verifies the restore can still complete. The manner in which
    a replica is killed and the settings enabled at the time vary with the
    parameters.
    """

    backupstore_cleanup(client)

    update_setting(client, common.SETTING_DEGRADED_AVAILABILITY,
                   str(allow_degraded_availability).lower())

    data_path = "/data/test"
    _, _, _, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    volume_size=str(2 * Gi),
                                    data_size_in_mb=DATA_SIZE_IN_MB_4,
                                    data_path=data_path)

    volume = client.by_id_volume(volume_name)
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name, retry_count=600)
    _, b = find_backup(client, volume_name, snap.name)

    restore_volume_name = volume_name + "-restore"
    client.create_volume(name=restore_volume_name, size=str(2 * Gi),
                         fromBackup=b.url)

    _ = wait_for_volume_restoration_start(client, restore_volume_name, b.name)
    restore_volume = client.by_id_volume(restore_volume_name)
    failed_replica = restore_volume.replicas[0]

    if disable_rebuild:
        common.update_setting(
            client,
            common.SETTING_CONCURRENT_REPLICA_REBUILD_PER_NODE_LIMIT, "0")

    if replica_failure_mode == REPLICA_FAILURE_MODE_CRASH:
        crash_replica_processes(client, core_api, restore_volume_name,
                                replicas=[failed_replica],
                                wait_to_fail=False)
    if replica_failure_mode == REPLICA_FAILURE_MODE_DELETE:
        restore_volume.replicaRemove(name=failed_replica.name)

    if not disable_rebuild:
        # If disable_rebuild then we expect the volume to quickly finish
        # restoration and detach. We MIGHT be able to catch it degraded before,
        # but trying can lead to flakes. Check degraded at the end of test,
        # since no rebuilds are allowed.
        wait_for_volume_degraded(client, restore_volume_name)
        running_replica_count = 0
        for i in range(RETRY_COUNTS):
            running_replica_count = 0
            for r in restore_volume.replicas:
                if r['running'] and not r['failedAt']:
                    running_replica_count += 1
            if running_replica_count == 3:
                break
            time.sleep(RETRY_INTERVAL)
        assert running_replica_count == 3

    wait_for_volume_restoration_completed(client, restore_volume_name)
    wait_for_volume_condition_restore(client, restore_volume_name,
                                      "status", "False")
    restore_volume = wait_for_volume_detached(client, restore_volume_name)
    assert restore_volume.ready

    if disable_rebuild and replica_failure_mode == REPLICA_FAILURE_MODE_DELETE:
        assert len(restore_volume.replicas) == 3
        for r in restore_volume.replicas:
            assert r['failedAt'] == ""
            assert failed_replica.name != r.name

    restore_pod_name = restore_volume_name + "-pod"
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"
    create_pv_for_volume(client, core_api, restore_volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, restore_volume, restore_pvc_name)

    restore_pod = pod_make(name=restore_pod_name)
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]
    create_and_wait_pod(core_api, restore_pod)

    restore_volume = client.by_id_volume(restore_volume_name)
    if disable_rebuild:
        # Restoration should be complete, but without one replica.
        assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == \
            VOLUME_ROBUSTNESS_DEGRADED
    else:
        assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == \
            VOLUME_ROBUSTNESS_HEALTHY

    restore_md5sum = get_pod_data_md5sum(core_api, restore_pod_name, data_path)
    assert restore_md5sum == md5sum

    # cleanup the backupstore so we don't impact other tests
    # since we crashed the replica that initiated the restore
    # it's backupstore lock will still be present, so we need to
    # wait till the lock is expired, before we can delete the backups
    backupstore_wait_for_lock_expiration()
    backupstore_cleanup(client)
