import pytest
import common
import time
import random

from common import client, core_api, volume_name  # NOQA
from common import SIZE, VOLUME_RWTEST_SIZE, EXPAND_SIZE, Gi
from common import DATA_SIZE_IN_MB_2, DATA_SIZE_IN_MB_3
from common import check_volume_data, cleanup_volume, create_and_check_volume
from common import delete_replica_processes, crash_replica_processes
from common import get_self_host_id, check_volume_endpoint
from common import wait_for_snapshot_purge, write_volume_random_data
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import create_snapshot
from common import expand_attached_volume, check_block_device_size
from common import write_volume_data, generate_random_data
from common import wait_for_rebuild_complete
from common import disable_auto_salvage # NOQA
from common import pod_make  # NOQA
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_pvc_spec
from common import create_and_wait_pod
from common import write_pod_volume_random_data
from common import wait_for_volume_healthy, wait_for_volume_degraded
from common import get_pod_data_md5sum
from common import wait_for_pod_remount
from common import delete_and_wait_pod
from common import delete_and_wait_pvc, delete_and_wait_pv
from common import wait_for_rebuild_start
from common import prepare_pod_with_data_in_mb
from common import wait_for_replica_running
from common import set_random_backupstore
from common import wait_for_backup_completion, find_backup
from common import wait_for_volume_creation, wait_for_volume_detached
from common import wait_for_volume_restoration_start
from common import wait_for_volume_restoration_completed
from common import check_volume_last_backup
from common import activate_standby_volume


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


def ha_simple_recovery_test(client, volume_name, size, base_image=""):  # NOQA
    volume = create_and_check_volume(client, volume_name, 2, size, base_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

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

    volume = common.wait_for_volume_healthy(client, volname)

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
    """
    ha_salvage_test(client, core_api, volume_name)


def ha_salvage_test(client, core_api, # NOQA
                    volume_name, base_image=""):  # NOQA
    # case: replica processes are wrongly removed
    volume = create_and_check_volume(client, volume_name, 2,
                                     base_image=base_image)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    delete_replica_processes(client, core_api, volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)

    # case: replica processes get crashed
    volume = create_and_check_volume(client, volume_name, 2,
                                     base_image=base_image)
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 2
    replica0_name = volume.replicas[0].name
    replica1_name = volume.replicas[1].name

    data = write_volume_random_data(volume)

    crash_replica_processes(client, core_api, volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt != ""
    assert volume.replicas[1].failedAt != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)

    cleanup_volume(client, volume)


# https://github.com/rancher/longhorn/issues/253
def test_ha_backup_deletion_recovery(client, volume_name):  # NOQA
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


def ha_backup_deletion_recovery_test(client, volume_name, size, base_image=""):  # NOQA
    volume = client.create_volume(name=volume_name, size=size,
                                  numberOfReplicas=2, baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    # test backupTarget for multiple settings
    backupstores = common.get_backupstore_url()
    for backupstore in backupstores:
        if common.is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            setting = client.update(setting, value=backupsettings[0])
            assert setting.value == backupsettings[0]

            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential.value == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting.value == backupstore
            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential.value == ""

        data = write_volume_random_data(volume)
        snap2 = create_snapshot(client, volume_name)
        create_snapshot(client, volume_name)

        volume.snapshotBackup(name=snap2.name)

        _, b = common.find_backup(client, volume_name, snap2.name)

        res_name = common.generate_volume_name()
        res_volume = client.create_volume(name=res_name, size=size,
                                          numberOfReplicas=2,
                                          fromBackup=b.url)
        res_volume = common.wait_for_volume_restoration_completed(
            client, res_name)
        res_volume = common.wait_for_volume_detached(client, res_name)
        res_volume = res_volume.attach(hostId=host_id)
        res_volume = common.wait_for_volume_healthy(client, res_name)
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
        res_volume = common.wait_for_volume_detached(client, res_name)

        client.delete(res_volume)
        common.wait_for_volume_delete(client, res_name)

    cleanup_volume(client, volume)


# https://github.com/rancher/longhorn/issues/415
def test_ha_prohibit_deleting_last_replica(client, volume_name):  # NOQA
    """
    Test prohibiting deleting the last replica

    1. Create volume with one replica and attach to the current node.
    2. Try to delete the replica. It should error out

    FIXME: Move out of test_ha.py
    """
    volume = create_and_check_volume(client, volume_name, 1)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume.replicas) == 1
    replica0 = volume.replicas[0]

    with pytest.raises(Exception) as e:
        volume.replicaRemove(name=replica0.name)
    assert "no other healthy replica available" in str(e.value)

    cleanup_volume(client, volume)


def test_ha_recovery_with_expansion(client, volume_name):   # NOQA
    """
    [HA] Test recovery with volume expansion

    1. Create a volume length `SIZE` and attach to the current node.
    2. Write `data1` to the volume
    3. Expand the volume to `EXPAND_SIZE`, and check volume has been expanded
    4. Write `data2` starting from `SIZE`.
    5. Remove replica0 from volume
    6. Wait volume to start rebuilding and complete
    7. Check the `data1` and `data2`

    FIXME: why on step 6, checked volume.replicas >= 2?
    """
    volume = create_and_check_volume(client, volume_name, 2, SIZE)

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2
    replica0 = volume.replicas[0]
    assert replica0.name != ""
    replica1 = volume.replicas[1]
    assert replica1.name != ""

    data1 = write_volume_random_data(volume)

    expand_attached_volume(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_block_device_size(volume, int(EXPAND_SIZE))

    data2 = {
        'pos': int(SIZE),
        'content': generate_random_data(VOLUME_RWTEST_SIZE),
    }
    data2 = write_volume_data(volume, data2)

    volume.replicaRemove(name=replica0.name)
    # wait until we saw a replica starts rebuilding
    new_replica_found = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        for r in v.replicas:
            if r.name != replica0.name and \
                    r.name != replica1.name:
                new_replica_found = True
                break
        if new_replica_found:
            break
        time.sleep(RETRY_INTERVAL)
    wait_for_rebuild_complete(client, volume_name)
    assert new_replica_found

    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.state == common.VOLUME_STATE_ATTACHED
    assert volume.robustness == common.VOLUME_ROBUSTNESS_HEALTHY
    assert len(volume.replicas) >= 2

    found = False
    for replica in volume.replicas:
        if replica.name == replica1.name:
            found = True
            break
    assert found

    check_volume_data(volume, data1, False)
    check_volume_data(volume, data2)

    cleanup_volume(client, volume)


def wait_pod_for_auto_salvage(
        client, core_api, volume_name, pod_name, pv_name, pvc_name,   # NOQA
        original_md5sum, data_path="/data/test"):
    # this line may fail if the recovery is too quick
    common.wait_for_volume_faulted(client, volume_name)

    wait_for_volume_healthy(client, volume_name)

    wait_for_pod_remount(core_api, pod_name)

    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert md5sum == original_md5sum

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


def test_salvage_auto_crash_all_replicas(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature by crashing all the replicas

    1. Create PV/PVC/POD. Make sure POD has liveness check. Start the pod
    2. Write random data to the pod and get the md5sum.
    3. Run `sync` command inside the pod to make sure data flush to the volume.
    4. Crash all replica processes using SIGTERM
    5. Wait for volume to `faulted`, then `healthy`
    6. Check replica `failedAt` has been cleared.
    7. Wait for pod to be restarted.
    8. Check md5sum of the data in the Pod.

    FIXME: Step 5 is only a intermediate state, maybe no way to get it for sure
    """

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, pod_make, volume_name)

    crash_replica_processes(client, core_api, volume_name)

    wait_pod_for_auto_salvage(client, core_api, volume_name,
                              pod_name, pv_name, pvc_name, md5sum)


