import pytest
import common
import time
import random
import subprocess

from common import client, core_api, volume_name  # NOQA
from common import sts_name, statefulset, storage_class  # NOQA
from common import DATA_SIZE_IN_MB_1, DATA_SIZE_IN_MB_2, DATA_SIZE_IN_MB_3
from common import DATA_SIZE_IN_MB_4
from common import check_volume_data, cleanup_volume, create_and_check_volume
from common import delete_replica_processes, crash_replica_processes
from common import get_self_host_id, check_volume_endpoint
from common import wait_for_snapshot_purge, write_volume_random_data
from common import create_snapshot
from common import expand_attached_volume, check_block_device_size
from common import write_volume_data, generate_random_data
from common import wait_for_rebuild_complete
from common import disable_auto_salvage # NOQA
from common import pod_make, pod, csi_pv, pvc  # NOQA
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_pvc_spec
from common import create_and_wait_pod
from common import write_pod_volume_random_data
from common import wait_for_volume_healthy, wait_for_volume_degraded
from common import get_pod_data_md5sum
from common import wait_for_pod_remount
from common import delete_and_wait_pod
from common import wait_for_rebuild_start
from common import prepare_pod_with_data_in_mb
from common import set_random_backupstore
from common import wait_for_backup_completion, find_backup
from common import wait_for_volume_creation, wait_for_volume_detached
from common import wait_for_volume_restoration_start
from common import wait_for_backup_restore_completed
from common import wait_for_volume_restoration_completed
from common import check_volume_last_backup
from common import activate_standby_volume
from common import set_backupstore_s3  # NOQA
from common import create_backup
from common import wait_for_volume_faulted
from common import wait_for_volume_delete
from common import SETTING_AUTO_SALVAGE
from common import SETTING_BACKUP_TARGET
from common import wait_for_volume_condition_restore
from common import wait_for_pod_restart
from common import crash_engine_process_with_sigkill
from common import wait_for_volume_healthy_no_frontend
from common import exec_instance_manager
from common import SIZE, VOLUME_RWTEST_SIZE, EXPAND_SIZE, Gi
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import write_pod_volume_data
from common import read_volume_data
from common import VOLUME_FIELD_ROBUSTNESS
from common import VOLUME_ROBUSTNESS_HEALTHY
from common import wait_for_volume_expansion
from common import delete_and_wait_pvc, delete_and_wait_pv
from common import wait_for_volume_replica_count
from common import settings_reset # NOQA

from backupstore import backupstore_cleanup
from backupstore import backupstore_delete_random_backup_block
from backupstore import backupstore_wait_for_lock_expiration


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
    7. Verify there are 5 replicas, 3 good replicas
        (one is from the first three replicas), and 2 failed replicas
        (both are from the first three replicas).
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
        wait_for_backup_completion(client, volume_name, snap2.name)
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
        client, core_api, volume_name, pod_name, original_md5sum,  # NOQA
        data_path="/data/test"):
    try:
        # this line may fail if the recovery is too quick
        common.wait_for_volume_faulted(client, volume_name)
    except AssertionError:
        print("\nException waiting for volume faulted,"
              "could have missed it")

    wait_for_volume_healthy(client, volume_name)

    common.wait_for_pod_phase(core_api, pod_name, pod_phase="Pending")
    common.wait_for_pod_phase(core_api, pod_name, pod_phase="Running")

    wait_for_pod_remount(core_api, pod_name)

    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)
    assert md5sum == original_md5sum


def test_salvage_auto_crash_all_replicas(
        client, core_api, storage_class, sts_name, statefulset):  # NOQA
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
    wait_pod_for_auto_salvage(client, core_api, vol_name, pod_name, md5sum)

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

    wait_pod_for_auto_salvage(client, core_api, vol_name, pod_name, md5sum)


