import common
import time

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import wait_for_volume_state, wait_for_volume_delete
from common import RETRY_COUNTS, RETRY_ITERVAL


def test_ha_simple_recovery(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = client.by_id_volume(volume_name)
    assert volume["endpoint"] == DEV_PATH + volume_name

    assert len(volume["replicas"]) == 2
    replica0 = volume["replicas"][0]
    assert replica0["name"] != ""

    replica1 = volume["replicas"][1]
    assert replica1["name"] != ""

    volume = volume.replicaRemove(name=replica0["name"])

    # wait until we saw a replica starts rebuilding
    new_replica_found = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        for r in v["replicas"]:
            if r["name"] != replica0["name"] and \
                    r["name"] != replica1["name"]:
                new_replica_found = True
                break
        if new_replica_found:
            break
        time.sleep(RETRY_ITERVAL)
    assert new_replica_found

    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = client.by_id_volume(volume_name)
    assert volume["state"] == "healthy"
    assert len(volume["replicas"]) >= 2

    found = False
    for replica in volume["replicas"]:
        if replica["name"] == replica1["name"]:
            found = True
            break
    assert found

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_ha_salvage(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    assert len(volume["replicas"]) == 2
    replica0_name = volume["replicas"][0]["name"]
    replica1_name = volume["replicas"][1]["name"]

    common.k8s_delete_replica_pods_for_volume(volume_name)

    volume = wait_for_volume_state(client, volume_name, "faulted")
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["badTimestamp"] != ""
    assert volume["replicas"][1]["badTimestamp"] != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = wait_for_volume_state(client, volume_name, "detached")
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["badTimestamp"] == ""
    assert volume["replicas"][1]["badTimestamp"] == ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0
