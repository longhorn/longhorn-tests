import common
import pytest
import time

from common import RETRY_COUNTS, RETRY_INTERVAL
from common import client, core_api  # NOQA
from common import storage_class, statefulset, pod  # NOQA
from common import sts_name, volume_name  # NOQA
from common import check_volume_data, cleanup_volume, \
    create_and_check_volume, get_longhorn_api_client, get_self_host_id, \
    wait_for_volume_detached, wait_for_volume_degraded, \
    wait_for_volume_healthy, wait_scheduling_failure, \
    write_volume_random_data, wait_for_rebuild_complete
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import SETTING_DEFAULT_DATA_LOCALITY
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import write_pod_volume_random_data
from common import wait_for_volume_replica_count

from common import Mi, Gi, DATA_SIZE_IN_MB_2, DATA_SIZE_IN_MB_4
from common import create_and_wait_pod
from common import settings_reset # NOQA
from common import wait_for_rebuild_start
from common import delete_and_wait_pod
from common import wait_for_replica_failed
from common import crash_engine_process_with_sigkill
from common import wait_for_replica_running

from time import sleep


@pytest.yield_fixture(autouse=True)
def reset_settings():
    yield
    client = get_longhorn_api_client()  # NOQA
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=True)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="true")


def get_host_replica(volume, host_id):
    """
    Get the replica of the volume that is running on the test host. Trigger a
    failed assertion if it can't be found.
    :param volume: The volume to get the replica from.
    :param host_id: The ID of the test host.
    :return: The replica hosted on the test host.
    """
    host_replica = None
    for i in volume.replicas:
        if i.hostId == host_id:
            host_replica = i
    assert host_replica is not None
    return host_replica


# We check to make sure the replica is found, running, and in RW mode (not
# rebuilding) since the longhorn-engine has the latest status compared to
# longhorn-manager, which might be in an intermediate state.
def wait_new_replica_ready(client, volume_name, replica_names):  # NOQA
    """
    Wait for a new replica to be found on the specified volume. Trigger a
    failed assertion if one can't be found.
    :param client: The Longhorn client to use in the request.
    :param volume_name: The name of the volume.
    :param replica_names: The list of names of the volume's old replicas.
    """
    new_replica_ready = False
    wait_for_rebuild_complete(client, volume_name)
    for _ in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        for r in v.replicas:
            if r["name"] not in replica_names and r["running"] and \
                    r["mode"] == "RW":
                new_replica_ready = True
                break
        if new_replica_ready:
            break
        sleep(RETRY_INTERVAL)
    assert new_replica_ready