def test_rebuild_failure_with_intensive_data(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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


def test_rebuild_replica_and_from_replica_on_the_same_node(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test the corner case that the from-replica and the rebuilding replica
    are on the same node

    Test prerequisites:
      - set Replica Node Level Soft Anti-Affinity enabled

    1. Enable the setting replica-soft-anti-affinity.
    2. Disable scheduling for all nodes except for one.
    3. Create a pod with Longhorn volume and wait for pod to start
    4. Write data to `/data/test` inside the pod and get `original_checksum`
    5. Find running replicas of the volume
    6. Crash one of the running replicas.
    7. Wait for the replica rebuild to start.
    8. Check if the rebuilding replica is a new replica,
       and the replica which is sending data is an existing replica.
    9. Wait for volume to finish the rebuild and become healthy,
       then check if the replica is rebuilt on the only available node
    10. Check md5sum for the written data
    """

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="true")

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
            client, core_api, csi_pv, pvc, pod_make, volume_name,
            data_path=data_path, data_size_in_mb=DATA_SIZE_IN_MB_4)

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


def test_rebuild_with_restoration(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if the rebuild is disabled for the restoring volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to the volume and get the md5sum.
    4. Create a backup for the volume.
    5. Restore a volume from the backup.
    6. Delete one replica during the restoration.
    7. Wait for the restoration complete and the volume detached.
    8. Check if the replica is rebuilt for the auto detachment.
    9. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    10. Check if the restored volume is state `Healthy`
        after the attachment.
    11. Check md5sum of the data in the restored volume.
    12. Do cleanup.
    """
    set_random_backupstore(client)

    original_volume_name = volume_name + "-origin"
    data_path = "/data/test"
    original_pod_name, original_pv_name, original_pvc_name, original_md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, original_volume_name,
            data_path=data_path, data_size_in_mb=DATA_SIZE_IN_MB_3)

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
        client, restore_volume_name, b.name)
    restore_volume = client.by_id_volume(restore_volume_name)
    restore_volume.replicaRemove(name=restoring_replica)
    client.list_backupVolume()

    # Wait for the rebuild start
    running_replica_count = 0
    for i in range(RETRY_COUNTS):
        running_replica_count = 0
        restore_volume = client.by_id_volume(restore_volume_name)
        for r in restore_volume.replicas:
            if r['running'] and not r['failedAt']:
                running_replica_count += 1
        if running_replica_count == 3:
            break
        time.sleep(RETRY_INTERVAL)
    assert running_replica_count == 3

    wait_for_volume_restoration_completed(client, restore_volume_name)
    restore_volume = wait_for_volume_detached(client, restore_volume_name)
    assert len(restore_volume.replicas) == 3
    for r in restore_volume.replicas:
        assert restoring_replica != r.name
        assert r['failedAt'] == ""

    restore_pod_name = restore_volume_name + "-pod"
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"
    restore_pod = pod_make(name=restore_pod_name)
    create_pv_for_volume(client, core_api, restore_volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, restore_volume, restore_pvc_name)
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]
    create_and_wait_pod(core_api, restore_pod)

    restore_volume = client.by_id_volume(restore_volume_name)
    assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

    md5sum = get_pod_data_md5sum(core_api, restore_pod_name, data_path)
    assert original_md5sum == md5sum

    # cleanup the backupstore so we don't impact other tests
    # since we crashed the replica that initiated the restore
    # it's backupstore lock will still be present, so we need to
    # wait till the lock is expired, before we can delete the backups
    backupstore_wait_for_lock_expiration()
    backupstore_cleanup(client)


def test_rebuild_with_inc_restoration(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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
    set_random_backupstore(client)

    std_volume_name = volume_name + "-std"
    data_path1 = "/data/test1"
    std_pod_name, std_pv_name, std_pvc_name, std_md5sum1 = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, std_volume_name,
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
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path2, DATA_SIZE_IN_MB_2)
    std_md5sum2 = get_pod_data_md5sum(core_api, std_pod_name, data_path2)
    snap2 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap2.name)
    wait_for_backup_completion(client, std_volume_name, snap2.name)
    bv, b2 = find_backup(client, std_volume_name, snap2.name)

    # Trigger rebuild during the incremental restoration
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
    assert dr_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

    md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path1)
    assert std_md5sum1 == md5sum1
    md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert std_md5sum2 == md5sum2

    # cleanup
    backupstore_cleanup(client)


