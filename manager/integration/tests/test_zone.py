import pytest
import time

from random import randrange

from common import client # NOQA
from common import core_api  # NOQA
from common import pvc, pod  # NOQA
from common import volume_name # NOQA

from common import cleanup_node_disks
from common import get_self_host_id

from common import get_update_disks
from common import update_node_disks

from common import create_and_wait_pod
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import delete_and_wait_pod

from common import create_and_check_volume
from common import wait_for_volume_condition_scheduled
from common import wait_for_volume_degraded
from common import wait_for_volume_detached
from common import wait_for_volume_delete
from common import wait_for_volume_healthy
from common import wait_for_volume_replica_count

from common import get_host_replica_count

from common import get_k8s_zone_label
from common import is_k8s_node_gke_cos
from common import set_and_wait_k8s_nodes_zone_label
from common import set_node_cordon
from common import set_node_tags
from common import wait_for_node_tag_update

from common import update_setting

from common import CONDITION_STATUS_TRUE
from common import RETRY_COUNTS
from common import RETRY_INTERVAL
from common import RETRY_INTERVAL_LONG
from common import SETTING_DEFAULT_DATA_LOCALITY
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY
from common import SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY
from common import SETTING_REPLICA_AUTO_BALANCE
from common import DATA_ENGINE

from test_scheduling import wait_new_replica_ready


ZONE1 = "lh-zone1"
ZONE2 = "lh-zone2"
ZONE3 = "lh-zone3"


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


def wait_longhorn_nodes_zone_not_empty(client): # NOQA

    lh_nodes = client.list_node()
    node_names = map(lambda node: node.name, lh_nodes)

    for node_name in node_names:
        for j in range(RETRY_COUNTS):
            lh_node = client.by_id_node(node_name)
            if lh_node.zone != '':
                break
            time.sleep(RETRY_INTERVAL)

        assert lh_node.zone != ''


def get_zone_replica_count(client, volume_name, zone_name, chk_running=False): # NOQA
    volume = client.by_id_volume(volume_name)

    zone_replica_count = 0
    for replica in volume.replicas:
        if chk_running and not replica.running:
            continue
        replica_host_id = replica.hostId
        replica_host_zone = client.by_id_node(replica_host_id).zone
        if replica_host_zone == zone_name:
            zone_replica_count += 1
    return zone_replica_count


@pytest.mark.v2_volume_test  # NOQA
def test_zone_tags(client, core_api, volume_name, k8s_node_zone_tags):  # NOQA
    """
    Test anti affinity zone feature

    1. Add Kubernetes zone labels to the nodes
        1. Only two zones now: zone1 and zone2
    2. Create a volume with two replicas
    3. Verify zone1 and zone2 either has one replica.
    4. Remove a random replica and wait for volume to finish rebuild
    5. Verify zone1 and zone2 either has one replica.
    6. Repeat step 4-5 a few times.
    7. Update volume to 3 replicas, make sure they're scheduled on 3 nodes
    8. Remove a random replica and wait for volume to finish rebuild
    9. Make sure replicas are on different nodes
    10. Repeat step 8-9 a few times
    """

    wait_longhorn_nodes_zone_not_empty(client)

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=2)

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


