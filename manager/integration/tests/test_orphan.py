import pytest
import os
import time
import random
import string

from common import core_api, client # NOQA
from common import Gi, SIZE
from common import volume_name # NOQA
from common import SETTING_ORPHAN_AUTO_DELETION
from common import RETRY_COUNTS, RETRY_INTERVAL_LONG
from common import exec_nsenter
from common import get_self_host_id
from common import get_update_disks, wait_for_disk_update, cleanup_node_disks
from common import create_and_check_volume, wait_for_volume_healthy
from common import cleanup_volume_by_name
from common import create_host_disk, cleanup_host_disks
from common import wait_for_node_update
from common import wait_for_disk_status


def generate_random_id(num_bytes):
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(num_bytes))


def crate_disks_on_host(client, disk_names, request):  # NOQA
    disk_paths = []

    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    update_disks = get_update_disks(node.disks)

    for name in disk_names:
        disk_path = create_host_disk(client,
                                     name,
                                     str(Gi),
                                     lht_hostId)
        disk = {"path": disk_path, "allowScheduling": True}
        update_disks[name] = disk
        disk_paths.append(disk_path)

    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_update(client, node.name, len(update_disks))

    def finalizer():
        delete_extra_disks_on_host(client, disk_names)
        for disk_name in disk_names:
            cleanup_host_disks(client, disk_name)

    request.addfinalizer(finalizer)

    return disk_paths


def create_volume_with_replica_on_each_node(client, volume_name):  # NOQA
    lht_hostId = get_self_host_id()

    nodes = client.list_node()

    volume = create_and_check_volume(client, volume_name, len(nodes), SIZE)
    volume.attach(hostId=lht_hostId, disableFrontend=False)
    wait_for_volume_healthy(client, volume_name)

    return volume


def create_orphaned_directories_on_host(volume, disk_paths, num_orphans):  # NOQA
    lht_hostId = get_self_host_id()
    paths = []
    for replica in volume.replicas:
        if replica.hostId != lht_hostId:
            continue
        for _ in range(num_orphans):
            for i, disk_path in enumerate(disk_paths):
                replica_dir_name = volume.name + "-" + generate_random_id(8)
                path = os.path.join(disk_path, "replicas", replica_dir_name)
                paths.append(path)
                exec_nsenter("cp -a {} {}".format(replica.dataPath, path))

    return paths


def wait_for_orphan_delete(client, name):  # NOQA
    for _ in range(RETRY_COUNTS):
        orphans = client.list_orphan()
        found = False
        for orphan in orphans:
            if orphan.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL_LONG)
    assert not found


def delete_orphan(client, orphan_name):  # NOQA
    orphan = client.by_id_orphan(orphan_name)
    client.delete(orphan)
    wait_for_orphan_delete(client, orphan_name)


def delete_orphans(client):  # NOQA
    orphans = client.list_orphan()
    for orphan in orphans:
        delete_orphan(client, orphan.name)


def wait_for_orphan_count(client, number, retry_counts=120):  # NOQA
    for _ in range(retry_counts):
        orphans = client.list_orphan()
        if len(orphans) == number:
            break
        time.sleep(RETRY_INTERVAL_LONG)
    return len(orphans)


def wait_for_file_count(path, number, retry_counts=120):
    for _ in range(retry_counts):
        count = exec_nsenter("ls {} | wc -l".format(path))
        if int(count) == number:
            break
        time.sleep(RETRY_INTERVAL_LONG)

    count = exec_nsenter("ls {} | wc -l".format(path))
    return int(count)


def delete_orphaned_directory_on_host(directories):  # NOQA
    for path in directories:
        exec_nsenter("rm -rf {}".format(path))


def delete_extra_disks_on_host(client, disk_names):  # NOQA
    lht_hostId = get_self_host_id()

    node = client.by_id_node(lht_hostId)
    update_disk = get_update_disks(node.disks)

    for disk_name in disk_names:
        update_disk[disk_name].allowScheduling = False
        update_disk[disk_name].evictionRequested = True

    node = node.diskUpdate(disks=update_disk)

    for disk_name in disk_names:
        wait_for_disk_status(client, lht_hostId,
                             disk_name,
                             "storageScheduled", 0)


