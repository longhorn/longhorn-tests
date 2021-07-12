import os
import subprocess

import pytest

from backupstore import set_random_backupstore  # NOQA
from common import client, random_labels, volume_name, core_api  # NOQA
from common import csi_pv, pvc, pod_make  # NOQA
from common import csi_pv_backingimage, pvc_backingimage  # NOQA
from common import disable_auto_salvage  # NOQA

from test_basic import volume_basic_test, volume_iscsi_basic_test,\
    snapshot_test, backup_test, backup_labels_test
from test_engine_upgrade import engine_offline_upgrade_test, \
    engine_live_upgrade_test, engine_live_upgrade_rollback_test
from test_ha import ha_simple_recovery_test, ha_salvage_test, \
    ha_backup_deletion_recovery_test
from test_csi import csi_mount_test, csi_io_test, csi_backup_test
from test_recurring_job import recurring_job_labels_test

from common import get_self_host_id
from common import create_and_check_volume, wait_for_volume_healthy, \
    wait_for_volume_delete, cleanup_all_volumes
from common import create_backing_image_with_matching_url, \
    wait_for_backing_image_disk_cleanup, cleanup_all_backing_images
from common import get_volume_endpoint, mount_disk, cleanup_host_disk
from common import write_volume_random_data, check_volume_data