# Test case #2: delete one replica process, wait for rebuild start
# then delete all replica processes.
def test_salvage_auto_crash_replicas_short_wait(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature, with replica building pending

    1. Create a PV/PVC/Pod with liveness check.
    2. Create volume and start the pod.
    3. Write random data to the pod and get the md5sum.
    4. Run `sync` command inside the pod to make sure data flush to the volume.
    5. Crash one of the replica.
    6. Wait for rebuild start and the rebuilding replica running
    7. Crash all the replicas.
    8. Make sure volume and Pod recovers.
    9. Check md5sum of the data in the Pod.
    """
    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, pod_make, volume_name,
            data_size_in_mb=DATA_SIZE_IN_MB_2)

    volume = client.by_id_volume(volume_name)
    replica0 = volume.replicas[0]

    crash_replica_processes(client, core_api, volume_name, [replica0])

    # Need to wait for rebuilding replica running before crashing all replicas
    # Otherwise the rebuilding replica may become running after step7 then
    # the auto salvage cannot be triggered.
    _, rebuilding_replica = wait_for_rebuild_start(client, volume_name)
    wait_for_replica_running(client, volume_name, rebuilding_replica)

    volume = client.by_id_volume(volume_name)

    replicas = []
    for r in volume.replicas:
        if r.running is True:
            replicas.append(r)

    crash_replica_processes(client, core_api, volume_name, replicas)

    wait_pod_for_auto_salvage(client, core_api, volume_name,
                              pod_name, pv_name, pvc_name, md5sum)


# Test case #3: delete one replica process, wait for rebuild finish
# then delete all replica processes.
def test_salvage_auto_crash_replicas_long_wait(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature, with replica building complete

    1. Create a PV/PVC/Pod with liveness check.
    2. Create volume and start the pod.
    3. Write random data to the pod and get the md5sum.
    4. Run `sync` command inside the pod to make sure data flush to the volume.
    5. Crash one of the replica then wait for rebuild complete.
    6. Crash all the replicas.
    7. Make sure volume and Pod recovers.
    8. Check md5sum of the data in the Pod.
    """
    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, pod_make, volume_name)

    volume = client.by_id_volume(volume_name)
    replica0 = volume.replicas[0]

    crash_replica_processes(client, core_api, volume_name, [replica0])
    wait_for_rebuild_start(client, volume_name)
    wait_for_rebuild_complete(client, volume_name)

    volume = client.by_id_volume(volume_name)

    replicas = []
    for r in volume.replicas:
        if r.running is True:
            replicas.append(r)

    crash_replica_processes(client, core_api, volume_name, replicas)

    wait_pod_for_auto_salvage(client, core_api, volume_name,
                              pod_name, pv_name, pvc_name, md5sum)