def test_soft_anti_affinity_scheduling(client, volume_name):  # NOQA
    """
    Test that volumes with Soft Anti-Affinity work as expected.

    With Soft Anti-Affinity, a new replica should still be scheduled on a node
    with an existing replica, which will result in "Healthy" state but limited
    redundancy.

    1. Create a volume and attach to the current node
    2. Generate and write `data` to the volume.
    3. Set `soft anti-affinity` to true
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
    6. Wait for the volume to complete rebuild. Volume should have 3 replicas.
    7. Verify `data`
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="true")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = list(map(lambda replica: replica.name, volume.replicas))
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_soft_anti_affinity_detach(client, volume_name):  # NOQA
    """
    Test that volumes with Soft Anti-Affinity can detach and reattach to a
    node properly.

    1. Create a volume and attach to the current node.
    2. Generate and write `data` to the volume
    3. Set `soft anti-affinity` to true
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
    6. Wait for the new replica to be rebuilt
    7. Detach the volume.
    8. Verify there are 3 replicas
    9. Attach the volume again. Verify there are still 3 replicas
    10. Verify the `data`.
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="true")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = list(map(lambda replica: replica.name, volume.replicas))
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == 3

    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_scheduling(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity work as expected.

    With Hard Anti-Affinity, scheduling on nodes with existing replicas should
    be forbidden, resulting in "Degraded" state.

    1. Create a volume and attach to the current node
    2. Generate and write `data` to the volume.
    3. Set `soft anti-affinity` to false
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
        1. Verify volume will be in degraded state.
        2. Verify volume reports condition `scheduled == false`
        3. Verify only two of three replicas of volume are healthy.
        4. Verify the remaining replica doesn't have `replica.HostID`, meaning
        it's unscheduled
    6. Check volume `data`
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    # Instead of waiting for timeout and lengthening the tests a significant
    # amount we can make sure the scheduling isn't working by making sure the
    # volume becomes Degraded and reports a scheduling error.
    wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    # While there are three replicas that should exist to meet the Volume's
    # request, only two of those volumes should actually be Healthy.
    volume = client.by_id_volume(volume_name)
    assert sum([1 for replica in volume.replicas if replica.running and
                replica.mode == "RW"]) == 2
    # Confirm that the final volume is an unscheduled volume.
    assert sum([1 for replica in volume.replicas if
                not replica.hostId]) == 1
    # Three replicas in total should still exist.
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_detach(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity are still able to detach and
    reattach to a node properly, even in degraded state.

    1. Create a volume and attach to the current node
    2. Generate and write `data` to the volume.
    3. Set `soft anti-affinity` to false
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
        1. Verify volume will be in degraded state.
        2. Verify volume reports condition `scheduled == false`
    6. Detach the volume.
    7. Verify that volume only have 2 replicas
        1. Unhealthy replica will be removed upon detach.
    8. Attach the volume again.
        1. Verify volume will be in degraded state.
        2. Verify volume reports condition `scheduled == false`
        3. Verify only two of three replicas of volume are healthy.
        4. Verify the remaining replica doesn't have `replica.HostID`, meaning
        it's unscheduled
    9. Check volume `data`
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == 2

    volume.attach(hostId=host_id)
    # Make sure we're still not getting another successful replica.
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    assert sum([1 for replica in volume.replicas if replica.running and
                replica.mode == "RW"]) == 2
    assert sum([1 for replica in volume.replicas if
                not replica.hostId]) == 1
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_live_rebuild(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity can build new replicas live once
    a valid node is available.

    If no nodes without existing replicas are available, the volume should
    remain in "Degraded" state. However, once one is available, the replica
    should now be scheduled successfully, with the volume returning to
    "Healthy" state.

    1. Create a volume and attach to the current node
    2. Generate and write `data` to the volume.
    3. Set `soft anti-affinity` to false
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
        1. Verify volume will be in degraded state.
        2. Verify volume reports condition `scheduled == false`
    6. Enable the current node's scheduling
    7. Wait for volume to start rebuilding and become healthy again
    8. Check volume `data`
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume.replicas)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    # Allow scheduling on host node again
    client.update(node, allowScheduling=True)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_offline_rebuild(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity can build new replicas during
    the attaching process once a valid node is available.

    Once a new replica has been built as part of the attaching process, the
    volume should be Healthy again.

    1. Create a volume and attach to the current node
    2. Generate and write `data` to the volume.
    3. Set `soft anti-affinity` to false
    4. Disable current node's scheduling.
    5. Remove the replica on the current node
        1. Verify volume will be in degraded state.
        2. Verify volume reports condition `scheduled == false`
    6. Detach the volume.
    7. Enable current node's scheduling.
    8. Attach the volume again.
    9. Wait for volume to become healthy with 3 replicas
    10. Check volume `data`
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume.replicas)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica.name)
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    client.update(node, allowScheduling=True)
    volume.attach(hostId=host_id)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume.replicas) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_replica_rebuild_per_volume_limit(
    client, core_api, storage_class, sts_name, statefulset):  # NOQA
    """
    Test the volume always only have one replica scheduled for rebuild

    1. Set soft anti-affinity to `true`.
    2. Create a volume with 1 replica.
    3. Attach the volume and write a few hundreds MB data to it.
    4. Scale the volume replica to 5.
    5. Constantly checking the volume replica list to make sure there should be
       only 1 replica in WO state.
    6. Wait for the volume to complete rebuilding. Then remove 4 of the 5
       replicas.
    7. Monitoring the volume replica list again.
    8. Once the rebuild was completed again, verify the data checksum.
    """
    replica_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_soft_anti_affinity_setting, value="true")

    data_path = '/data/test'
    storage_class['parameters']['numberOfReplicas'] = "1"
    vol_name, pod_name, md5sum = \
        common.prepare_statefulset_with_data_in_mb(
            client, core_api, statefulset, sts_name, storage_class,
            data_path=data_path, data_size_in_mb=DATA_SIZE_IN_MB_2)

    # Scale the volume replica to 5
    r_count = 5
    vol = client.by_id_volume(vol_name)
    vol.updateReplicaCount(replicaCount=r_count)

    vol = common.wait_for_volume_replicas_mode(client, vol_name, 'RW',
                                               replica_count=r_count)

    # Delete 4 volume replicas
    del vol.replicas[0]
    for r in vol.replicas:
        vol.replicaRemove(name=r.name)

    r_count = 1
    common.wait_for_volume_replicas_mode(client, vol_name, 'RW',
                                         replica_count=r_count)

    assert md5sum == common.get_pod_data_md5sum(core_api, pod_name, data_path)