@pytest.mark.v2_volume_test  # NOQA
@pytest.mark.node  # NOQA
def test_replica_zone_anti_affinity(client, core_api, volume_name, k8s_node_zone_tags):  # NOQA
    """
    Test replica scheduler with zone anti-affinity

    1. Set zone anti-affinity to hard.
    2. Label nodes 1 & 2 with same zone label "zone1".
    Label node 3 with zone label "zone2".
    3. Create a volume with 3 replicas.
    4. Wait for volume condition `scheduled` to be false.
    5. Label node 2 with zone label "zone3".
    6. Wait for volume condition `scheduled` to be success.
    7. Clear the volume.
    8. Set zone anti-affinity to soft.
    9. Change the zone labels on node 1 & 2 & 3 to "zone1".
    10. Create a volume.
    11. Wait for volume condition `scheduled` to be success.
    12. Clean up the replica count, the zone labels and the volume.
    """

    wait_longhorn_nodes_zone_not_empty(client)

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="false")

    replica_zone_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY)
    client.update(replica_zone_soft_anti_affinity_setting, value="false")

    volume = create_and_check_volume(client, volume_name)

    lh_nodes = client.list_node()

    count = 0
    node_zone_map = {}
    for node in lh_nodes:
        count += 1
        node_zone_map[node.name] = "lh-zone" + str(count)

    set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    wait_for_volume_condition_scheduled(client, volume_name,
                                        "status",
                                        CONDITION_STATUS_TRUE)

    replica_zone_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY)
    client.update(replica_zone_soft_anti_affinity_setting, value="true")

    volume = client.by_id_volume(volume_name)
    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    node_zone_map = {}
    for node in lh_nodes:
        node_zone_map[node.name] = "lh-zone1"

    set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    volume = create_and_check_volume(client, volume_name)
    wait_for_volume_condition_scheduled(client, volume_name,
                                        "status",
                                        CONDITION_STATUS_TRUE)


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_zone_least_effort(client, core_api, volume_name):  # NOQA
    """
    Scenario: replica auto-balance zones with least-effort.

    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set volume spec `replicaAutoBalance` to `least-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-2.
        set node-3 to zone-3.
    And disable scheduling for node-2.
        disable scheduling for node-3.
    And create a volume with 6 replicas.
    And attach the volume to self-node.
    And 6 replicas running in zone-1.
        0 replicas running in zone-2.
        0 replicas running in zone-3.

    When enable scheduling for node-2.
    Then count replicas running on each node.
    And zone-1 replica count != zone-2 replica count.
        zone-2 replica count != 0.
        zone-3 replica count == 0.

    When enable scheduling for node-3.
    Then count replicas running on each node.
    And zone-1 replica count != zone-3 replica count.
        zone-2 replica count != 0.
        zone-3 replica count != 0.
    """
    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "least-effort")

    n1, n2, n3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE2,
            n3.name: ZONE3
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    client.update(n2, allowScheduling=False)
    client.update(n3, allowScheduling=False)

    n_replicas = 6
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=n_replicas)
    volume.attach(hostId=get_self_host_id())

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        if z1_r_count == 6 and z2_r_count == z3_r_count == 0:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert z1_r_count == 6
    assert z2_r_count == 0
    assert z3_r_count == 0

    client.update(n2, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        all_r_count = z1_r_count + z2_r_count + z3_r_count
        if z2_r_count != 0 and all_r_count == n_replicas:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert z1_r_count != z2_r_count
    assert z2_r_count != 0
    assert z3_r_count == 0

    client.update(n3, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        all_r_count = z1_r_count + z2_r_count + z3_r_count
        if z3_r_count != 0 and all_r_count == n_replicas:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert z1_r_count != z3_r_count
    assert z2_r_count != 0
    assert z3_r_count != 0


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_zone_best_effort(client, core_api, volume_name):  # NOQA
    """
    Scenario: replica auto-balance zones with best-effort.

    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set volume spec `replicaAutoBalance` to `best-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-2.
        set node-3 to zone-3.
    And disable scheduling for node-2.
        disable scheduling for node-3.
    And create a volume with 6 replicas.
    And attach the volume to self-node.
    And 6 replicas running in zone-1.
        0 replicas running in zone-2.
        0 replicas running in zone-3.

    When enable scheduling for node-2.
    Then count replicas running on each node.
    And 3 replicas running in zone-1.
        3 replicas running in zone-2.
        0 replicas running in zone-3.

    When enable scheduling for node-3.
    Then count replicas running on each node.
    And 2 replicas running in zone-1.
        2 replicas running in zone-2.
        2 replicas running in zone-3.
    """

    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "best-effort")

    n1, n2, n3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE2,
            n3.name: ZONE3
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    client.update(n2, allowScheduling=False)
    client.update(n3, allowScheduling=False)

    n_replicas = 6
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=n_replicas)
    volume.attach(hostId=get_self_host_id())

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        if z1_r_count == 6 and z2_r_count == z3_r_count == 0:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert z1_r_count == 6
    assert z2_r_count == 0
    assert z3_r_count == 0

    client.update(n2, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        if z1_r_count == z2_r_count == 3 and z3_r_count == 0:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL_LONG)
    assert z1_r_count == 3
    assert z2_r_count == 3
    assert z3_r_count == 0

    client.update(n3, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        if z1_r_count == z2_r_count == z3_r_count == 2:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL_LONG)
    assert z1_r_count == 2
    assert z2_r_count == 2
    assert z3_r_count == 2


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_when_disabled_disk_scheduling_in_zone(client, core_api, volume_name):  # NOQA
    """
    Scenario: replica auto-balance when disk scheduling is disabled on nodes
              in a zone.

    Issue: https://github.com/longhorn/longhorn/issues/6508

    Given `replica-soft-anti-affinity` setting is `true`.
    And node-1 is in zone-1.
        node-2 is in zone-2.
        node-3 is in zone-3.
    And disk scheduling is disabled on node-3.
    And create a volume with 3 replicas.
    And attach the volume to test pod node.
    And 3 replicas running in zone-1 and zone-2.
        0 replicas running in zone-3.

    When set `replica-auto-balance` to `best-effort`.

    Then 3 replicas running in zone-1 and zone-2.
         0 replicas running in zone-3.
    And replica count remains stable across zones and nodes.
    """
    # Set `replica-soft-anti-affinity` to `true`.
    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")

    # Assign nodes to respective zones
    node1, node2, node3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            node1.name: ZONE1,
            node2.name: ZONE2,
            node3.name: ZONE3
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    # Disable disk scheduling on node 3
    cleanup_node_disks(client, node3.name)

    # Create a volume with 3 replicas
    num_of_replicas = 3
    volume = client.create_volume(name=volume_name,
                                  numberOfReplicas=num_of_replicas,
                                  dataEngine=DATA_ENGINE)

    # Wait for the volume to detach and attach it to the test pod node
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())

    # Define a function to assert replica count
    def assert_replica_count(is_stable=False):
        assert_tolerated = 0
        for _ in range(RETRY_COUNTS):
            if is_k8s_node_gke_cos(core_api):
                _set_and_wait_k8s_node_zone_label()

            time.sleep(RETRY_INTERVAL)

            zone3_replica_count = get_zone_replica_count(
                client, volume_name, ZONE3, chk_running=True)
            assert zone3_replica_count == 0

            total_replica_count = \
                get_zone_replica_count(
                    client, volume_name, ZONE1, chk_running=True) + \
                get_zone_replica_count(
                    client, volume_name, ZONE2, chk_running=True)

            if is_stable:
                try:
                    assert total_replica_count == num_of_replicas
                except AssertionError as e:
                    # The GKE zone label undergoes periodic updates to reflect
                    # the current zone. Consequently, we cannot guarantee the
                    # exact zone of the replica node. Therefore, we'll allow
                    # for one assertion error to accommodate GKE's update
                    # process.
                    if is_k8s_node_gke_cos(core_api) and assert_tolerated < 1:
                        assert_tolerated += 1
                    else:
                        raise AssertionError(e)
            elif total_replica_count == num_of_replicas:
                break

        assert total_replica_count == 3

    # Perform the initial assertion to ensure the replica count is as expected
    assert_replica_count()

    # Update the replica-auto-balance setting to `best-effort`
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "best-effort")

    # Perform the final assertion to ensure the replica count is as expected,
    # and stable after the setting update
    assert_replica_count(is_stable=True)


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_when_no_storage_available_in_zone(client, core_api, volume_name):  # NOQA
    """
    Scenario: replica auto-balance when there is no storage available on nodes
              in a zone.

    Issue: https://github.com/longhorn/longhorn/issues/6671

    Given `replica-soft-anti-affinity` setting is `true`.
    And node-1 is in zone-1.
        node-2 is in zone-2.
        node-3 is in zone-3.
    And fill up the storage on node-3.
    And create a volume with 3 replicas.
    And attach the volume to test pod node.
    And 3 replicas running in zone-1 and zone-2.
        0 replicas running in zone-3.

    When set `replica-auto-balance` to `best-effort`.

    Then 3 replicas running in zone-1 and zone-2.
         0 replicas running in zone-3.
    And replica count remains stable across zones and nodes.
    """
    # Set `replica-soft-anti-affinity` to `true`.
    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")

    # Assign nodes to respective zones
    node1, node2, node3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            node1.name: ZONE1,
            node2.name: ZONE2,
            node3.name: ZONE3
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    # Fill up the storage on node 3
    for _, disk in node3.disks.items():
        disk.storageReserved = disk.storageMaximum

    update_disks = get_update_disks(node3.disks)
    update_node_disks(client, node3.name, disks=update_disks, retry=True)

    # Create a volume with 3 replicas
    num_of_replicas = 3
    volume = client.create_volume(name=volume_name,
                                  numberOfReplicas=num_of_replicas,
                                  dataEngine=DATA_ENGINE)

    # Wait for the volume to detach and attach it to the test pod node
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())

    # Define a function to assert replica count
    def assert_replica_count(is_stable=False):
        assert_tolerated = 0
        for _ in range(RETRY_COUNTS):
            if is_k8s_node_gke_cos(core_api):
                _set_and_wait_k8s_node_zone_label()

            time.sleep(RETRY_INTERVAL)

            zone3_replica_count = get_zone_replica_count(
                client, volume_name, ZONE3, chk_running=True)
            assert zone3_replica_count == 0

            total_replica_count = \
                get_zone_replica_count(
                    client, volume_name, ZONE1, chk_running=True) + \
                get_zone_replica_count(
                    client, volume_name, ZONE2, chk_running=True)

            if is_stable:
                try:
                    assert total_replica_count == num_of_replicas
                except AssertionError as e:
                    # The GKE zone label undergoes periodic updates to reflect
                    # the current zone. Consequently, we cannot guarantee the
                    # exact zone of the replica node. Therefore, we'll allow
                    # for one assertion error to accommodate GKE's update
                    # process.
                    if is_k8s_node_gke_cos(core_api) and assert_tolerated < 1:
                        assert_tolerated += 1
                    else:
                        raise AssertionError(e)
            elif total_replica_count == num_of_replicas:
                break

        assert total_replica_count == 3

    # Perform the initial assertion to ensure the replica count is as expected
    assert_replica_count()

    # Update the replica-auto-balance setting to `best-effort`
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "best-effort")

    # Perform the final assertion to ensure the replica count is as expected,
    # and stable after the setting update
    assert_replica_count(is_stable=True)


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_when_replica_on_unschedulable_node(client, core_api, volume_name, request):  # NOQA
    """
    Scenario: replica auto-balance when replica already running on
              an unschedulable node.

    Issue: https://github.com/longhorn/longhorn/issues/4502

    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set volume spec `replicaAutoBalance` to `least-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-2.
        set node-3 to zone-3.
    And node-2 tagged `AVAIL`.
        node-3 tagged `AVAIL`.
    And create a volume with 2 replicas and nodeSelector `AVAIL`.
    And attach the volume to self-node.
    And 0 replicas running in zone-1.
        1 replicas running in zone-2.
        1 replicas running in zone-3.

    When cordone node-2.
    Then replicas should remain balanced with,
         0 replicas running in zone-1.
         1 replicas running in zone-2.
         1 replicas running in zone-3.
    """
    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "least-effort")

    n1, n2, n3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE2,
            n3.name: ZONE3
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    client.update(n2, allowScheduling=True, tags=["AVAIL"])
    client.update(n3, allowScheduling=True, tags=["AVAIL"])

    n_replicas = 2
    volume = client.create_volume(name=volume_name,
                                  numberOfReplicas=n_replicas,
                                  nodeSelector=["AVAIL"],
                                  dataLocality="best-effort",
                                  dataEngine=DATA_ENGINE)

    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=get_self_host_id())

    for _ in range(RETRY_COUNTS):
        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)

        if z1_r_count == 0 and (z2_r_count and z3_r_count == 1):
            break
        time.sleep(RETRY_INTERVAL)

    assert z1_r_count == 0 and (z2_r_count and z3_r_count == 1)

    # Set cordon on node
    def finalizer():
        set_node_cordon(core_api, n2.name, False)
    request.addfinalizer(finalizer)

    set_node_cordon(core_api, n2.name, True)

    assert_tolerated = 0
    for _ in range(RETRY_COUNTS):
        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        z3_r_count = get_zone_replica_count(
            client, volume_name, ZONE3, chk_running=True)
        try:
            assert z1_r_count == 0 and (z2_r_count and z3_r_count == 1)
        except AssertionError as e:
            # The GKE zone label undergoes periodic updates to reflect
            # the current zone. Consequently, we cannot guarantee the
            # exact zone of the replica node. Therefore, we'll allow
            # for one assertion error to accommodate GKE's update process.
            if is_k8s_node_gke_cos(core_api) and assert_tolerated < 1:
                assert_tolerated += 1
            else:
                raise AssertionError(e)

        volume = client.by_id_volume(volume_name)
        for status in volume.rebuildStatus:
            assert not status.isRebuilding

        time.sleep(RETRY_INTERVAL)


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_zone_best_effort_with_data_locality(client, core_api, volume_name, pod):  # NOQA
    """
    Background:
    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set `default-data-locality` to `best-effort`.
    And set `replicaAutoBalance` to `best-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-1.
        set node-3 to zone-2.
    And create volume with 2 replicas.
    And create pv for volume.
    And create pvc for volume.

    Scenario Outline: replica auto-balance zones with best-effort should
                      not remove pod local replicas when data locality is
                      enabled (best-effort).

    Given create and wait pod on <pod-node>.
    And disable scheduling and evict node-3.
    And count replicas on each nodes.
    And 1 replica running on <pod-node>.
        1 replica running on <duplicate-node>.
        0 replica running on node-3.

    When enable scheduling for node-3.
    Then count replicas on each nodes.
    And 1 replica running on <pod-node>.
        0 replica running on <duplicate-node>.
        1 replica running on node-3.
    And count replicas in each zones.
    And 1 replica running in zone-1.
        1 replica running in zone-2.
    And loop 3 times with each wait 5 seconds and count replicas on each nodes.
        To ensure no addition scheduling is happening.
        1 replica running on <pod-node>.
        0 replica running on <duplicate-node>.
        1 replica running on node-3.

    And delete pod.

    Examples:
        | pod-node | duplicate-node |
        | node-1   | node-2         |
        | node-2   | node-1         |
        | node-1   | node-2         |
    """

    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_DEFAULT_DATA_LOCALITY, "best-effort")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "best-effort")

    n1, n2, n3 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE1,
            n3.name: ZONE2
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    n_replicas = 2
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=n_replicas)
    create_pv_for_volume(client, core_api, volume, volume_name)
    create_pvc_for_volume(client, core_api, volume, volume_name)
    pod['spec']['volumes'] = [{
        "name": "pod-data",
        "persistentVolumeClaim": {
            "claimName": volume_name
        }
    }]

    for i in range(1, 4):
        pod_node_name = n2.name if i % 2 == 0 else n1.name
        pod['spec']['nodeSelector'] = {
            "kubernetes.io/hostname": pod_node_name
        }
        create_and_wait_pod(core_api, pod)

        client.update(n3, allowScheduling=False, evictionRequested=True)

        duplicate_node = [n1.name, n2.name]
        duplicate_node.remove(pod_node_name)
        for _ in range(RETRY_COUNTS):
            if is_k8s_node_gke_cos(core_api):
                _set_and_wait_k8s_node_zone_label()

            pod_node_r_count = get_host_replica_count(
                client, volume_name, pod_node_name, chk_running=True)
            duplicate_node_r_count = get_host_replica_count(
                client, volume_name, duplicate_node[0], chk_running=True)
            balance_node_r_count = get_host_replica_count(
                client, volume_name, n3.name, chk_running=False)

            if pod_node_r_count == duplicate_node_r_count == 1 and \
                    balance_node_r_count == 0:
                break

            time.sleep(RETRY_INTERVAL)
        assert pod_node_r_count == 1
        assert duplicate_node_r_count == 1
        assert balance_node_r_count == 0

        client.update(n3, allowScheduling=True)

        for _ in range(RETRY_COUNTS):
            if is_k8s_node_gke_cos(core_api):
                _set_and_wait_k8s_node_zone_label()

            pod_node_r_count = get_host_replica_count(
                client, volume_name, pod_node_name, chk_running=True)
            duplicate_node_r_count = get_host_replica_count(
                client, volume_name, duplicate_node[0], chk_running=False)
            balance_node_r_count = get_host_replica_count(
                client, volume_name, n3.name, chk_running=True)

            if pod_node_r_count == balance_node_r_count == 1 and \
                    duplicate_node_r_count == 0:
                break

            time.sleep(RETRY_INTERVAL)
        assert pod_node_r_count == 1
        assert duplicate_node_r_count == 0
        assert balance_node_r_count == 1

        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)
        assert z1_r_count == z2_r_count == 1

        # loop 3 times and each to wait 5 seconds to ensure there is no
        # re-scheduling happening.
        for _ in range(3):
            if is_k8s_node_gke_cos(core_api):
                _set_and_wait_k8s_node_zone_label()

            time.sleep(5)
            assert pod_node_r_count == get_host_replica_count(
                client, volume_name, pod_node_name, chk_running=True)
            assert duplicate_node_r_count == get_host_replica_count(
                client, volume_name, duplicate_node[0], chk_running=False)
            assert balance_node_r_count == get_host_replica_count(
                client, volume_name, n3.name, chk_running=True)

        delete_and_wait_pod(core_api, pod['metadata']['name'])


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_node_duplicates_in_multiple_zones(client, core_api, volume_name):  # NOQA
    """
    Scenario: replica auto-balance to nodes with duplicated replicas in the
              zone.

    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set volume spec `replicaAutoBalance` to `least-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-2.
    And disable scheduling for node-3.
    And create a volume with 3 replicas.
    And attach the volume to self-node.
    And zone-1 and zone-2 should contain 3 replica in total.

    When set node-3 to the zone with duplicated replicas.
    And enable scheduling for node-3.
    Then count replicas running on each node.
    And 1 replica running on node-1
        1 replica running on node-2
        1 replica running on node-3.
    And count replicas running in each zone.
    And total of 3 replicas running in zone-1 and zone-2.
    """

    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "least-effort")

    n1, n2, n3 = client.list_node()

    node_zone_map = {
        n1.name: ZONE1,
        n2.name: ZONE2,
        n3.name: "temp"
    }
    set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    client.update(n3, allowScheduling=False)

    n_replicas = 3
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=n_replicas)
    volume.attach(hostId=get_self_host_id())
    z1_r_count = get_zone_replica_count(client, volume_name, ZONE1)
    z2_r_count = get_zone_replica_count(client, volume_name, ZONE2)
    assert z1_r_count + z2_r_count == n_replicas

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {}
        if z1_r_count == 2:
            node_zone_map = {
                n1.name: ZONE1,
                n2.name: ZONE2,
                n3.name: ZONE1
            }
        else:
            node_zone_map = {
                n1.name: ZONE1,
                n2.name: ZONE2,
                n3.name: ZONE2
            }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    client.update(n3, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        n1_r_count = get_host_replica_count(
            client, volume_name, n1.name, chk_running=True)
        n2_r_count = get_host_replica_count(
            client, volume_name, n2.name, chk_running=True)
        n3_r_count = get_host_replica_count(
            client, volume_name, n3.name, chk_running=True)

        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)

        if n1_r_count == n2_r_count == n3_r_count == 1 and \
                z1_r_count + z2_r_count == n_replicas:
            break
        time.sleep(RETRY_INTERVAL)

    assert n1_r_count == 1
    assert n2_r_count == 1
    assert n3_r_count == 1

    assert z1_r_count + z2_r_count == n_replicas