def test_rebuild_failure_with_intensive_data(client, core_api, volume_name, pod_make):  # NOQA
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
            client, core_api, pod_make, volume_name,
            data_path=data_path_1, data_size_in_mb=DATA_SIZE_IN_MB_2)
    create_snapshot(client, volume_name)
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path_2, DATA_SIZE_IN_MB_2)
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

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


def test_rebuild_replica_and_from_replica_on_the_same_node(
        client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test the corner case that the from-replica and the rebuilding replica
    are on the same node

    1. Disable scheduling for all nodes except for one.
    2. Create a pod with Longhorn volume and wait for pod to start
    3. Write data to `/data/test` inside the pod and get `original_checksum`
    4. Find running replicas of the volume
    5. Crash one of the running replicas.
    6. Wait for the replica rebuild to start.
    7. Check if the rebuilding replica is a new replica,
       and the replica which is sending data is an existing replica.
    8. Wait for volume to finish the rebuild and become healthy,
       then check if the replica is rebuilt on the only available node
    9. Check md5sum for the written data
    """
    available_node_name = ""
    nodes = client.list_node()
    assert len(nodes) > 0
    for node in nodes:
        if not available_node_name:
            available_node_name = node.name
            continue
        node = client.update(node, allowScheduling=False)
        common.wait_for_node_update(client, node.id,
                                    "allowScheduling", False)

    data_path = "/data/test"
    pod_name, pv_name, pvc_name, original_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, pod_make, volume_name,
            data_path=data_path, data_size_in_mb=DATA_SIZE_IN_MB_3)

    volume = client.by_id_volume(volume_name)
    original_replicas = volume.replicas
    assert len(original_replicas) == 3
    # Trigger rebuild
    crash_replica_processes(client, core_api, volume_name,
                            [original_replicas[0]])
    wait_for_volume_degraded(client, volume_name)
    from_replica_name, rebuilding_replica_name = \
        wait_for_rebuild_start(client, volume_name)
    assert from_replica_name != rebuilding_replica_name
    verified_from_replica = False
    for r in original_replicas:
        assert r.name != rebuilding_replica_name
        if r.name == from_replica_name:
            verified_from_replica = True
    assert verified_from_replica

    # Wait for volume healthy and
    # check if the replica is rebuilt on the only available node
    volume = wait_for_volume_healthy(client, volume_name)
    for replica in volume.replicas:
        if replica.name == rebuilding_replica_name:
            rebuilt_replica = replica
            break
    assert rebuilt_replica
    assert rebuilt_replica.hostId == available_node_name

    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert original_md5sum == md5sum

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


def test_rebuild_with_restoration(
        client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test if the rebuild is disabled for the restoring volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to the volume and get the md5sum.
    4. Create a backup for the volume.
    5. Restore a volume from the backup.
    6. Delete one replica during the restoration.
    7. Wait for the restoration complete and the volume detached.
    8. Check if there is a rebuilt replica for the restored volume.
    9. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    10. Check if the restored volume is state `degraded`
        after the attachment.
    11. Wait for the rebuild complete and the volume becoming healthy.
    12. Check md5sum of the data in the restored volume.
    13. Do cleanup.
    """
    set_random_backupstore(client)

    original_volume_name = volume_name + "-origin"
    data_path = "/data/test"
    original_pod_name, original_pv_name, original_pvc_name, original_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, pod_make, original_volume_name,
            data_path=data_path, data_size_in_mb=DATA_SIZE_IN_MB_2)

    original_volume = client.by_id_volume(original_volume_name)
    snap = create_snapshot(client, original_volume_name)
    original_volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, original_volume_name, snap.name)
    bv, b = find_backup(client, original_volume_name, snap.name)

    restore_volume_name = volume_name + "-restore"
    client.create_volume(name=restore_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b.url)
    wait_for_volume_creation(client, restore_volume_name)

    restoring_replica = wait_for_volume_restoration_start(
        client, restore_volume_name)
    restore_volume = client.by_id_volume(restore_volume_name)
    restore_volume.replicaRemove(name=restoring_replica)
    wait_for_volume_restoration_completed(client, restore_volume_name)
    restore_volume = wait_for_volume_detached(client, restore_volume_name)
    assert len(restore_volume.replicas) == 2
    for r in restore_volume.replicas:
        assert restoring_replica != r.name

    restore_pod_name = restore_volume_name + "-pod"
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"
    restore_pod = pod_make(name=restore_pod_name)
    create_pv_for_volume(client, core_api, restore_volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, restore_volume, restore_pvc_name)
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]
    create_and_wait_pod(core_api, restore_pod)

    wait_for_volume_degraded(client, restore_volume_name)
    wait_for_rebuild_complete(client, restore_volume_name)
    wait_for_volume_healthy(client, restore_volume_name)

    md5sum = get_pod_data_md5sum(core_api, restore_pod_name, data_path)
    assert original_md5sum == md5sum

    bv.backupDelete(name=b.name)
    delete_and_wait_pod(core_api, original_pod_name)
    delete_and_wait_pvc(core_api, original_pvc_name)
    delete_and_wait_pv(core_api, original_pv_name)
    delete_and_wait_pod(core_api, restore_pod_name)
    delete_and_wait_pvc(core_api, restore_pvc_name)
    delete_and_wait_pv(core_api, restore_pv_name)


