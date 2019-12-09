import pytest
import random
import string

from common import client, node_default_tags, volume_name # NOQA
from common import RETRY_COUNTS, RETRY_INTERVAL, SIZE
from common import check_volume_replicas, cleanup_volume, \
    generate_volume_name, get_self_host_id, get_update_disks, set_node_tags, \
    wait_for_volume_delete, wait_for_volume_detached, \
    wait_for_volume_healthy, wait_scheduling_failure
from time import sleep


def generate_tag_name():
    return "tag/" + "".join(random.choice(string.ascii_lowercase +
                                          string.digits) for _ in range(6))


def generate_unordered_tag_names():
    unsorted = []
    is_sorted = []
    while unsorted == is_sorted:
        unsorted = []
        for _ in range(3):
            unsorted.append(generate_tag_name())
        is_sorted = sorted(unsorted)
    return unsorted, is_sorted


def test_tag_basic(client):  # NOQA
    """
    Test that applying Tags to Nodes/Disks and retrieving them work as
    expected. Ensures that Tags are properly validated when updated.
    """
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    disks = get_update_disks(node.disks)
    assert len(node.disks) == 1
    assert disks[0].tags is None
    assert node.tags is None

    unsorted_disk, sorted_disk = generate_unordered_tag_names()
    unsorted_node, sorted_node = generate_unordered_tag_names()
    update_disks = get_update_disks(node.disks)
    update_disks[0].tags = unsorted_disk
    node = node.diskUpdate(disks=update_disks)
    disks = get_update_disks(node.disks)
    assert disks[0].tags == sorted_disk

    node = set_node_tags(client, node, unsorted_node)
    assert node.tags == sorted_node

    improper_tag_cases = [
        [""],   # Empty string
        [" "],  # Whitespace
        ["/"],  # Leading /
        [","],  # Illegal character
    ]
    for tags in improper_tag_cases:
        with pytest.raises(Exception) as e:
            set_node_tags(client, node, tags)
        assert "at least one error encountered while validating tags" in \
               str(e.value)
        with pytest.raises(Exception) as e:
            update_disks = get_update_disks(node.disks)
            update_disks[0].tags = tags
            node.diskUpdate(disks=update_disks)
        assert "at least one error encountered while validating tags" in \
               str(e.value)

    update_disks = get_update_disks(node.disks)
    update_disks[0].tags = []
    node = node.diskUpdate(disks=update_disks)
    disks = get_update_disks(node.disks)
    assert disks[0].tags is None

    node = set_node_tags(client, node)
    assert node.tags is None


def test_tag_scheduling(client, node_default_tags):  # NOQA
    """
    Test that scheduling succeeds if there are available Nodes/Disks with the
    requested Tags.
    """
    host_id = get_self_host_id()
    tag_specs = [
        # Select all Nodes.
        {
            "disk": [],
            "expected": 3,
            "node": []
        },
        # Selector works with AND on Disk Tags.
        {
            "disk": ["ssd", "nvme"],
            "expected": 2,
            "node": []
        },
        # Selector works with AND on Node Tags.
        {
            "disk": [],
            "expected": 2,
            "node": ["main", "storage"]
        },
        # Selector works based on combined Disk AND Node selector.
        {
            "disk": ["ssd", "nvme"],
            "expected": 1,
            "node": ["storage", "main"]
        }
    ]
    for specs in tag_specs:
        volume_name = generate_volume_name()  # NOQA
        client.create_volume(name=volume_name, size=SIZE, numberOfReplicas=3,
                             diskSelector=specs["disk"],
                             nodeSelector=specs["node"])
        volume = wait_for_volume_detached(client, volume_name)
        assert volume.diskSelector == specs["disk"]
        assert volume.nodeSelector == specs["node"]

        volume.attach(hostId=host_id)
        volume = wait_for_volume_healthy(client, volume_name)
        assert len(volume.replicas) == 3
        check_volume_replicas(volume, specs, node_default_tags)

        cleanup_volume(client, volume)


def test_tag_scheduling_failure(client, node_default_tags):  # NOQA
    """
    Test that scheduling fails if no Nodes/Disks with the requested Tags are
    available.
    """
    invalid_tag_cases = [
        # Only one Disk Tag exists.
        {
            "disk": ["doesnotexist", "ssd"],
            "node": []
        },
        # Only one Node Tag exists.
        {
            "disk": [],
            "node": ["doesnotexist", "main"]
        }
    ]
    for tags in invalid_tag_cases:
        volume_name = generate_volume_name()  # NOQA
        with pytest.raises(Exception) as e:
            client.create_volume(name=volume_name, size=SIZE,
                                 numberOfReplicas=3,
                                 diskSelector=tags["disk"],
                                 nodeSelector=tags["node"])
        assert "does not exist" in str(e.value)
    unsatisfied_tag_cases = [
        {
            "disk": [],
            "node": ["main", "fallback"]
        },
        {
            "disk": ["ssd", "m2"],
            "node": []
        }
    ]
    for tags in unsatisfied_tag_cases:
        volume_name = generate_volume_name()
        client.create_volume(name=volume_name, size=SIZE, numberOfReplicas=3,
                             diskSelector=tags["disk"],
                             nodeSelector=tags["node"])
        volume = wait_for_volume_detached(client, volume_name)
        assert volume.diskSelector == tags["disk"]
        assert volume.nodeSelector == tags["node"]
        wait_scheduling_failure(client, volume_name)

        client.delete(volume)
        wait_for_volume_delete(client, volume.name)
        volumes = client.list_volume()
        assert len(volumes) == 0


def test_tag_scheduling_on_update(client, node_default_tags, volume_name):  # NOQA
    """
    Test that Replicas get scheduled if a Node/Disk disks updated with the
    proper Tags.
    """
    tag_spec = {
        "disk": ["ssd", "m2"],
        "expected": 1,
        "node": ["main", "fallback"]
    }
    client.create_volume(name=volume_name, size=SIZE, numberOfReplicas=3,
                         diskSelector=tag_spec["disk"],
                         nodeSelector=tag_spec["node"])
    volume = wait_for_volume_detached(client, volume_name)
    assert volume.diskSelector == tag_spec["disk"]
    assert volume.nodeSelector == tag_spec["node"]

    wait_scheduling_failure(client, volume_name)

    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    update_disks = get_update_disks(node.disks)
    update_disks[0].tags = tag_spec["disk"]
    node = node.diskUpdate(disks=update_disks)
    set_node_tags(client, node, tag_spec["node"])
    scheduled = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        if v.conditions.scheduled.status == "True":
            scheduled = True
        if scheduled:
            break
        sleep(RETRY_INTERVAL)
    assert scheduled

    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    nodes = client.list_node()
    node_mapping = {node.id: {
        "disk": get_update_disks(node.disks)[0].tags,
        "node": node.tags
    } for node in nodes}
    assert len(volume.replicas) == 3
    check_volume_replicas(volume, tag_spec, node_mapping)

    cleanup_volume(client, volume)
