import pytest

from common import RETRY_COUNTS, RETRY_INTERVAL
from common import client, volume_name  # NOQA
from common import check_volume_data, cleanup_volume, \
    create_and_check_volume, get_longhorn_api_client, get_self_host_id, \
    wait_for_volume_detached, wait_for_volume_degraded, \
    wait_for_volume_healthy, wait_scheduling_failure, \
    write_volume_random_data, wait_for_rebuild_complete
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
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


@pytest.mark.skip(reason="TODO")
def test_replica_rebuild_per_volume_limit():
    """
    Test the volume always only have one replica scheduled for rebuild

    1. Set soft anti-affinity to `true`.
    2. Create a volume with one replicas.
    3. Attach the volume and write a few hundreds MB data to it.
    4. Scale the volume replica to 5.
    5. Constantly checking the volume replica list to make sure there should be
    at most one replica which is not in the RW state. It should be:
        1. Either in the WO state
        2. Doesn't have any state because it's preparing for the rebuild.
    6. Wait for the volume to complete rebuilding. Then remove 4 of the 5
    replicas.
    7. Monitoring the volume replica list again.
    8. Once the rebuild was completed again, delete the volume and reset the
    setting.

    """
    pass


@pytest.mark.skip(reason="TODO")
def test_replica_rebuild_concurrent_limit():
    """
    Test setting ReplicaRebuildConcurrentLimit

    1. Create 3 volumes, each with 3 replicas.
    2. Attach the volumes and write a few hundreds MB data into each of them.
    3. Set ReplicaRebuildConcurrentLimit to 0.
    4. Delete two of the three replicas for every volume.
    5. Wait for 60 seconds. Check the volume's replica list, make sure no
    rebuild happened.
    6. Set ReplicaRebuildConcurrentLimit to 1.
    7. Monitoring the three volumes, the maximum number of rebuilding replica
    of those three volumes should be 1.
        1. Make sure there is at least one time we observed one replica is
        being rebuilt.
    8. Wait for the rebuild to finish. Check the correctness of the data.
    9. Set ReplicaRebuildConcurrentLimit to 0.
    10. Delete two of the the replicas for every volume.
    11. Set ReplicaRebuildConcurrentLimit to 10.
    12. Monitoring the three volumes, the maximum number of rebuilding replica
    of those three volumes should be 3 (due to the per volume limit).
        1. Make sure there is at least one time we observed three replica is
        being rebuilt.
    13. Cleanup the volume

    """
    pass