def test_rebuild_with_inc_restoration(
        client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test if the rebuild is disabled for the DR volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to `/data/test1` inside the pod and get the md5sum.
    4. Create the 1st backup for the volume.
    5. Create a DR volume based on the backup
       and wait for the init restoration complete.
    6. Write more data to the original volume then create the 2nd backup.
    7. Wait for the DR volume incremental restoration start
       then delete one replica during the restoration.
    8. Wait for the inc restoration complete.
    9. Activate the DR volume then check
       if the rebuild is disabled for the DR volume.
    10. Create PV/PVC/Pod for the activated volume
        and wait for the pod start.
    11. Check if the restored volume is state `degraded`
        after the attachment.
    12. Wait for the rebuild complete and the volume becoming healthy.
    13. Check md5sum of the data in the activated volume.
    14. Do cleanup.
    """
    set_random_backupstore(client)

    std_volume_name = volume_name + "-std"
    data_path1 = "/data/test1"
    std_pod_name, std_pv_name, std_pvc_name, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, pod_make, std_volume_name,
            data_path=data_path1, data_size_in_mb=DATA_SIZE_IN_MB_2)

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
    wait_for_volume_restoration_completed(client, dr_volume_name)

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_2)
    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, data_path2)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name)
    bv, b2 = find_backup(client, std_volume_name, snap2.name)

    # Trigger rebuild during the incremental restoration
    restoring_replica = wait_for_volume_restoration_start(
        client, dr_volume_name)
    dr_volume = client.by_id_volume(dr_volume_name)
    dr_volume.replicaRemove(name=restoring_replica)

    # Wait for inc restoration complete
    check_volume_last_backup(client, dr_volume_name, b2.name)
    dr_volume = wait_for_volume_degraded(client, dr_volume_name)
    assert len(dr_volume.replicas) == 2
    for r in dr_volume.replicas:
        assert restoring_replica != r.name

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

    wait_for_volume_degraded(client, dr_volume_name)
    wait_for_rebuild_start(client, dr_volume_name)
    wait_for_rebuild_complete(client, dr_volume_name)
    wait_for_volume_healthy(client, dr_volume_name)

    md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path1)
    assert std_md5sum1 == md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert std_md5sum2 == md5sum2

    bv.backupDelete(name=b1.name)
    bv.backupDelete(name=b2.name)
    delete_and_wait_pod(core_api, std_pod_name)
    delete_and_wait_pvc(core_api, std_pvc_name)
    delete_and_wait_pv(core_api, std_pv_name)
    delete_and_wait_pod(core_api, dr_pod_name)
    delete_and_wait_pvc(core_api, dr_pvc_name)
    delete_and_wait_pv(core_api, dr_pv_name)


@pytest.mark.skip
def test_single_replica_failed_during_engine_start():
    """
    Test if the volume still works fine when there is
    an invalid replica/backend in the engine starting phase.

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
    pass
