import pytest
import subprocess
import common
from common import clients, volume_name, wait_for_volume_healthy  # NOQA
from common import get_random_client
from common import SIZE
from common import wait_for_volume_delete
from common import set_node_scheduling
from common import get_volume_endpoint, write_volume_dev_random_mb_data
from common import get_device_checksum
from common import wait_for_rebuild_start, wait_for_rebuild_complete
from common import Gi
from test_scheduling import get_host_replica

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
    check_detached_volume_data(client, volume_name, data)

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
    check_detached_volume_data(client, volume_name, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
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
    # Step 1
    client = get_random_client(clients) # NOQA

    # local_node : write data / migrate target
    # hosts[0] : migrate initial node
    # hosts[1] : node to schedule on/off
    local_node = common.get_self_host_id()
    hosts = get_hosts_for_migration_test(clients)
    schedule_node = client.by_id_node(hosts[1])

    set_node_scheduling(client, schedule_node,
                        allowScheduling=False, retry=True)

    # Step 2,3,4
    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=3,
                                  backingImage="",
                                  accessMode="rwx", migratable=True)
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=local_node)
    volume = common.wait_for_volume_degraded(client, volume_name)

    data = common.write_volume_random_data(volume)
    common.check_volume_data(volume, data)

    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)
    old_replicas = []
    v = client.by_id_volume(volume_name)
    replicas = v.replicas
    for r in replicas:
        old_replicas.append(r.name)

    # Step 6
    volume.attach(hostId=hosts[0])
    volume = common.wait_for_volume_degraded(client, volume_name)

    # Step 7
    volume.attach(hostId=local_node)

    # Step 8
    volume = common.wait_for_volume_migration_ready(client, volume_name)
    volume = common.wait_for_volume_degraded(client, volume_name)

    new_replicas = []
    v = client.by_id_volume(volume_name)
    replicas = v.replicas
    for r in replicas:
        if r.name not in old_replicas:
            new_replicas.append(r.name)

    assert len(old_replicas) == len(new_replicas)

    # Step 9
    volume.detach(hostId=hosts[0])

    # Step 10
    volume = common.wait_for_volume_migration_node(client,
                                                   volume_name,
                                                   local_node)

    # Step 11
    set_node_scheduling(client, schedule_node,
                        allowScheduling=True, retry=True)
    volume = common.wait_for_volume_healthy(client, volume_name)

    # Step 12
    common.check_volume_data(volume, data)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
def test_migration_with_failed_replica(clients, request, volume_name):  # NOQA
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
    def finalizer():
        exec_cmd = ["mkdir", "-p", "/var/lib/longhorn/replicas"]
        subprocess.check_output(exec_cmd)

    request.addfinalizer(finalizer)

    client, volume, data = setup_migration_test(clients,
                                                volume_name,
                                                replica_cnt=3)

    current_node = common.get_self_host_id()
    hosts = get_hosts_for_migration_test(clients)
    migrate_target = hosts[0]
    volume.attach(hostId=current_node)
    volume = common.wait_for_volume_healthy(client, volume_name)

    old_replicas = []
    for replica in volume.replicas:
        old_replicas.append(replica.name)

    exec_cmd = ["rm", "-rf",  "/var/lib/longhorn/replicas"]
    subprocess.check_output(exec_cmd)
    volume = common.wait_for_volume_degraded(client, volume_name)

    volume.attach(hostId=migrate_target)
    volume = common.wait_for_volume_migration_ready(client, volume_name)

    new_replicas = 0
    for replica in volume.replicas:
        if replica.hostId == current_node:
            assert replica.running is False
        else:
            assert replica.running is True
            if replica.name not in old_replicas:
                new_replicas = new_replicas + 1
    assert new_replicas == 2

    volume.detach(hostId=current_node)

    volume = common.wait_for_volume_migration_node(client,
                                                   volume_name,
                                                   migrate_target)

    volume.updateReplicaCount(replicaCount=2)
    volume = common.wait_for_volume_healthy(client, volume_name)
    volume.detach(hostId="")
    volume = common.wait_for_volume_detached(client, volume_name)
    volume = client.by_id_volume(volume_name)
    check_detached_volume_data(client, volume_name, data)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
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
    # Step 1
    client = get_random_client(clients)  # NOQA
    current_host = common.get_self_host_id()
    host1, host2 = get_hosts_for_migration_test(clients)

    # Step 2
    volume = client.create_volume(name=volume_name, size=str(2 * Gi),
                                  numberOfReplicas=3,
                                  backingImage="",
                                  accessMode="rwx", migratable=True)
    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=current_host)
    volume = common.wait_for_volume_healthy(client, volume_name)
    old_replicas = volume.replicas

    volume_endpoint = get_volume_endpoint(volume)
    write_volume_dev_random_mb_data(volume_endpoint,
                                    1, 1500)
    data = get_device_checksum(volume_endpoint)

    # Step 3
    host_replica = get_host_replica(volume, host_id=current_host)
    volume.replicaRemove(name=host_replica.name)

    # Step 4
    wait_for_rebuild_start(client, volume_name)

    volume.attach(hostId=host1)
    volume = client.by_id_volume(volume_name)
    assert len(volume.replicas) == len(old_replicas)

    wait_for_rebuild_complete(client, volume_name)

    # Step 5
    volume = common.wait_for_volume_migration_ready(client, volume_name)
    new_replicas = volume.replicas
    assert len(old_replicas) == (len(new_replicas) - len(old_replicas))

    # Step 6
    volume.detach(hostId=current_host)

    # Step 7
    volume = common.wait_for_volume_migration_node(client,
                                                   volume_name,
                                                   host1)
    volume = common.wait_for_volume_healthy(client, volume_name)

    replicas = volume.replicas
    assert len(replicas) == len(old_replicas)

    # Step 8
    volume.detach(hostId=host1)

    volume = common.wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=current_host)
    volume = common.wait_for_volume_healthy(client, volume_name)
    volume_endpoint = get_volume_endpoint(volume)
    assert data == get_device_checksum(volume_endpoint)


@pytest.mark.coretest  # NOQA
@pytest.mark.migration # NOQA
@pytest.mark.skip(reason="TODO") # NOQA
def test_migration_with_restore_volume(clients, volume_name):  # NOQA
    """
    Test that a restored volume can be migrated.

    1. Prepare one backup.
    2. Create a StorageClass with `migratable` being enabled and
       `fromBackup` pointing to the above backup.
    3. Create a new RWX migratable volume using the StorageClass.
    2. Attach to node 1, then write some data.
    4. Attach the volume to node 2 (migration target).
    5. Wait for the migration ready. Verify that field
       `volume.controllers[0].requestedBackupRestore` is empty.
    6. Confirm the migration then validate the data.
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
        if host != current_host:
            hosts.append(host)
    return hosts[0], hosts[1]


def check_detached_volume_data(client, volume_name, data): # NOQA
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


def setup_migration_test(clients, volume_name, backing_image="", replica_cnt=REPLICA_COUNT): # NOQA
    """
    Creates a new migratable volume then attaches it to the
    current node to write some test data on it.
    """
    client = get_random_client(clients)
    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=replica_cnt,
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
