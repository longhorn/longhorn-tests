import pytest
import common
import time
import random

from common import client, core_api, volume_name  # NOQA
from common import SIZE, DEV_PATH, VOLUME_RWTEST_SIZE, EXPAND_SIZE, Gi
from common import check_volume_data, cleanup_volume, create_and_check_volume
from common import delete_replica_processes, crash_replica_processes
from common import get_self_host_id, get_volume_endpoint
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
from common import write_pod_volume_data, write_pod_volume_random_data
from common import wait_for_volume_healthy, wait_for_volume_degraded
from common import read_volume_data
from common import get_pod_data_md5sum
from common import wait_for_pod_remount
from common import get_liveness_probe_spec
from common import delete_and_wait_pod
from common import delete_and_wait_pvc, delete_and_wait_pv
from common import wait_for_rebuild_start
from kubernetes.stream import stream

RANDOM_DATA_SIZE = 300


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
    assert get_volume_endpoint(volume) == DEV_PATH + volname

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
    restored backup, delete a replica when restoring in progress.
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


def test_salvage_auto_crash_all_replicas(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature by crashing all the replicas

    1. Create PV/PVC/POD. Make sure POD has liveness check. Start the pod
    2. Generate `test_data` and write to the pod.
    3. Run `sync` command inside the pod to make sure data flush to the volume.
    4. Crash all replica processes using SIGTERM
    5. Wait for volume to `faulted`, then `healthy`
    6. Check replica `failedAt` has been cleared.
    7. Wait for pod to be restarted.
    8. Check pod `test_data`.

    FIXME: Step 5 is only a intermediate state, maybe no way to get it for sure
    """
    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)

    pod_liveness_probe_spec = get_liveness_probe_spec(initial_delay=1,
                                                      period=1)

    pod['spec']['containers'][0]['livenessProbe'] = pod_liveness_probe_spec

    volume = create_and_check_volume(client, volume_name, num_of_replicas=2)

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    write_pod_volume_data(core_api, pod_name, test_data)

    stream(core_api.connect_get_namespaced_pod_exec,
           pod_name,
           'default',
           command="sync",
           stderr=True, stdin=True,
           stdout=True, tty=True,
           _preload_content=False)

    crash_replica_processes(client, core_api, volume_name)

    # this line may fail if the recovery is too quick
    common.wait_for_volume_faulted(client, volume_name)

    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    wait_for_pod_remount(core_api, pod_name)

    resp = read_volume_data(core_api, pod_name)

    assert test_data == resp

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


# Test case #2: delete one replica process, wait for 5 seconds
# then delete all replica processes.
def test_salvage_auto_crash_replicas_short_wait(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature, with replica building pending

    1. Create a PV/PVC/Pod with liveness check.
    2. Create volume and start the pod.
    3. Generate `test_data` and write to the pod.
    4. Run `sync` command inside the pod to make sure data flush to the volume.
    5. Crash one of the replica. Wait for 5 seconds.
    6. Crash all the replicas.
    7. Make sure volume and Pod recovers.
    8. Check `test_data` in the Pod.

    FIXME: step 5 should wait for the replica to start rebuilding.
    """
    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)

    pod_liveness_probe_spec = get_liveness_probe_spec(initial_delay=1,
                                                      period=1)

    pod['spec']['containers'][0]['livenessProbe'] = pod_liveness_probe_spec

    volume = create_and_check_volume(client, volume_name, num_of_replicas=2)

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    write_pod_volume_data(core_api, pod_name, test_data)

    stream(core_api.connect_get_namespaced_pod_exec,
           pod_name,
           'default',
           command="sync",
           stderr=True, stdin=True,
           stdout=True, tty=True,
           _preload_content=False)

    volume = client.by_id_volume(volume_name)
    replica0 = volume.replicas[0]

    crash_replica_processes(client, core_api, volume_name, [replica0])

    time.sleep(5)

    volume = client.by_id_volume(volume_name)

    replicas = []
    for r in volume.replicas:
        if r.running is True:
            replicas.append(r)

    crash_replica_processes(client, core_api, volume_name, replicas)

    volume = common.wait_for_volume_faulted(client, volume_name)

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 2
    assert volume.replicas[0].failedAt == ""
    assert volume.replicas[1].failedAt == ""

    volume = wait_for_volume_healthy(client, volume_name)

    wait_for_pod_remount(core_api, pod_name)

    resp = read_volume_data(core_api, pod_name)

    assert test_data == resp

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


# Test case #3: delete one replica process, wait for 60 seconds
# then delete all replica processes.
def test_salvage_auto_crash_replicas_long_wait(client, core_api, volume_name, pod_make):  # NOQA
    """
    [HA] Test automatic salvage feature, with replica building pending

    1. Create a PV/PVC/Pod with liveness check.
    2. Create volume and start the pod.
    3. Generate `test_data` and write to the pod.
    4. Run `sync` command inside the pod to make sure data flush to the volume.
    5. Crash one of the replica. Wait for 60 seconds.
    6. Crash all the replicas.
    7. Make sure volume and Pod recovers.
    8. Check `test_data` in the Pod.

    FIXME: step 5 should wait for the replica to finish rebuilding.
    FIXME: should create common function with the previous couple test cases
    """
    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)

    pod_liveness_probe_spec = get_liveness_probe_spec(initial_delay=1,
                                                      period=1)

    pod['spec']['containers'][0]['livenessProbe'] = pod_liveness_probe_spec

    volume = create_and_check_volume(client, volume_name, num_of_replicas=2)

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    write_pod_volume_data(core_api, pod_name, test_data)

    stream(core_api.connect_get_namespaced_pod_exec,
           pod_name,
           'default',
           command="sync",
           stderr=True, stdin=True,
           stdout=True, tty=True,
           _preload_content=False)

    volume = client.by_id_volume(volume_name)
    replica0 = volume.replicas[0]

    crash_replica_processes(client, core_api, volume_name, [replica0])

    time.sleep(60)

    volume = client.by_id_volume(volume_name)

    replicas = []
    for r in volume.replicas:
        if r.running is True:
            replicas.append(r)

    crash_replica_processes(client, core_api, volume_name, replicas)

    volume = common.wait_for_volume_faulted(client, volume_name)

    volume = common.wait_for_volume_detached_unknown(client, volume_name)
    assert len(volume.replicas) == 3

    volume = wait_for_volume_healthy(client, volume_name)

    wait_for_pod_remount(core_api, pod_name)

    resp = read_volume_data(core_api, pod_name)

    assert test_data == resp

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


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
    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)
    pod_liveness_probe_spec = get_liveness_probe_spec(initial_delay=1,
                                                      period=1)
    pod['spec']['containers'][0]['livenessProbe'] = pod_liveness_probe_spec

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3, size=str(1 * Gi))
    assert len(volume.replicas) == 3
    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    data_path_1 = "/data/test1"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path_1, RANDOM_DATA_SIZE)
    original_md5sum_1 = get_pod_data_md5sum(core_api, pod_name, data_path_1)
    create_snapshot(client, volume_name)
    data_path_2 = "/data/test2"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path_2, RANDOM_DATA_SIZE)
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