@pytest.mark.skip(reason="REQUIRE_5_NODES")
def test_replica_auto_balance_zone_best_effort_with_uneven_node_in_zones(client, core_api, volume_name, pod):  # NOQA
    """
    Given set `replica-soft-anti-affinity` to `true`.
    And set `replica-zone-soft-anti-affinity` to `true`.
    And set `replicaAutoBalance` to `best-effort`.
    And set node-1 to zone-1.
        set node-2 to zone-1.
        set node-3 to zone-1.
        set node-4 to zone-2.
        set node-5 to zone-2.
    And disable scheduling for node-2.
        disable scheduling for node-3.
        disable scheduling for node-4.
        disable scheduling for node-5.
    And create volume with 4 replicas.
    And attach the volume to node-1.

    Scenario: replica auto-balance zones with best-effort should balance
              replicas in zone.

    Given 4 replica running on node-1.
          0 replica running on node-2.
          0 replica running on node-3.
          0 replica running on node-4.
          0 replica running on node-5.

    When enable scheduling for node-4.
    Then count replicas on each zones.
    And 2 replica running on zode-1.
        2 replica running on zode-2.

    When enable scheduling for node-2.
         enable scheduling for node-3.
    Then count replicas on each nodes.
    And 1 replica running on node-1.
        1 replica running on node-2.
        1 replica running on node-3.
        1 replica running on node-4.
        0 replica running on node-5.

    When enable scheduling for node-5.
    Then count replicas on each zones.
    And 2 replica running on zode-1.
        2 replica running on zode-2.
    """

    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_DEFAULT_DATA_LOCALITY, "best-effort")
    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "best-effort")

    n1, n2, n3, n4, n5 = client.list_node()

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE1,
            n3.name: ZONE1,
            n4.name: ZONE2,
            n5.name: ZONE2
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    client.update(n2, allowScheduling=False)
    client.update(n3, allowScheduling=False)
    client.update(n4, allowScheduling=False)
    client.update(n5, allowScheduling=False)

    n_replicas = 4
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=n_replicas)
    volume.attach(hostId=n1.name)

    for _ in range(RETRY_COUNTS):
        n1_r_count = get_host_replica_count(
            client, volume_name, n1.name, chk_running=True)
        n2_r_count = get_host_replica_count(
            client, volume_name, n2.name, chk_running=False)
        n3_r_count = get_host_replica_count(
            client, volume_name, n3.name, chk_running=False)
        n4_r_count = get_host_replica_count(
            client, volume_name, n4.name, chk_running=False)
        n5_r_count = get_host_replica_count(
            client, volume_name, n5.name, chk_running=False)

        if n1_r_count == 4 and \
                n2_r_count == n3_r_count == n4_r_count == n5_r_count == 0:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert n1_r_count == 4
    assert n2_r_count == 0
    assert n3_r_count == 0
    assert n4_r_count == 0
    assert n5_r_count == 0

    client.update(n4, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)

        if z1_r_count == z2_r_count == 2:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)

    assert z1_r_count == 2
    assert z2_r_count == 2

    client.update(n2, allowScheduling=True)
    client.update(n3, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        n1_r_count = get_host_replica_count(
            client, volume_name, n1.name, chk_running=True)
        n2_r_count = get_host_replica_count(
            client, volume_name, n2.name, chk_running=True)
        n3_r_count = get_host_replica_count(
            client, volume_name, n3.name, chk_running=True)
        n4_r_count = get_host_replica_count(
            client, volume_name, n4.name, chk_running=True)
        n5_r_count = get_host_replica_count(
            client, volume_name, n5.name, chk_running=False)

        if n1_r_count == n2_r_count == n3_r_count == n4_r_count == 1 and \
                n5_r_count == 0:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)
    assert n1_r_count == 1
    assert n2_r_count == 1
    assert n3_r_count == 1
    assert n4_r_count == 1
    assert n5_r_count == 0

    client.update(n5, allowScheduling=True)

    for _ in range(RETRY_COUNTS):
        z1_r_count = get_zone_replica_count(
            client, volume_name, ZONE1, chk_running=True)
        z2_r_count = get_zone_replica_count(
            client, volume_name, ZONE2, chk_running=True)

        if z1_r_count == z2_r_count == 2:
            break

        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(RETRY_INTERVAL)

    assert z1_r_count == 2
    assert z2_r_count == 2


