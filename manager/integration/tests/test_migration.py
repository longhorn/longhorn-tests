import pytest

import common
from common import clients, volume_name  # NOQA
from common import get_volume_attached_nodes
from common import get_random_client
from common import SIZE
from common import wait_for_volume_delete

REPLICA_COUNT = 2


@pytest.mark.coretest  # NOQA
def test_migration_confirm(clients, volume_name):  # NOQA
    migration_confirm_test(clients, volume_name)


def migration_confirm_test(clients, volume_name, base_image=""):  # NOQA
    client = get_random_client(clients)
    hosts = clients.keys()
    host1 = hosts[0]
    host2 = hosts[1]

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT,
                                  baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host1)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = volume.migrationStart(nodeId=host2)
    attached_nodes = get_volume_attached_nodes(volume)
    assert host1 in attached_nodes
    assert volume["migrationNodeID"] == host2
    with pytest.raises(Exception) as e:
        volume.migrationConfirm()
    assert "migration is not ready" in str(e.value)

    volume = common.wait_for_volume_migration_ready(client, volume_name)
    volume = volume.migrationConfirm()
    volume = common.wait_for_volume_migration_node(client,
                                                   volume_name,
                                                   host2)
    assert volume["migrationNodeID"] == ""

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    client.delete(volume)

    wait_for_volume_delete(client, volume_name)


@pytest.mark.coretest  # NOQA
def test_migration_rollback(clients, volume_name):  # NOQA
    migration_rollback_test(clients, volume_name)


def migration_rollback_test(clients, volume_name, base_image=""):  # NOQA
    client = get_random_client(clients)
    hosts = clients.keys()
    host1 = hosts[0]
    host2 = hosts[1]

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT,
                                  baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host1)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = volume.migrationStart(nodeId=host2)
    attached_nodes = get_volume_attached_nodes(volume)
    assert host1 in attached_nodes
    assert volume["migrationNodeID"] == host2

    volume = common.wait_for_volume_migration_ready(client, volume_name)
    volume = volume.migrationRollback()
    volume = common.wait_for_volume_migration_node(client, volume_name, host1)
    assert volume["migrationNodeID"] == ""

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    client.delete(volume)

    wait_for_volume_delete(client, volume_name)
