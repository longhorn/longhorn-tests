import pytest

import common
from common import clients, volume_name  # NOQA
from common import get_random_client
from common import SIZE
from common import wait_for_volume_delete

REPLICA_COUNT = 2

@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
def test_migration_confirm(clients, volume_name):  # NOQA
    """
    Test that a migratable RWX volume can be live migrated
    from one node to another.

    1. Creates a new RWX migratable volume.
    2. Attach to test node to write some test data on it.
    3. Detach from test node.
    4. Get set of nodes excluding the test node
    5. Attach volume to node 1 (initial node)
    6. Attach volume to node 2 (migration target)
    7. Wait for migration ready (engine running on node 2)
    8. Detach volume from node 1
    9. Observe volume migrated to node 2 (single active engine)
    10. Validate initially written test data
    """
    migration_confirm_test(clients, volume_name)


def migration_confirm_test(clients, volume_name, backing_image=""):  # NOQA
    client, volume, data = setup_migration_test(clients, volume_name,
                                                backing_image)
    host1, host2 = get_hosts_for_migration_test(clients)

    volume.attach(hostId=host1)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume.attach(hostId=host2)
    volume = common.wait_for_volume_migration_ready(client, volume_name)

    volume.detach(hostId=host1)
    volume = common.wait_for_volume_migration_node(client, volume_name, host2)

    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)

    # verify test data
    check_volume_data(client, volume_name, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
def test_migration_rollback(clients, volume_name):  # NOQA
    """
    Test that a migratable RWX volume can be rolled back
    to initial node.

    1. Creates a new RWX migratable volume.
    2. Attach to test node to write some test data on it.
    3. Detach from test node.
    4. Get set of nodes excluding the test node
    5. Attach volume to node 1 (initial node)
    6. Attach volume to node 2 (migration target)
    7. Wait for migration ready (engine running on node 2)
    8. Detach volume from node 2
    9. Observe volume stayed on node 1 (single active engine)
    10. Validate initially written test data
    """
    migration_rollback_test(clients, volume_name)


def migration_rollback_test(clients, volume_name, backing_image=""):  # NOQA
    client, volume, data = setup_migration_test(clients, volume_name,
                                                backing_image)
    host1, host2 = get_hosts_for_migration_test(clients)

    volume.attach(hostId=host1)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume.attach(hostId=host2)
    volume = common.wait_for_volume_migration_ready(client, volume_name)

    volume.detach(hostId=host2)
    volume = common.wait_for_volume_migration_node(client, volume_name, host1)

    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)

    # verify test data
    check_volume_data(client, volume_name, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
@pytest.mark.skip(reason="TODO") # NOQA
def test_migration_with_unscheduled_replica(clients, volume_name):  # NOQA
    """
    Test that a degraded migratable RWX volume that contain an unscheduled
    replica can be migrated.

    1. Disable the scheduling for one node.
    2. Create a new RWX migratable volume.
    3. Attach to test node to write some test data on it.
    4. Detach from test node.
    5. Get set of nodes excluding the test node.
    6. Attach volume to node 1 (initial node).
       The volume should be Degraded with an unscheduled replica.
    7. Attach volume to node 2 (migration target)
    8. Wait for migration ready (engine running on node 2).
       The newly created migration replica count should be the same as
       that of the current replicas.
       And there is one migration replica not scheduled, either.
    9. Detach volume from node 1.
    10. Observe volume migrated to node 2 (single active engine)
    11. Enable the scheduling for the node and wait for rebuilding complete.
    12. Validate initially written test data.
    """
    return


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
@pytest.mark.skip(reason="TODO") # NOQA
def test_migration_with_failed_replica(clients, volume_name):  # NOQA
    """
    Test that a degraded migratable RWX volume that contain an failed replica
    can be migrated.

    1. Create a new RWX migratable volume.
    2. Attach to node 1 to write some test data on it.
    3. Remove the replica directory (/var/lib/longhorn/replicas) for one node.
       This makes one volume replica stay failed.
    4. Attach volume to node 2 (migration target).
    5. Wait for migration ready (engine running on node 2).
       The newly created migration replica count should be the same as
       that of the healthy current replicas.
    6. Detach volume from node 1.
    7. Observe volume migrated to node 2 (single active engine).
       And the old failed replica will be cleaned up.
    8. Validate initially written test data.
    """
    return


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
@pytest.mark.skip(reason="TODO") # NOQA
def test_migration_with_rebuilding_replica(clients, volume_name):  # NOQA
    """
    Test that a degraded migratable RWX volume that contain a rebuilding
    replica can be migrated.

    1. Create a new RWX migratable volume.
    2. Attach to node 1, then write a large amount if data on it so that
       the following rebuilding will take a while.
    3. Remove one healthy replica to trigger rebuilding.
    4. Immediately attach volume to node 2 (migration target) once
       the rebuilding starts.
       There should be no replica created before rebuilding complete.
    5. Wait for rebuilding complete then migration ready
       (engine running on node 2).
       The newly created migration replica count should be the same as
       that of the current replicas.
    6. Detach volume from node 1.
    7. Observe volume migrated to node 2 (single active engine).
    8. Validate initially written test data.
    """
    return


def get_hosts_for_migration_test(clients): # NOQA
    """
    Filters out the current node from the returned hosts list

    We use the current node for device writing before the test
    and verification of the data after the test
    """
    hosts = []
    current_host = common.get_self_host_id()
    for host in list(clients):
        if host is not current_host:
            hosts.append(host)
    return hosts[0], hosts[1]


def check_volume_data(client, volume_name, data): # NOQA
    """
    Attaches the volume to the current node
    then compares the volumes data
    against the passed data.
    """
    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=common.get_self_host_id())
    volume = common.wait_for_volume_healthy(client, volume_name)
    common.check_volume_data(volume, data)

    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)


def setup_migration_test(clients, volume_name, backing_image=""): # NOQA
    """
    Creates a new migratable volume then attaches it to the
    current node to write some test data on it.
    """
    client = get_random_client(clients)
    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT,
                                  backingImage=backing_image,
                                  accessMode="rwx", migratable=True)
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=common.get_self_host_id())
    volume = common.wait_for_volume_healthy(client, volume_name)

    # write test data
    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)
    return client, volume, data