@pytest.mark.v2_volume_test  # NOQA
def test_replica_auto_balance_should_respect_node_selector(client, core_api, volume_name, pod):  # NOQA
    """
    Background:

    Given Setting (replica-soft-anti-affinity) is (true).
    And Setting (replica-zone-soft-anti-affinity) is (true).
    And Node (node-1, node-2) has tag (tag-0).
    And Node (node-1) is in zone (lh-zone-1).
        Node (node-2) is in zone (lh-zone-2).
        Node (node-3) is in zone (should-not-schedule).

    Scenario Outline: replica auto-balance should respect node-selector.

    Issue: https://github.com/longhorn/longhorn/issues/5971

    Given Volume created.
    And Volume replica number is (3).
    And Volume has node selector (tag-0).
    And Volume attached (node-1).
    And Replica is in zone (lh-zone-1, lh-zone-2).

    When Setting (replica-auto-balance) is (least-effort).

    Then Replica is in zone (lh-zone-1, lh-zone-2) (loop 10 sec).
    """
    update_setting(client, SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY, "true")
    update_setting(client, SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY, "true")

    n1, n2, n3 = client.list_node()

    selected_nodes = [n1, n2]

    node_tag = "tag0"
    for node in selected_nodes:
        set_node_tags(client, node, tags=[node_tag])
        wait_for_node_tag_update(client, node.name, [node_tag])

    # The GKE zone label is periodically updated with the actual zone.
    # Invoke _set_k8s_node_zone_label to refresh the zone label with each
    # retry iteration to maintain the expected zone label.
    def _set_and_wait_k8s_node_zone_label():
        node_zone_map = {
            n1.name: ZONE1,
            n2.name: ZONE2,
            n3.name: "should-not-schedule"
        }
        set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map)

    _set_and_wait_k8s_node_zone_label()

    n_replicas = 3
    client.create_volume(name=volume_name,
                         numberOfReplicas=n_replicas,
                         nodeSelector=[node_tag],
                         dataEngine=DATA_ENGINE)
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=selected_nodes[0].name)

    z1_r_count = get_zone_replica_count(client, volume_name, ZONE1)
    z2_r_count = get_zone_replica_count(client, volume_name, ZONE2)
    assert z1_r_count + z2_r_count == n_replicas

    update_setting(client, SETTING_REPLICA_AUTO_BALANCE, "least-effort")

    # Check over 10 seconds to check for unexpected re-scheduling.
    for _ in range(10):
        if is_k8s_node_gke_cos(core_api):
            _set_and_wait_k8s_node_zone_label()

        time.sleep(1)

        check_z1_r_count = get_zone_replica_count(client, volume_name, ZONE1)
        check_z2_r_count = get_zone_replica_count(client, volume_name, ZONE2)

        assert check_z1_r_count == z1_r_count
        assert check_z2_r_count == z2_r_count