@pytest.mark.orphan
def test_orphaned_dirs_with_wrong_naming_format(client, volume_name, request):  # NOQA
    """
    Test orphan CRs are not created for the orphaned directories with wrong
    naming formats
    1. Create a new disk holding valid and invalid orphaned replica
       directories
    2. Create a volume and then attach to the current node
    3. Create one valid orphaned replica directories by copying the active
       replica directory
    4. Create multiple invalid orphan replica directories with wrong naming
       format
    5. Clean up volume
    6. Verify orphan list only contains the orphan CR for valid orphaned
       replica directory
    7. Clean up disk
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    create_orphaned_directories_on_host(volume, disk_paths, 1)

    # Step 4
    for replica in volume.replicas:
        if replica.hostId != lht_hostId:
            continue

        # Create invalid orphaned directories.
        # 8-byte random id missing
        exec_nsenter("mkdir -p {}".format(os.path.join(replica.diskPath,
                                                       "replicas",
                                                       volume_name)))
        # wrong random id length
        exec_nsenter("mkdir -p {}".format(
            os.path.join(replica.diskPath,
                         "replicas",
                         volume_name + "-" + generate_random_id(4))))
        # volume.meta missing
        path = os.path.join(replica.diskPath,
                            "replicas",
                            volume_name + "-" + generate_random_id(8))
        exec_nsenter("cp -a {} {}; rm -f {}".format(
            replica.dataPath, path, os.path.join(path, "volume.meta")))
        # corrupted volume.meta
        path = os.path.join(replica.diskPath,
                            "replicas",
                            volume_name + "-" + generate_random_id(8))
        exec_nsenter("cp -a {} {}; echo xxx > {}".format(
            replica.dataPath, path, os.path.join(path, "volume.meta")))

    # Step 5
    cleanup_volume_by_name(client, volume_name)

    # Step 6
    assert wait_for_orphan_count(client, 1, 180) == 1


@pytest.mark.orphan
def test_delete_orphans(client, volume_name, request):  # NOQA
    """
    Test the deletion of orphaned replica directories
    1. Create a new disk holding valid and invalid orphaned replica
       directories
    2. Create a volume and attach to the current node
    3. Create multiple orphaned replica directories by copying the
       active replica directory
    4. Clean up volume
    5. Verify orphan list contains CRs for the valid orphaned replica
       directories
    6. Delete all orphan CRs
    7. Verify orphan list is empty and the orphan replica directories are
       deleted
    8. Verify all orphaned replica directories are deleted
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    num_orphans = 5
    create_orphaned_directories_on_host(volume, disk_paths, num_orphans)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, num_orphans, 180) == num_orphans

    # Step 6
    delete_orphans(client)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0

    # Step 8
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               0,
                               180) == 0