from common import BACKING_IMAGE_NAME, BACKING_IMAGE_QCOW2_URL, \
    BACKING_IMAGE_RAW_URL, BACKING_IMAGE_EXT4_SIZE, \
    DIRECTORY_PATH


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_backing_image_basic_operation(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        backing_image_basic_operation_test(
            client, volume_name, BACKING_IMAGE_NAME, bi_url)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


def backing_image_basic_operation_test(client, volume_name, bi_name, bi_url):  # NOQA
    """
    Test Backing Image APIs.

    1. Create a backing image.
    2. Create and attach a Volume with the backing image set.
    3. Verify that the all disk states in the backing image are "downloaded".
    4. Try to use the API to manually clean up one disk for the backing image
       but get failed.
    5. Try to use the API to directly delete the backing image
       but get failed.
    6. Delete the volume.
    7. Use the API to manually clean up one disk for the backing image
    8. Delete the backing image.
    """

    volume = create_and_check_volume(
        client, volume_name, 3,
        str(BACKING_IMAGE_EXT4_SIZE), bi_name)
    lht_host_id = get_self_host_id()
    volume.attach(hostId=lht_host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert volume.backingImage == bi_name
    assert volume.size == str(BACKING_IMAGE_EXT4_SIZE)

    random_disk_id = ""
    backing_image = client.by_id_backing_image(bi_name)
    assert backing_image.imageURL == bi_url
    assert not backing_image.deletionTimestamp
    assert len(backing_image.diskStateMap) == 3
    for disk_id, state in iter(backing_image.diskStateMap.items()):
        assert state == "downloaded"
        random_disk_id = disk_id
    assert random_disk_id != ''

    with pytest.raises(Exception):
        backing_image.backingImageCleanup(disks=[random_disk_id])
    with pytest.raises(Exception):
        client.delete(backing_image)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    backing_image = client.by_id_backing_image(bi_name)
    backing_image.backingImageCleanup(disks=[random_disk_id])
    backing_image = wait_for_backing_image_disk_cleanup(
        client, bi_name, random_disk_id)
    client.delete(backing_image)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_backing_image_content(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        backing_image_content_test(
            client, volume_name, BACKING_IMAGE_NAME, bi_url)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


def backing_image_content_test(client, volume_name_prefix, bi_name, bi_url):  # NOQA
    """
    Verify the content of the Backing Image is accessible and read-only for
    all volumes.

    1. Create a backing image. (Done by the caller)
    2. Create a Volume with the backing image set then attach it to host node.
    3. Verify that the all disk states in the backing image are "downloaded".
    4. Verify volume can be directly mounted and there is already data in the
       filesystem due to the backing image.
    5. Verify the volume r/w.
    6. Launch one more volume with the same backing image.
    7. Verify the data content of the new volume is the same as the data in
       step 4.
    5. Do cleanup. (Done by the caller)
    """
    lht_host_id = get_self_host_id()

    volume_name1 = volume_name_prefix + "-1"
    volume1 = create_and_check_volume(
        client, volume_name1, 3,
        str(BACKING_IMAGE_EXT4_SIZE), bi_name)
    volume1.attach(hostId=lht_host_id)
    volume1 = wait_for_volume_healthy(client, volume_name1)
    assert volume1.backingImage == bi_name
    assert volume1.size == str(BACKING_IMAGE_EXT4_SIZE)

    backing_image = client.by_id_backing_image(bi_name)
    assert backing_image.imageURL == bi_url
    assert not backing_image.deletionTimestamp
    assert len(backing_image.diskStateMap) == 3
    for disk_id, state in iter(backing_image.diskStateMap.items()):
        assert state == "downloaded"

    # Since there is already a filesystem with data in the backing image,
    # we can directly mount and access the volume without `mkfs`.
    dev1 = get_volume_endpoint(volume1)
    mount_path1 = os.path.join(DIRECTORY_PATH, volume_name1)
    mount_disk(dev1, mount_path1)
    output1 = subprocess.check_output(["ls", mount_path1])
    # The following random write may crash the filesystem of volume1,
    # need to umount it here
    cleanup_host_disk(volume_name1)

    # Verify r/w for the volume with a backing image
    data = write_volume_random_data(volume1)
    check_volume_data(volume1, data)

    volume_name2 = volume_name_prefix + "-2"
    volume2 = create_and_check_volume(
        client, volume_name2, 3,
        str(BACKING_IMAGE_EXT4_SIZE), bi_name)
    volume2.attach(hostId=lht_host_id)
    volume2 = wait_for_volume_healthy(client, volume_name2)
    assert volume1.backingImage == bi_name
    assert volume1.size == str(BACKING_IMAGE_EXT4_SIZE)
    dev2 = get_volume_endpoint(volume2)
    mount_path2 = os.path.join(DIRECTORY_PATH, volume_name2)
    mount_disk(dev2, mount_path2)
    output2 = subprocess.check_output(["ls", mount_path2])
    # The output is the content of the backing image, which should keep
    # unchanged
    assert output2 == output1

    cleanup_host_disk(volume_name2)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_volume_basic_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        volume_basic_test(client, volume_name, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_volume_iscsi_basic_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        volume_iscsi_basic_test(client, volume_name, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_snapshot_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        snapshot_test(client, volume_name, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_backup_with_backing_image(set_random_backupstore, client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        backup_test(client, volume_name, str(BACKING_IMAGE_EXT4_SIZE),
                    BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_backup_labels_with_backing_image(set_random_backupstore, client, random_labels, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        backup_labels_test(client, random_labels, volume_name,
                           str(BACKING_IMAGE_EXT4_SIZE), BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_ha_simple_recovery_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        ha_simple_recovery_test(client, volume_name,
                                str(BACKING_IMAGE_EXT4_SIZE),
                                BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image  # NOQA
def test_ha_salvage_with_backing_image(client, core_api, disable_auto_salvage, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        ha_salvage_test(client, core_api, volume_name, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image  # NOQA
def test_ha_backup_deletion_recovery(set_random_backupstore, client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        ha_backup_deletion_recovery_test(client, volume_name,
                                         str(BACKING_IMAGE_EXT4_SIZE),
                                         BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image  # NOQA
def test_engine_offline_upgrade_with_backing_image(client, core_api, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        engine_offline_upgrade_test(client, core_api, volume_name,
                                    BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_engine_live_upgrade_with_backing_image(client, core_api, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        engine_live_upgrade_test(client, core_api, volume_name,
                                 BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image  # NOQA
def test_engine_live_upgrade_rollback_with_backing_image(client, core_api, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        engine_live_upgrade_rollback_test(client, core_api, volume_name,
                                          BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_mount_with_backing_image(client, core_api, csi_pv_backingimage, pvc_backingimage, pod_make):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        csi_mount_test(client, core_api,
                       csi_pv_backingimage, pvc_backingimage, pod_make,
                       BACKING_IMAGE_EXT4_SIZE, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_io_with_backing_image(client, core_api, csi_pv_backingimage, pvc_backingimage, pod_make):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        csi_io_test(client, core_api,
                    csi_pv_backingimage, pvc_backingimage, pod_make)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest  # NOQA
@pytest.mark.backing_image  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_backup_with_backing_image(set_random_backupstore, client, core_api, csi_pv, pvc, pod_make):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        csi_backup_test(client, core_api, csi_pv, pvc, pod_make,
                        BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image
@pytest.mark.recurring_job
def test_recurring_job_labels_with_backing_image(set_random_backupstore, client, random_labels, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        recurring_job_labels_test(client, random_labels, volume_name,
                                  str(BACKING_IMAGE_EXT4_SIZE),
                                  BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.skip(reason="TODO") # NOQA
@pytest.mark.backing_image  # NOQA
def test_backing_image_with_disk_migration():  # NOQA
    """
    1. Update settings:
       1. Disable Node Soft Anti-affinity.
       2. Set Replica Replenishment Wait Interval to a relatively long value.
    2. Create a new host disk.
    3. Disable the default disk and add the extra disk with scheduling enabled
       for the current node.
    4. Create a backing image.
    5. Create and attach a 2-replica volume with the backing image set.
       Then verify:
       1. there is a replica scheduled to the new disk.
       2. there are 2 entries in the backing image download state map,
          and both are state `downloaded`.
    6. Directly mount the volume (without making filesystem) to a directory.
       Then verify the content of the backing image by checking the existence
       of the directory `<Mount point>/guests/`.
    7. Write random data to the mount point then verify the data.
    8. Unmount the host disk. Then verify:
       1. The replica in the host disk will be failed.
       2. The disk state in the backing image will become failed.
       3. The related download pod named
          `<Backing image name>-<First 8 characters of disk UUID>` is removed.
    9. Remount the host disk to another path. Then create another Longhorn disk
       based on the migrated path (disk migration).
    10. Verify the followings.
        1. The disk added in step3 (before the migration) should
           be "unschedulable".
        2. The disk added in step9 (after the migration) should
           become "schedulable".
        3. The failed replica will be reused. And the replica DiskID as well as
           the disk path is updated.
        4. The 2-replica volume r/w works fine.
        5. The download state in the backing image will become `downloaded`.
        6. The related download pod will be recreated.
    11. Do cleanup.
    """
