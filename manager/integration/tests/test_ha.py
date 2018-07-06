import common
import time

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import check_data, get_self_host_id
from common import write_random_data
from common import RETRY_COUNTS, RETRY_ITERVAL


def test_ha_simple_recovery(clients, volume_name):  # NOQA
    # get a random client
    for _, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume["endpoint"] == DEV_PATH + volume_name

    assert len(volume["replicas"]) == 2
    replica0 = volume["replicas"][0]
    assert replica0["name"] != ""

    replica1 = volume["replicas"][1]
    assert replica1["name"] != ""

    data = write_random_data(volume["endpoint"])

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

    volume = common.wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)
    assert volume["state"] == common.VOLUME_STATE_ATTACHED
    assert volume["robustness"] == common.VOLUME_ROBUSTNESS_HEALTHY
    assert len(volume["replicas"]) >= 2

    found = False
    for replica in volume["replicas"]:
        if replica["name"] == replica1["name"]:
            found = True
            break
    assert found

    check_data(volume['endpoint'], data)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    common.wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


def test_ha_salvage(clients, volume_name):  # NOQA
    # get a random client
    for _, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = common.wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    assert len(volume["replicas"]) == 2
    replica0_name = volume["replicas"][0]["name"]
    replica1_name = volume["replicas"][1]["name"]

    data = write_random_data(volume["endpoint"])

    common.k8s_delete_replica_pods_for_volume(volume_name)

    volume = common.wait_for_volume_faulted(client, volume_name)
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["failedAt"] != ""
    assert volume["replicas"][1]["failedAt"] != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["failedAt"] == ""
    assert volume["replicas"][1]["failedAt"] == ""

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    check_data(volume["endpoint"], data)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    client.delete(volume)
    common.wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0
