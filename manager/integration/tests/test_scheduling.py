import pytest

from common import RETRY_COUNTS, RETRY_INTERVAL
from common import client, volume_name  # NOQA
from common import check_volume_data, cleanup_volume, \
    create_and_check_volume, get_longhorn_api_client, get_self_host_id, \
    wait_for_volume_detached, wait_for_volume_degraded, \
    wait_for_volume_healthy, wait_scheduling_failure, write_volume_random_data
from time import sleep

SETTING_REPLICA_SOFT_ANTI_AFFINITY = "replica-soft-anti-affinity"


@pytest.yield_fixture(autouse=True)
def reset_settings():
    yield
    client = get_longhorn_api_client()  # NOQA
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=True)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
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
    for i in volume["replicas"]:
        if i["hostId"] == host_id:
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
    for _ in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        for r in v["replicas"]:
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
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="true")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume["replicas"])
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_soft_anti_affinity_detach(client, volume_name):  # NOQA
    """
    Test that volumes with Soft Anti-Affinity can detach and reattach to a
    node properly.
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="true")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume["replicas"])
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == 3

    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_scheduling(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity work as expected.

    With Hard Anti-Affinity, scheduling on nodes with existing replicas should
    be forbidden, resulting in "Degraded" state.
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    # Instead of waiting for timeout and lengthening the tests a significant
    # amount we can make sure the scheduling isn't working by making sure the
    # volume becomes Degraded and reports a scheduling error.
    wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    # While there are three replicas that should exist to meet the Volume's
    # request, only two of those volumes should actually be Healthy.
    volume = client.by_id_volume(volume_name)
    assert sum([1 for replica in volume["replicas"] if replica["running"] and
                replica["mode"] == "RW"]) == 2
    # Confirm that the final volume is an unscheduled volume.
    assert sum([1 for replica in volume["replicas"] if
                not replica["hostId"]]) == 1
    # Three replicas in total should still exist.
    assert len(volume["replicas"]) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_detach(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity are still able to detach and
    reattach to a node properly, even in degraded state.
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == 2

    volume.attach(hostId=host_id)
    # Make sure we're still not getting another successful replica.
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    assert sum([1 for replica in volume["replicas"] if replica["running"] and
                replica["mode"] == "RW"]) == 2
    assert sum([1 for replica in volume["replicas"] if
                not replica["hostId"]]) == 1
    assert len(volume["replicas"]) == 3
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
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume["replicas"])
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    # Allow scheduling on host node again
    client.update(node, allowScheduling=True)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)


def test_hard_anti_affinity_offline_rebuild(client, volume_name):  # NOQA
    """
    Test that volumes with Hard Anti-Affinity can build new replicas during
    the attaching process once a valid node is available.

    Once a new replica has been built as part of the attaching process, the
    volume should be Healthy again.
    """
    volume = create_and_check_volume(client, volume_name)
    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3

    data = write_volume_random_data(volume)
    setting = client.by_id_setting(SETTING_REPLICA_SOFT_ANTI_AFFINITY)
    client.update(setting, value="false")
    node = client.by_id_node(host_id)
    client.update(node, allowScheduling=False)
    replica_names = map(lambda replica: replica.name, volume["replicas"])
    host_replica = get_host_replica(volume, host_id)

    volume.replicaRemove(name=host_replica["name"])
    volume = wait_for_volume_degraded(client, volume_name)
    wait_scheduling_failure(client, volume_name)
    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    client.update(node, allowScheduling=True)
    volume.attach(hostId=host_id)
    wait_new_replica_ready(client, volume_name, replica_names)
    volume = wait_for_volume_healthy(client, volume_name)
    assert len(volume["replicas"]) == 3
    check_volume_data(volume, data)

    cleanup_volume(client, volume)