@pytest.mark.orphan
def test_orphaned_replica_dir_missing(client, volume_name, request):  # NOQA
    """
    Test orphan CRs are deleted in background if the orphaned replica
    directories are missing
    1. Create a new disk for holding valid and invalid orphaned replica
       directories
    2. Create a volume and attach to the current node
    3. Create a orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CRs for the orphaned replica
       directories
    6. Delete the on-disk orphaned replica directories
    7. Verify the orphan CR is deleted in background
    8. Clean up disk
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    orphaned_directories = create_orphaned_directories_on_host(volume,
                                                               disk_paths,
                                                               1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6
    delete_orphaned_directory_on_host(orphaned_directories)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0


@pytest.mark.orphan
def test_delete_orphan_after_orphaned_dir_is_deleted(client, volume_name, request):  # NOQA
    """
    Test the immediate deletion of orphan CRs after the orphaned replica
    directory is deleted
    1. Create a new disk for holding valid and invalid orphaned replica
       directories
    2. Create a volume and attach to the current node
    3. Create a valid orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CR for the orphaned replica
       directories
    6. Delete the on-disk orphaned replica directories
    7. Delete the orphan CRs immediately
    8. Verify orphan list is empty
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    orphaned_directories = create_orphaned_directories_on_host(volume,
                                                               disk_paths,
                                                               1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6
    delete_orphaned_directory_on_host(orphaned_directories)

    # Step 7
    delete_orphans(client)

    # Step 8
    assert wait_for_orphan_count(client, 0, 180) == 0


@pytest.mark.orphan
def test_disk_evicted(client, volume_name, request):  # NOQA
    """
    Test the orphan CR is deleted in background but on-disk data still exists
    if the disk is evicted
    1. Create a new disk for holding valid and invalid orphaned
       replica directories
    2. Create a volume and attach to the current node
    3. Create a valid orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the valid orphaned replica directory
    6. Evict the disk containing the orphaned replica directory
    7. Verify the orphan CR is deleted in background, but the on-disk orphaned
       replica directory still exists
    8. Set the disk scheduleable again
    9. Verify the orphan CR is created again and the on-disk orphaned replica
       directory still exists
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    lht_hostId = get_self_host_id()

    # Step 1
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    create_orphaned_directories_on_host(volume, disk_paths, 1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6: Request disk eviction evictionRequested
    node = client.by_id_node(lht_hostId)
    update_disks = get_update_disks(node.disks)

    update_disks[disk_names[0]].allowScheduling = False
    update_disks[disk_names[0]].evictionRequested = True
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_update(client, node.name, len(update_disks))

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0

    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               1,
                               180) == 1

    # Step 8: Set disk allowScheduling to true and evictionRequested to false
    node = client.by_id_node(lht_hostId)
    update_disks = get_update_disks(node.disks)

    update_disks[disk_names[0]].allowScheduling = True
    update_disks[disk_names[0]].evictionRequested = False
    node = node.diskUpdate(disks=update_disks)
    node = wait_for_disk_update(client, node.name, len(update_disks))

    # Step 9
    assert wait_for_orphan_count(client, 1, 180) == 1

    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               1,
                               180) == 1


@pytest.mark.orphan
def test_node_evicted(client, volume_name, request):  # NOQA
    """
    Test the orphan CR is deleted in background but on-disk data still exists
    if the node is evicted
    1. Create a new-disk for holding valid and invalid orphaned replica
       directories
    2. Create a volume and attach to the current node
    3. Create a valid orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the valid orphaned replica directory
    6. Evict the node containing the orphaned replica directory
    7. Verify the orphan CR is deleted in background, but the on-disk
       orphaned replica directory still exists
    8. Disable node eviction
    9. Verify the orphan CR is created again and the on-disk orphaned replica
       directory still exists
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    create_orphaned_directories_on_host(volume, disk_paths, 1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6: request node eviction
    node = client.by_id_node(lht_hostId)
    client.update(node, allowScheduling=False, evictionRequested=True)
    node = wait_for_node_update(client, lht_hostId,
                                "allowScheduling", False)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               1,
                               180) == 1

    # Step 8: Disable node eviction
    node = client.by_id_node(lht_hostId)
    client.update(node, allowScheduling=True, evictionRequested=False)
    node = wait_for_node_update(client, lht_hostId,
                                "allowScheduling", True)

    # Step 9
    assert wait_for_orphan_count(client, 1, 180) == 1
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               1,
                               180) == 1


@pytest.mark.orphan
def test_orphaned_dirs_in_duplicated_disks(client, volume_name, request):  # NOQA
    """
    Test orphaned dirs in duplicated disks. LH should not create a orphan CR
    for the orphaned dir in the deduplicate and unscheduled disk.
    1. Create a new disk for holding orphaned replica directories
    2. Create a folder under the new disk. This folder will be the duplicated
       disk. Add it to the node.
    3. Create a volume and attach to the current node
    4. Create multiple orphaned replica directories in the two disks by
       copying the active replica directory
    5. Clean up volume
    6. Verify orphan list only contains the orphan CRs for replica directories
       in the ready disk
    7. Delete all orphan CRs
    8. Verify orphan list is empty
    9. Verify orphaned directories in the new disk are deleted
    10. Verify orphaned directories in the duplicated disk are no deleted
    """

    disk_names = ["vol-disk-" + generate_random_id(4),
                  "vol-disk-" + generate_random_id(4)]

    # Step 1
    disk_paths = []

    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, [disk_names[0]], request)

    # Step 2: create duplicated disks for node
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    disk_path = os.path.join(disk_paths[0], disk_names[1])
    disk_paths.append(disk_path)
    exec_nsenter("mkdir -p {}".format(disk_path))
    disk2 = {"path": disk_path, "allowScheduling": True}

    update_disk = get_update_disks(disks)
    update_disk[disk_names[1]] = disk2
    node = node.diskUpdate(disks=update_disk)
    node = wait_for_disk_update(client, lht_hostId, len(update_disk))

    # Step 3
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 4
    num_orphans = 5
    create_orphaned_directories_on_host(volume, disk_paths, num_orphans)

    # Step 5
    cleanup_volume_by_name(client, volume_name)

    # Step 6
    assert wait_for_orphan_count(client, num_orphans, 180) == num_orphans

    # Step 7
    delete_orphans(client)

    # Step 8
    count = wait_for_orphan_count(client, 0, 180)
    assert count == 0

    # Step 9: The orphaned directories in the ready disk should be deleted
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               0,
                               180) == 0

    # Step 10: The orphaned directories in the duplicated disk should not be
    # deleted
    assert wait_for_file_count(os.path.join(disk_paths[1], "replicas"),
                               num_orphans,
                               180) == num_orphans


