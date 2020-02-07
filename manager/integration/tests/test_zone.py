import pytest
import time

from common import client # NOQA
from common import core_api  # NOQA
from common import create_and_check_volume
from common import get_self_host_id
from common import RETRY_COUNTS
from common import RETRY_INTERVAL
from common import volume_name # NOQA
from common import wait_for_volume_degraded
from common import wait_for_volume_healthy
from common import wait_for_volume_replica_count
from random import randrange
from test_scheduling import wait_new_replica_ready
from common import get_version_api_client


# label deprecated for k8s >= v1.17
DEPRECATED_K8S_ZONE_LABEL = "failure-domain.beta.kubernetes.io/zone"

K8S_ZONE_LABEL = "topology.kubernetes.io/zone"

ZONE1 = "lh-zone1"
ZONE2 = "lh-zone2"


def get_k8s_zone_label():
    ver_api = get_version_api_client()
    k8s_ver_data = ver_api.get_code()

    k8s_ver_major = k8s_ver_data.major
    assert k8s_ver_major == '1'

    k8s_ver_minor = k8s_ver_data.minor

    if int(k8s_ver_minor) >= 17:
        k8s_zone_label = K8S_ZONE_LABEL
    else:
        k8s_zone_label = DEPRECATED_K8S_ZONE_LABEL

    return k8s_zone_label


@pytest.fixture
def k8s_node_zone_tags(client, core_api):  # NOQA

    k8s_zone_label = get_k8s_zone_label()
    lh_nodes = client.list_node()

    node_index = 0
    for node in lh_nodes:
        node_name = node.name

        if node_index % 2 == 0:
            zone = ZONE1
        else:
            zone = ZONE2

        payload = {
            "metadata": {
                "labels": {
                    k8s_zone_label: zone}
            }
        }

        core_api.patch_node(node_name, body=payload)
        node_index += 1

    yield

    lh_nodes = client.list_node()

    node_index = 0
    for node in lh_nodes:
        node_name = node.name

        payload = {
            "metadata": {
                "labels": {
                    k8s_zone_label: None}
            }
        }

        core_api.patch_node(node_name, body=payload)


def wait_longhorn_node_zone_updated(client): # NOQA

    lh_nodes = client.list_node()
    node_names = map(lambda node: node.name, lh_nodes)

    for node_name in node_names:
        for j in range(RETRY_COUNTS):
            lh_node = client.by_id_node(node_name)
            if lh_node.zone != '':
                break
            time.sleep(RETRY_INTERVAL)

        assert lh_node.zone != ''


def get_zone_replica_count(client, volume_name, zone_name): # NOQA
    volume = client.by_id_volume(volume_name)

    zone_replica_count = 0
    for replica in volume.replicas:
        replica_host_id = replica.hostId
        replica_host_zone = client.by_id_node(replica_host_id).zone
        if replica_host_zone == zone_name:
            zone_replica_count += 1
    return zone_replica_count


def test_zone_tags(client, core_api, volume_name, k8s_node_zone_tags):  # NOQA

    wait_longhorn_node_zone_updated(client)

    volume = create_and_check_volume(client, volume_name, num_of_replicas=2)

    host_id = get_self_host_id()

    volume.attach(hostId=host_id)

    volume = wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    zone1_replica_count = get_zone_replica_count(client, volume_name, ZONE1)
    zone2_replica_count = get_zone_replica_count(client, volume_name, ZONE2)

    assert zone1_replica_count == zone2_replica_count

    for i in range(randrange(3, 5)):
        volume = client.by_id_volume(volume_name)

        replica_count = len(volume.replicas)
        assert replica_count == 2

        replica_id = randrange(0, replica_count)

        replica_name = volume.replicas[replica_id].name

        volume.replicaRemove(name=replica_name)

        wait_for_volume_degraded(client, volume_name)

        wait_for_volume_healthy(client, volume_name)

        wait_for_volume_replica_count(client, volume_name, replica_count)

        volume = client.by_id_volume(volume_name)

        replica_names = map(lambda replica: replica.name, volume["replicas"])

        wait_new_replica_ready(client, volume_name, replica_names)

        zone1_replica_count = \
            get_zone_replica_count(client, volume_name, ZONE1)
        zone2_replica_count = \
            get_zone_replica_count(client, volume_name, ZONE2)

        assert zone1_replica_count == zone2_replica_count

    volume.updateReplicaCount(replicaCount=3)

    wait_for_volume_degraded(client, volume_name)

    wait_for_volume_replica_count(client, volume_name, 3)

    wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    lh_node_names = list(map(lambda node: node.name, client.list_node()))

    for replica in volume.replicas:
        lh_node_names.remove(replica.hostId)

    assert lh_node_names == []

    for i in range(randrange(3, 5)):
        volume = client.by_id_volume(volume_name)

        replica_count = len(volume.replicas)
        assert replica_count == 3

        replica_id = randrange(0, replica_count)

        replica_name = volume.replicas[replica_id].name

        volume.replicaRemove(name=replica_name)

        wait_for_volume_degraded(client, volume_name)

        wait_for_volume_healthy(client, volume_name)

        wait_for_volume_replica_count(client, volume_name, replica_count)

        volume = client.by_id_volume(volume_name)

        lh_node_names = list(map(lambda node: node.name, client.list_node()))

        for replica in volume.replicas:
            lh_node_names.remove(replica.hostId)

        assert lh_node_names == []

    # test soft antiaffinity feature
    volume.updateReplicaCount(replicaCount=4)

    wait_for_volume_degraded(client, volume_name)

    wait_for_volume_replica_count(client, volume_name, 4)

    wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    assert len(volume.replicas) == 4