def test_data_locality_basic(client, core_api, volume_name, pod, settings_reset):  # NOQA
    """
    Test data locality basic feature

    Context:

    Data Locality feature allows users to have an option to keep a local
    replica on the same node as the consuming pod.
    Longhorn is currently supporting 2 modes:
    - disabled: Longhorn does not try to keep a local replica
    - best-effort: Longhorn try to keep a local replica

    See manual tests at:
    https://github.com/longhorn/longhorn/issues/1045#issuecomment-680706283

    Steps:

    1. Create a volume(1) with 1 replica and dataLocality set to disabled
    2. Find node where the replica is located on.
       Let's call the node is replica-node
    3. Attach the volume to a node different than replica-node.
       Let call the node is engine-node
    4. Write 200MB data to volume(1)
    5. Use a retry loop to verify that Longhorn does not create
       a replica on the engine-node
    6. Update dataLocality to best-effort for volume(1)
    7. Use a retry loop to verify that Longhorn creates and rebuilds
       a replica on the engine-node and remove the other replica
    8. detach the volume(1) and attach it to a different node.
       Let's call the new node is new-engine-node and the old
       node is old-engine-node
    9. Wait for volume(1) to finish attaching
    10. Use a retry loop to verify that Longhorn creates and rebuilds
       a replica on the new-engine-node and remove the replica on
       old-engine-node
    11. Update dataLocality to disabled for volume(1)
    12. detach the volume(1) and attach it to a different node.
       Let's call the new node is new-engine-node and the old
       node is old-engine-node
    13. Wait for volume(1) to finish detaching
    14. Use a retry loop to verify that Longhorn does not create
        a replica on the new-engine-node

    15. Add the tag AVAIL to node-1 and node-2
    16. Set node soft anti-affinity to `true`.
    17. Create a volume(2) with 3 replicas and dataLocality set to best-effort
    18. Use a retry loop to verify that all 3 replicas are on node-1 and
        node-2, no replica is on node-3
    19. Attach volume(2) to node-3
    20. User a retry loop to verify that there is no replica on node-3 and
        we can still read/write to volume(2)
    21. Find the node which contains 2 replicas.
        Let call the node is most-replica-node
    22. Set the replica count to 2 for volume(2)
    23. Verify that Longhorn remove one replica from most-replica-node

    24. Remove the tag AVAIL from node-1 and node-2
    25. Set node soft anti-affinity to `false`.
    26. Create a volume(3) with 1 replicas and dataLocality set to best-effort
    27. Attach volume(3) to node-3.
    28. Use a retry loop to verify that volume(3) has only 1 replica on node-3
    29. Write 10GB data to volume(3)
    30. Detach volume(3)
    31. Attach volume(3) to node-1
    32. Use a retry loop to:
        Wait until volume(3) finishes attaching.
        Wait until Longhorn start rebuilding a replica on node-1
        Immediately detach volume(3)
    33. Verify that the replica on node-1 is in ERR state.
    34. Attach volume(3) to node-1
    35. Wait until volume(3) finishes attaching.
    36. Use a retry loop to verify the Longhorn cleanup the ERR replica,
        rebuild a new replica on node-1, and remove the replica on node-3

    37. Disable scheduling for node-3
    38. Create a vol with 1 replica, `dataLocality = best-effort`.
        The replica is scheduled on a node (say node-1)
    39. Attach vol to node-3. There is a fail-to-schedule
        replica with Spec.HardNodeAffinity=node-3
    40. Increase numberOfReplica to 3. Verify that the replica set contains:
        one on node-1, one on node-2,  one failed replica
        with Spec.HardNodeAffinity=node-3.
    41. Decrease numberOfReplica to 2. Verify that the replica set contains:
        one on node-1, one on node-2,  one failed replica
        with Spec.HardNodeAffinity=node-3.
    42. Decrease numberOfReplica to 1. Verify that the replica set contains:
        one on node-1 or node-2,  one failed replica
        with Spec.HardNodeAffinity=node-3.
    43. Decrease numberOfReplica to 2. Verify that the replica set contains:
        one on node-1, one on node-2, one failed replica
        with Spec.HardNodeAffinity=node-3.
    44. Turn off data locality by set `dataLocality=disabled` for the vol.
        Verify that the replica set contains: one on node-1, one on node-2

    45. clean up
    """
    nodes = client.list_node()

    default_data_locality_setting = \
        client.by_id_setting(SETTING_DEFAULT_DATA_LOCALITY)
    try:
        client.update(default_data_locality_setting, value="disabled")
    except Exception as e:
        print("Exception when update Default Data Locality setting",
              default_data_locality_setting, e)

    volume1_name = volume_name + "-1"
    volume1_size = str(500 * Mi)
    volume1_data_path = "/data/test"
    pv1_name = volume1_name + "-pv"
    pvc1_name = volume1_name + "-pvc"
    pod1_name = volume1_name + "-pod"
    pod1 = pod

    pod1['metadata']['name'] = pod1_name

    volume1 = create_and_check_volume(client,
                                      volume1_name,
                                      num_of_replicas=1,
                                      size=volume1_size)

    volume1 = client.by_id_volume(volume1_name)
    create_pv_for_volume(client, core_api, volume1, pv1_name)
    create_pvc_for_volume(client, core_api, volume1, pvc1_name)

    volume1 = client.by_id_volume(volume1_name)
    volume1_replica_node = volume1.replicas[0]['hostId']

    volume1_attached_node = None
    for node in nodes:
        if node.name != volume1_replica_node:
            volume1_attached_node = node.name
            break

    assert volume1_attached_node is not None

    pod1['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": pvc1_name
        }
    }]

    pod1['spec']['nodeSelector'] = \
        {"kubernetes.io/hostname": volume1_attached_node}
    create_and_wait_pod(core_api, pod1)

    write_pod_volume_random_data(core_api, pod1_name,
                                 volume1_data_path, DATA_SIZE_IN_MB_2)

    for i in range(10):
        volume1 = client.by_id_volume(volume1_name)
        assert len(volume1.replicas) == 1
        assert volume1.replicas[0]['hostId'] != volume1_attached_node
        time.sleep(1)

    volume1 = client.by_id_volume(volume1_name)
    volume1.updateDataLocality(dataLocality="best-effort")

    wait_for_rebuild_start(client, volume1_name)

    volume1 = wait_for_volume_replica_count(client, volume1_name, 2)
    volume1 = client.by_id_volume(volume1_name)
    assert len(volume1.replicas) == 2

    wait_for_rebuild_complete(client, volume1_name)

    volume1 = wait_for_volume_replica_count(client, volume1_name, 1)
    volume1 = client.by_id_volume(volume1_name)

    assert len(volume1.replicas) == 1
    assert volume1.replicas[0]['hostId'] == volume1_attached_node

    delete_and_wait_pod(core_api, pod1_name)
    volume1 = wait_for_volume_detached(client, volume1_name)

    volume1_replica_node = volume1.replicas[0]['hostId']

    volume1_attached_node = None
    for node in nodes:
        if node.name != volume1_replica_node:
            volume1_attached_node = node.name
            break

    assert volume1_attached_node is not None

    pod1['spec']['nodeSelector'] = \
        {"kubernetes.io/hostname": volume1_attached_node}
    create_and_wait_pod(core_api, pod1)

    wait_for_rebuild_start(client, volume1_name)

    volume1 = client.by_id_volume(volume1_name)
    assert len(volume1.replicas) == 2

    wait_for_rebuild_complete(client, volume1_name)

    volume1 = wait_for_volume_replica_count(client, volume1_name, 1)
    volume1 = client.by_id_volume(volume1_name)
    assert len(volume1.replicas) == 1
    assert volume1.replicas[0]['hostId'] == volume1_attached_node

    node1 = nodes[0]
    node2 = nodes[1]
    node3 = nodes[2]

    client.update(node1, allowScheduling=True, tags=["AVAIL"])
    client.update(node2, allowScheduling=True, tags=["AVAIL"])

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    try:
        client.update(replica_node_soft_anti_affinity_setting,
                      value="true")
    except Exception as e:
        print("Exception when update "
              "Replica Node Level Soft Anti-Affinity setting",
              replica_node_soft_anti_affinity_setting, e)

    # case 2
    volume2_name = volume_name + "-2"
    volume2_size = str(500 * Mi)
    pv2_name = volume2_name + "-pv"
    pvc2_name = volume2_name + "-pvc"
    pod2_name = volume2_name + "-pod"
    pod2 = pod

    pod2['metadata']['name'] = pod2_name

    volume2 = client.create_volume(name=volume2_name,
                                   size=volume2_size,
                                   numberOfReplicas=3,
                                   nodeSelector=["AVAIL"],
                                   dataLocality="best-effort")

    volume2 = wait_for_volume_detached(client, volume2_name)
    volume2 = client.by_id_volume(volume2_name)
    create_pv_for_volume(client, core_api, volume2, pv2_name)
    create_pvc_for_volume(client, core_api, volume2, pvc2_name)

    volume2 = client.by_id_volume(volume2_name)

    pod2['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": pvc2_name
        }
    }]

    pod2['spec']['nodeSelector'] = {"kubernetes.io/hostname": node3.name}
    create_and_wait_pod(core_api, pod2)

    volume2 = wait_for_volume_healthy(client, volume2_name)

    for replica in volume2.replicas:
        assert replica["hostId"] != node3.name

    volume2.updateReplicaCount(replicaCount=2)

    # 2 Healthy replicas and 1 replica failed to schedule
    volume2 = wait_for_volume_replica_count(client, volume2_name, 3)
    volume2 = client.by_id_volume(volume2_name)

    volume2_healthy_replicas = []
    for replica in volume2.replicas:
        if replica.running is True:
            volume2_healthy_replicas.append(replica)

    assert len(volume2_healthy_replicas) == 2

    volume2_rep1 = volume2_healthy_replicas[0]
    volume2_rep2 = volume2_healthy_replicas[1]
    assert volume2_rep1["hostId"] != volume2_rep2["hostId"]

    # case 3
    client.update(node1, allowScheduling=True, tags=[])
    client.update(node2, allowScheduling=True, tags=[])

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    try:
        client.update(replica_node_soft_anti_affinity_setting,
                      value="false")
    except Exception as e:
        print("Exception when update "
              "Replica Node Level Soft Anti-Affinity setting",
              replica_node_soft_anti_affinity_setting, e)

    volume3_name = volume_name + "-3"
    volume3_size = str(1 * Gi)
    volume3_data_path = "/data/test"
    pv3_name = volume3_name + "-pv"
    pvc3_name = volume3_name + "-pvc"
    pod3_name = volume3_name + "-pod"
    pod3 = pod

    pod3['metadata']['name'] = pod3_name

    volume3 = client.create_volume(name=volume3_name,
                                   size=volume3_size,
                                   numberOfReplicas=1)

    volume3 = wait_for_volume_detached(client, volume3_name)
    volume3 = client.by_id_volume(volume3_name)
    create_pv_for_volume(client, core_api, volume3, pv3_name)
    create_pvc_for_volume(client, core_api, volume3, pvc3_name)

    volume3 = client.by_id_volume(volume3_name)

    pod3['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": pvc3_name
        }
    }]

    pod3['spec']['nodeSelector'] = {"kubernetes.io/hostname": node3.name}
    create_and_wait_pod(core_api, pod3)
    volume3 = wait_for_volume_healthy(client, volume3_name)

    write_pod_volume_random_data(core_api, pod3_name,
                                 volume3_data_path, DATA_SIZE_IN_MB_4)

    volume3.updateDataLocality(dataLocality="best-effort")
    volume3 = client.by_id_volume(volume3_name)

    if volume3.replicas[0]['hostId'] != node3.name:
        wait_for_rebuild_start(client, volume3_name)
        volume3 = client.by_id_volume(volume3_name)
        assert len(volume3.replicas) == 2
        wait_for_rebuild_complete(client, volume3_name)

    volume3 = wait_for_volume_replica_count(client, volume3_name, 1)
    assert volume3.replicas[0]["hostId"] == node3.name

    delete_and_wait_pod(core_api, pod3_name)

    pod3['spec']['nodeSelector'] = {"kubernetes.io/hostname": node1.name}
    create_and_wait_pod(core_api, pod3)

    wait_for_rebuild_start(client, volume3_name)
    crash_engine_process_with_sigkill(client, core_api, volume3_name)
    volume3 = client.by_id_volume(volume3_name)

    delete_and_wait_pod(core_api, pod3_name)
    wait_for_volume_detached(client, volume3_name)

    err_replica = None
    for replica in volume3.replicas:
        if replica["hostId"] == node1.name:
            err_replica = replica
            break

    assert err_replica is not None

    wait_for_replica_failed(client, volume3_name, err_replica["name"])

    volume3 = client.by_id_volume(volume3_name)
    assert len(volume3.replicas) == 1

    create_and_wait_pod(core_api, pod3)
    wait_for_rebuild_start(client, volume3_name)
    volume3 = client.by_id_volume(volume3_name)
    assert len(volume3.replicas) == 2
    wait_for_rebuild_complete(client, volume3_name)

    # Wait for deletion of extra replica
    volume3 = wait_for_volume_replica_count(client, volume3_name, 1)
    assert volume3.replicas[0]["hostId"] == node1.name
    assert volume3.replicas[0]["mode"] == "RW"
    assert volume3.replicas[0]["running"] is True

    # case 4
    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    try:
        client.update(replica_node_soft_anti_affinity_setting,
                      value="false")
    except Exception as e:
        print("Exception when update "
              "Replica Node Level Soft Anti-Affinity setting",
              replica_node_soft_anti_affinity_setting, e)

    client.update(node3, allowScheduling=False)

    volume4_name = volume_name + "-4"
    volume4_size = str(1 * Gi)

    volume4 = client.create_volume(name=volume4_name,
                                   size=volume4_size,
                                   numberOfReplicas=1,
                                   dataLocality="best-effort")

    volume4 = wait_for_volume_detached(client, volume4_name)
    volume4 = client.by_id_volume(volume4_name)

    volume4_replica_name = volume4.replicas[0]["name"]

    volume4.attach(hostId=node3.name)

    wait_for_volume_healthy(client, volume4_name)

    volume4 = client.by_id_volume(volume4_name)
    assert len(volume4.replicas) == 2

    for replica in volume4.replicas:
        if replica["name"] == volume4_replica_name:
            assert replica["running"] is True
            assert replica["mode"] == "RW"
        else:
            assert replica["running"] is False
            assert replica["mode"] == ""

    assert volume4.conditions.scheduled.reason == \
        "LocalReplicaSchedulingFailure"

    volume4 = volume4.updateReplicaCount(replicaCount=3)

    volume4 = wait_for_volume_degraded(client, volume4_name)

    v4_node1_replica_count = 0
    v4_node2_replica_count = 0
    v4_failed_replica_count = 0

    for replica in volume4.replicas:
        if replica["hostId"] == node1.name:
            v4_node1_replica_count += 1
        elif replica["hostId"] == node2.name:
            v4_node2_replica_count += 1
        elif replica["hostId"] == "":
            v4_failed_replica_count += 1

    assert v4_node1_replica_count == 1
    assert v4_node2_replica_count == 1
    assert v4_failed_replica_count > 0

    volume4 = volume4.updateReplicaCount(replicaCount=2)

    volume4 = wait_for_volume_replica_count(client, volume4_name, 3)

    v4_node1_replica_count = 0
    v4_node2_replica_count = 0
    v4_failed_replica_count = 0

    for replica in volume4.replicas:
        if replica["hostId"] == node1.name:
            v4_node1_replica_count += 1
        elif replica["hostId"] == node2.name:
            v4_node2_replica_count += 1
        elif replica["hostId"] == "":
            v4_failed_replica_count += 1

    assert v4_node1_replica_count == 1
    assert v4_node2_replica_count == 1
    assert v4_failed_replica_count > 0

    volume4 = volume4.updateReplicaCount(replicaCount=1)

    volume4 = wait_for_volume_replica_count(client, volume4_name, 2)

    v4_node1_replica_count = 0
    v4_node2_replica_count = 0
    v4_failed_replica_count = 0

    for replica in volume4.replicas:
        if replica["hostId"] == node1.name:
            v4_node1_replica_count += 1
        elif replica["hostId"] == node2.name:
            v4_node2_replica_count += 1
        elif replica["hostId"] == "":
            v4_failed_replica_count += 1

    assert v4_node1_replica_count + v4_node2_replica_count == 1
    assert v4_failed_replica_count == 1

    volume4 = volume4.updateDataLocality(dataLocality="disabled")
    volume4 = volume4.updateReplicaCount(replicaCount=2)
    wait_for_volume_healthy(client, volume4_name)
    volume4 = wait_for_volume_replica_count(client, volume4_name, 2)

    v4_node1_replica_count = 0
    v4_node2_replica_count = 0
    v4_node3_replica_count = 0

    for replica in volume4.replicas:
        wait_for_replica_running(client, volume4_name, replica["name"])
        if replica["hostId"] == node1.name:
            v4_node1_replica_count += 1
        elif replica["hostId"] == node2.name:
            v4_node2_replica_count += 1
        elif replica["hostId"] == node3.name:
            v4_node3_replica_count += 1

    assert v4_node1_replica_count == 1
    assert v4_node2_replica_count == 1
    assert v4_node3_replica_count == 0