@pytest.mark.orphan
def test_orphan_with_same_orphaned_dir_name_in_another_disk(client, volume_name, request):  # NOQA
    """
    Test orphan creation and deletion with same orphaned dir name in
    another disk
    1. Create a volume and attach to the current node's default disk
    2. Create a new disks for holding orphaned replica directories
    3. Create orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CRs for replica directories
    6. Delete the orphaned replica directories
    7. Verify orphan list is empty
    """

    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 2
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 3
    create_orphaned_directories_on_host(volume, disk_paths, 1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6
    delete_orphans(client)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0


@pytest.mark.orphan
def test_orphan_creation_and_deletion_in_multiple_disks(client, volume_name, request):  # NOQA
    """
    Test orphan creation and deletion in multiple disks
    1. Create multiple new-disks for holding orphaned replica directories
    2. Create a volume and attach to the current node
    3. Create multiple orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CRs for replica
       directories
    6. Delete all orphaned CRs
    7. Verify orphan list is empty
    8. Verify orphaned replica directories are deleted
    """

    disk_names = ["vol-disk-" + generate_random_id(4),
                  "vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    num_orphans = 5
    create_orphaned_directories_on_host(volume, disk_paths, num_orphans)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    count = wait_for_orphan_count(client,
                                  num_orphans * len(disk_paths),
                                  180)
    assert count == num_orphans * len(disk_paths)

    # Step 6
    delete_orphans(client)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0

    # Step 8
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               0,
                               180) == 0

    assert wait_for_file_count(os.path.join(disk_paths[1], "replicas"),
                               0,
                               180) == 0


@pytest.mark.orphan
def test_orphan_creation_and_background_deletion_in_multiple_disks(client, volume_name, request):  # NOQA
    """
    Test orphaned dirs creation and background deletion in multiple disks
    1. Create multiple new-disks for holding orphaned replica directories
    2. Create a volume and attach to the current node
    3. Create multiple orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CRs for replica
       directories
    6. Delete the orphaned replica directories in background
    7. Verify orphan list is empty
    """

    disk_names = ["vol-disk-" + generate_random_id(4),
                  "vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    num_orphans = 5
    orphaned_directories = create_orphaned_directories_on_host(volume,
                                                               disk_paths,
                                                               num_orphans)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    count = wait_for_orphan_count(client,
                                  num_orphans * len(disk_paths),
                                  180)
    assert count == num_orphans * len(disk_paths)

    # Step 6
    delete_orphaned_directory_on_host(orphaned_directories)

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0


@pytest.mark.orphan
def test_orphan_auto_deletion(client, volume_name, request):  # NOQA
    """
    Test orphaned dirs creation and background deletion in multiple disks
    1. Create a new disks for holding orphaned replica directories
    2. Create a volume and attach to the current node
    3. Create orphaned replica directories by copying the active
       replica directory
    4. Clean up volume
    5. Verify orphan list contains the orphan CRs for replica
       directories
    6. Enable the orphan-auto-deletion setting
    7. Verify orphan list is empty and the orphaned directory is
       deleted in background
    8. Clean up disk
    """
    disk_names = ["vol-disk-" + generate_random_id(4)]

    # Step 1
    lht_hostId = get_self_host_id()
    cleanup_node_disks(client, lht_hostId)
    disk_paths = crate_disks_on_host(client, disk_names, request)

    # Step 2
    volume = create_volume_with_replica_on_each_node(client, volume_name)

    # Step 3
    create_orphaned_directories_on_host(volume, disk_paths, 1)

    # Step 4
    cleanup_volume_by_name(client, volume_name)

    # Step 5
    assert wait_for_orphan_count(client, 1, 180) == 1

    # Step 6: enable orphan auto deletion
    setting = client.by_id_setting(SETTING_ORPHAN_AUTO_DELETION)
    client.update(setting, value="true")

    # Step 7
    assert wait_for_orphan_count(client, 0, 180) == 0
    assert wait_for_file_count(os.path.join(disk_paths[0], "replicas"),
                               0,
                               180) == 0