def test_inc_restoration_with_multiple_rebuild_and_expansion(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if the rebuild is disabled for the DR volume
    1. Setup a random backupstore.
    2. Create a pod with a volume and wait for pod to start.
    3. Write data to the volume and get the md5sum.
    4. Create the 1st backup for the volume.
    5. Create a DR volume based on the backup
       and wait for the init restoration complete.
    6. Shut down the pod and wait for the normal volume detached.
    7. Expand the normal volume and wait for expansion complete.
    8. Re-launch a pod for the normal volume.
    9. Write more data to the normal volume. Make sure there is data in the
       expanded part.
    10. Create the 2nd backup and wait for the backup creatiom complete.
    11. Delete one replica and trigger incremental restore simultaneously.
    12. Wait for the inc restoration complete and the volume becoming Healthy.
    13. Check the DR volume size and snapshot info. Make sure there is only
        one snapshot in the volume.
    14. Write data to the normal volume then create the 3rd backup.
    15. Wait for the 3rd backup creation then trigger the inc restore for the
        DR volume.
    16. Wait for the restore complete then activate the DR volume.
    17. Create PV/PVC/Pod for the activated volume
        and wait for the pod start.
    18. Check if the restored volume is state `healthy`
        after the attachment.
    19. Check md5sum of the data in the activated volume.
    20. Crash one random replica. Then verify the rebuild still works fine for
        the activated volume.
    21. Do cleanup.
    """
    set_random_backupstore(client)

    data_path1 = "/data/test1"

    std_volume_name = volume_name + "-std"
    std_pod_name = std_volume_name + "-pod"
    std_pv_name = std_volume_name + "-pv"
    std_pvc_name = std_volume_name + "-pvc"
    size = str(1 * Gi)

    std_pod = pod_make(name=std_pod_name)
    csi_pv['metadata']['name'] = std_pv_name
    csi_pv['spec']['csi']['volumeHandle'] = std_volume_name
    csi_pv['spec']['capacity']['storage'] = size
    csi_pv['spec']['persistentVolumeReclaimPolicy'] = 'Retain'
    pvc['metadata']['name'] = std_pvc_name
    pvc['spec']['volumeName'] = std_pv_name
    pvc['spec']['resources']['requests']['storage'] = size
    pvc['spec']['storageClassName'] = ''
    std_pod['spec']['volumes'] = [create_pvc_spec(std_pvc_name)]

    create_and_check_volume(client, std_volume_name,
                            num_of_replicas=3, size=size)
    core_api.create_persistent_volume(csi_pv)
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')
    create_and_wait_pod(core_api, std_pod)
    wait_for_volume_healthy(client, std_volume_name)

    # Create the 1st backup.
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path1, DATA_SIZE_IN_MB_3)
    std_md5sum1 = get_pod_data_md5sum(core_api, std_pod_name, data_path1)

    std_volume = client.by_id_volume(std_volume_name)
    snap1 = create_snapshot(client, std_volume_name)
    std_volume.snapshotBackup(name=snap1.name)
    wait_for_backup_completion(client, std_volume_name, snap1.name)
    bv, b1 = find_backup(client, std_volume_name, snap1.name)

    # Create the DR volume
    dr_volume_name = volume_name + "-dr"
    client.create_volume(name=dr_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         frontend="", standby=True)
    wait_for_volume_creation(client, dr_volume_name)
    wait_for_volume_healthy_no_frontend(client, dr_volume_name)
    wait_for_backup_restore_completed(client, dr_volume_name, b1.name)

    # Do offline expansion for the volume.
    delete_and_wait_pod(core_api, std_pod_name)
    delete_and_wait_pvc(core_api, std_pvc_name)
    delete_and_wait_pv(core_api, std_pv_name)
    std_volume = wait_for_volume_detached(client, std_volume_name)
    expand_size = str(2 * Gi)
    std_volume.expand(size=str(expand_size))
    wait_for_volume_expansion(client, std_volume_name)

    # Re-launch the pod
    csi_pv['spec']['capacity']['storage'] = expand_size
    pvc['spec']['resources']['requests']['storage'] = expand_size
    core_api.create_persistent_volume(csi_pv)
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')
    create_and_wait_pod(core_api, std_pod)
    wait_for_volume_healthy(client, std_volume_name)

    dr_volume = client.by_id_volume(dr_volume_name)
    for r in dr_volume.replicas:
        failed_replica = r.name
        break
    assert failed_replica

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

    # Trigger rebuild and the incremental restoration
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

    # Verify the snapshot info
    dr_volume = client.by_id_volume(dr_volume_name)
    assert dr_volume.size == expand_size
    snapshots = dr_volume.snapshotList(volume=dr_volume_name)
    assert len(snapshots) == 2
    for snap in snapshots:
        if snap["name"] != "volume-head":
            assert snap["name"] == "expand-" + expand_size
            assert not snap["usercreated"]
            assert "volume-head" in snap["children"]

    data_path3 = "/data/test3"
    write_pod_volume_random_data(core_api, std_pod_name,
                                 data_path3, DATA_SIZE_IN_MB_1)
    std_md5sum3 = get_pod_data_md5sum(core_api, std_pod_name, data_path3)
    snap3 = create_snapshot(client, std_volume_name)
    std_volume = client.by_id_volume(std_volume_name)
    std_volume.snapshotBackup(name=snap3.name)
    wait_for_backup_completion(client, std_volume_name, snap3.name)
    bv, b3 = find_backup(client, std_volume_name, snap3.name)

    client.list_backupVolume()
    check_volume_last_backup(client, dr_volume_name, b3.name)

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
    assert dr_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

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


@pytest.mark.coretest
def test_single_replica_failed_during_engine_start(
        client, core_api, volume_name, csi_pv, pvc, pod): # NOQA
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

    volume = client.by_id_volume(volume_name)
    for repl in volume.replicas:
        if repl.name == replica_name:
            break

    assert repl.running is False
    assert repl.failedAt != ''

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


def test_restore_volume_with_invalid_backupstore(client, volume_name, set_backupstore_s3): # NOQA
    """
    [HA] Test if the invalid backup target will lead to the restore volume
    becoming Faulted, and if the auto salvage feature is disabled for
    the faulted restore volume.

    1. Enable auto-salvage.
    2. Set a S3 backupstore. (Cannot use NFS server here before fixing #1295)
    3. Create a volume then a backup.
    4. Invalidate the target URL.
       (e.g.: s3://backupbucket-invalid@us-east-1/backupstore-invalid)
    5. Restore a volume from the backup.
       (The fromBackup fields of the volume create API should consist of
       the invalid target URL and the valid backup volume info)
    6. Wait for the restore volume Faulted.
    7. Check if the volume condition "restore":
       `volume.conditions[restore].status == False &&
       volume.conditions[restore].reason == "RestoreFailure".`
    8. Check if `volume.ready` is false.
    9. Make sure auto-salvage is not triggered even the feature is enabled.
    10. Verify if PV/PVC cannot be created from Longhorn.
    11. Verify the faulted volume cannot be attached to a node.
    12. Verify this faulted volume can be deleted.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    bv, b, _, _ = create_backup(client, volume_name)

    res_name = "res-" + volume_name
    invalid_backup_target_url = \
        "s3://backupbucket-invalid@us-east-1/backupstore-invalid"

    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    backup_target_setting = client.update(backup_target_setting,
                                          value=invalid_backup_target_url)

    res_volume = client.create_volume(name=res_name,
                                      fromBackup=b.url)

    wait_for_volume_faulted(client, res_name)

    res_volume = client.by_id_volume(res_name)

    assert res_volume.conditions['restore'].status == "False"
    assert res_volume.conditions['restore'].reason == "RestoreFailure"
    assert res_volume.ready is False

    for i in range(10):
        res_volume = client.by_id_volume(res_name)
        assert res_volume.state == "detached"
        time.sleep(0.5)

    assert hasattr(res_volume, 'pvCreate') is False
    assert hasattr(res_volume, 'pvcCreate') is False
    assert hasattr(res_volume, 'attach') is False

    client.delete(res_volume)
    wait_for_volume_delete(client, res_name)


def test_all_replica_restore_failure(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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
       9.2. `volume.conditions[restore].status == True &&
            volume.conditions[restore].reason == "RestoreInProgress"`.
       9.3. `volume.ready == false`.
    10. Wait for the restore volume Faulted.
    11. Check if `volume.conditions[restore].status == False &&
        volume.conditions[restore].reason == "RestoreFailure"`.
    12. Check if `volume.ready == false`.
    13. Make sure auto-salvage is not triggered even the feature is enabled.
    14. Verify if PV/PVC cannot be created from Longhorn.
    15. Verify the faulted volume cannot be attached to a node.
    16. Verify this faulted volume can be deleted.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    set_random_backupstore(client)
    backupstore_cleanup(client)

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(
            client, core_api, csi_pv, pvc, pod_make, volume_name)

    volume = client.by_id_volume(volume_name)
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    bv, b = find_backup(client, volume_name, snap.name)

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

    res_volume = client.by_id_volume(res_name)

    assert res_volume.conditions['restore'].status == "False"
    assert res_volume.conditions['restore'].reason == "RestoreFailure"
    assert res_volume.ready is False

    for i in range(10):
        res_volume = client.by_id_volume(res_name)
        assert res_volume.state == "detached"
        time.sleep(0.5)

    assert hasattr(res_volume, 'pvCreate') is False
    assert hasattr(res_volume, 'pvcCreate') is False
    assert hasattr(res_volume, 'attach') is False

    client.delete(res_volume)
    wait_for_volume_delete(client, res_name)


def test_single_replica_restore_failure(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if one replica restore failure will lead to the restore volume
    becoming Degraded, and if the restore volume is still usable after
    the failure.

    Notice that this case is similar to test_rebuild_with_restoration().
    But the way to fail the replica is different.
    test_rebuild_with_restoration() directly crash the replica process
    hence there is no error in the restore status.

    1. Enable auto-salvage.
    2. Set the a random backupstore.
    3. Do cleanup for the backupstore.
    4. Create a pod with a volume and wait for pod to start.
    5. Write data to the pod volume and get the md5sum.
    6. Create a backup for the volume.
    7. Restore a volume from the backup.
    8. Wait for the volume restore start by checking if:
       8.1. `volume.restoreStatus` shows the related restore info.
       8.2. `volume.conditions[restore].status == True &&
            volume.conditions[restore].reason == "RestoreInProgress"`.
       8.3. `volume.ready == false`.
    9. Find a way to fail just one replica restore.
       e.g. Use iptable to block the restore.
    10. Wait for the restore volume Degraded.
    11. Wait for the volume restore & rebuild complete and check if:
        11.1. `volume.ready == true`
        11.2. `volume.conditions[restore].status == False &&
              volume.conditions[restore].reason == ""`.
    12. Create PV/PVC/Pod for the restored volume and wait for the pod start.
    13. Check if the restored volume is state `Healthy`
        after the attachment.
    14. Check md5sum of the data in the restored volume.
    15. Do cleanup.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    set_random_backupstore(client)
    backupstore_cleanup(client)

    data_path = "/data/test"

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    data_size_in_mb=DATA_SIZE_IN_MB_2,
                                    data_path=data_path)

    volume = client.by_id_volume(volume_name)
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    bv, b = find_backup(client, volume_name, snap.name)

    res_name = "res-" + volume_name

    client.create_volume(name=res_name, fromBackup=b.url)
    wait_for_volume_condition_restore(client, res_name,
                                      "status", "True")
    wait_for_volume_condition_restore(client, res_name,
                                      "reason", "RestoreInProgress")

    res_volume = client.by_id_volume(res_name)
    assert res_volume.ready is False

    res_volume = wait_for_volume_healthy_no_frontend(client, res_name)

    failed_replica = res_volume.replicas[0]
    crash_replica_processes(client, core_api, res_name,
                            replicas=[failed_replica],
                            wait_to_fail=False)
    wait_for_volume_degraded(client, res_name)

    # Wait for the rebuild start
    running_replica_count = 0
    for i in range(RETRY_COUNTS):
        running_replica_count = 0
        res_volume = client.by_id_volume(res_name)
        for r in res_volume.replicas:
            if r['running'] and not r['failedAt']:
                running_replica_count += 1
        if running_replica_count == 3:
            break
        time.sleep(RETRY_INTERVAL)
    assert running_replica_count == 3

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
    assert res_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

    res_md5sum = get_pod_data_md5sum(core_api, res_pod_name, data_path)
    assert md5sum == res_md5sum

    # cleanup the backupstore so we don't impact other tests
    # since we crashed the replica that initiated the restore
    # it's backupstore lock will still be present, so we need to
    # wait till the lock is expired, before we can delete the backups
    backupstore_wait_for_lock_expiration()
    backupstore_cleanup(client)


def test_dr_volume_with_restore_command_error(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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
    10. Activate the DR volume and wait for it complete.
    11. Create PV/PVC/Pod for the activated volume.
    12. Validate the volume content.
    13. Verify Writing data to the activated volume is fine.
    """
    set_random_backupstore(client)

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
    wait_for_backup_restore_completed(client, dr_volume_name, b2.name)

    dr_volume = client.by_id_volume(dr_volume_name)
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
    wait_for_volume_degraded(client, dr_volume_name)

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


def test_engine_crash_for_restore_volume(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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
      9.2. `volume.conditions[restore].status == True &&
            volume.conditions[restore].reason == "RestoreInProgress"`.
    10. Wait for the volume restore complete and detached.
    11. Recreate a pod for the restored volume and wait for the pod start.
    12. Check the data md5sum for the restored data.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    set_random_backupstore(client)
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
    wait_for_volume_detached(client, res_name)

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
    assert res_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

    res_md5sum = get_pod_data_md5sum(core_api, res_pod_name, data_path)
    assert md5sum == res_md5sum

    # cleanup the backupstore so we don't impact other tests
    # since we only crashed the engine and not the replica
    # we don't need to wait for lock expiration, since the replica
    # process will remove the lock
    backupstore_cleanup(client)


def test_engine_crash_for_dr_volume(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
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
      13.2. `volume.conditions[restore].status == True &&
            volume.conditions[restore].reason == "RestoreInProgress"`.
      13.3. `volume.standby == true`
    14. Activate the DR volume and wait for detached.
    15. Create a pod for the restored volume and wait for the pod start.
    16. Check the data md5sum for the DR volume.
    """
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    assert auto_salvage_setting.name == SETTING_AUTO_SALVAGE
    assert auto_salvage_setting.value == "true"

    set_random_backupstore(client)
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
    wait_for_backup_completion(client, volume_name, snap2.name)
    bv, b2 = find_backup(client, volume_name, snap2.name)

    # Trigger the inc restore then crash the engine process immediately.
    client.list_backupVolume()
    wait_for_volume_restoration_start(client, dr_volume_name, b2.name)
    crash_engine_process_with_sigkill(client, core_api, dr_volume_name)
    wait_for_volume_detached(client, dr_volume_name)

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
    assert dr_volume[VOLUME_FIELD_ROBUSTNESS] == \
           VOLUME_ROBUSTNESS_HEALTHY

    dr_md5sum1 = get_pod_data_md5sum(core_api, dr_pod_name, data_path)
    assert md5sum1 == dr_md5sum1
    dr_md5sum2 = get_pod_data_md5sum(core_api, dr_pod_name, data_path2)
    assert md5sum2 == dr_md5sum2


def test_volume_reattach_after_engine_sigkill(
        client, core_api, volume_name, csi_pv, pvc, pod_make):  # NOQA
    """
    [HA] Test if the volume can be reattached after using SIGKILL
    to crash the engine process

    1. Create PV/PVC/Pod. Make sure Pod has the liveness check.
    2. Wait for the pod start and the volume healthy.
    3. Write random data to the pod and get the md5sum.
    4. Crash the engine process by SIGKILL in the engine manager.
    5. Wait for volume reattached.
    6. Wait for pod to be restarted.
    7. Check md5sum of the data in the Pod.
    8. Check if data can be still written to the volume.
    """
    data_path1 = "/data/test1"

    pod_name, _, _, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    data_size_in_mb=DATA_SIZE_IN_MB_2,
                                    data_path=data_path1)

    crash_engine_process_with_sigkill(client, core_api, volume_name)

    wait_for_volume_detached(client, volume_name)
    wait_for_volume_healthy(client, volume_name)

    wait_for_pod_restart(core_api, pod_name)
    wait_for_pod_remount(core_api, pod_name)

    res_md5sum = get_pod_data_md5sum(core_api, pod_name, data_path1)
    assert md5sum == res_md5sum

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
    5. Verify a new replica is rebuilt, and the old replica containing
    the crashed file is state ERROR
    6. Read the data from the volume and verify the md5sum.
    """
    replica_count = 3
    volume = create_and_check_volume(client, volume_name, replica_count)
    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
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

    crashed_replica = None
    for rep in volume.replicas:
        if rep["name"] == replica["name"]:
            crashed_replica = rep
            break

    assert crashed_replica["running"] is False
    assert crashed_replica["mode"] == ""
    assert crashed_replica["failedAt"] is not None

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

    hostId = get_self_host_id()
    volume = create_and_check_volume(client, volume_name, num_of_replicas=3)

    volume = volume.attach(hostId=hostId)
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
    assert volume.robustness == "healthy"

    check_volume_data(volume, data)


@pytest.mark.skip(reason="TODO") # NOQA
def test_disable_replica_rebuild():
    """
    Test disable replica rebuild

    1. Disable node scheduling on node-2 and node-3. To make sure
    replica scheduled on node-1.
    2. Set 'Disable Replica Rebuild' to true.
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
    12. Set 'Disable Replica Rebuild' to false, and wait for replica
    rebuild and volume becomes 'healthy' state with 2 replicas.
    13. Set 'Disable Replica Rebuild' to True, delete one replica.
    14. Wait for 30 seconds, no rebuild should get triggered. The volume
    should stay in 'degraded' state with 1 replica.
    15. Set 'Disable Replica Rebuild' to false, and wait for replica
    rebuild and volume becomes 'healthy' state with 2 replicas.
    16. Clean up the volume.
    """
    pass

@pytest.mark.skip(reason="TODO") # NOQA
def test_auto_remount_with_subpath():
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
       and `datalocality: best-effort`
    2. Deploy a statefulset with `replicas: 1` and using the above storageclass
       Make sure the container in the pod template uses subpath, like this:
       ```yaml
       volumeMounts:
       - name: <PVC-NAME>
         mountPath: /mnt
         subPath: html
       ```
    3. Find the node where the statefulset pods are running.
       Let's say `pod-1` is on `node-1`, and use `vol-1`.
    4. exec into `pod-1`, create a file `test_data.txt`
       inside the folder `/mnt/html`
    5. Kill the replica instance manager pod on `node-1`.
       This action simulates a network disconnection.
    6. in a 2 minutes retry loop:
       Exec into the `pod-1`, run `ls /mnt/html`.
       Verify the file `test_data.txt` exists.

    7. Kill the replica instance manager pod on `node-1` one more time.
    8. Wait for volume to become healthy,
       kill the replica instance manager pod on `node-1` one more time.
    9. in a 2 minutes retry loop:
       Exec into the `pod-1`, run `ls /mnt/html`.
       Verify the file `test_data.txt` exists.

    10. Update `numberOfReplicas` to 3.
        Wait for replicas rebuilding finishes.
    11. Kill the engine instance manager pod on `node-1`
    12. In a 2 minutes retry loop:
       Exec into the `pod-1`, run `ls /mnt/html`.
       Verify the file `test_data.txt` exists.

    13. kill `pod-1`.
    14. In a 2 minutes retry loop:
       Exec into the `pod-1`, run `ls /mnt/html`.
       Verify the file `test_data.txt` exists.
    """
    pass


@pytest.mark.skip(reason="TODO") # NOQA
def test_reuse_failed_replica():
    """
    Steps:
    1. Set a long wait interval for
       setting `replica-replenishment-wait-interval`.
    2. Disable the setting soft node anti-affinity.
    3. Create and attach a volume. Then write data to the volume.
    4. Disable the scheduling for a node.
    5. Crash the replica on the node.
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
    pass


@pytest.mark.skip(reason="TODO") # NOQA
def test_reuse_failed_replica_with_scheduling_check():
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
    pass
