import os
import subprocess

import pytest

from backupstore import set_random_backupstore, backupstore_cleanup  # NOQA
from common import client, random_labels, volume_name, core_api  # NOQA
from common import csi_pv, pvc, pod_make  # NOQA
from common import csi_pv_backingimage, pvc_backingimage  # NOQA
from common import disable_auto_salvage  # NOQA

from test_basic import volume_basic_test, volume_iscsi_basic_test, \
    snapshot_test, snapshot_prune_test, \
    snapshot_prune_and_coalesce_simultaneously, \
    backup_test, backup_labels_test
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
from common import cleanup_all_recurring_jobs

from common import BACKING_IMAGE_NAME, BACKING_IMAGE_QCOW2_URL, \
    BACKING_IMAGE_RAW_URL, BACKING_IMAGE_EXT4_SIZE, \
    DIRECTORY_PATH, BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD, \
    BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME, Gi

from common import wait_for_volume_detached
from common import wait_for_backing_image_status
from common import wait_for_backing_image_in_disk_fail
from common import get_disk_uuid
from common import write_volume_dev_random_mb_data, get_device_checksum
from common import check_backing_image_disk_map_status
from common import LONGHORN_NAMESPACE, RETRY_EXEC_COUNTS, RETRY_INTERVAL
from common import BACKING_IMAGE_QCOW2_CHECKSUM
from common import BACKING_IMAGE_STATE_READY
from common import BACKING_IMAGE_STATE_FAILED_AND_CLEANUP
from common import BACKING_IMAGE_STATE_IN_PROGRESS
from common import RETRY_COUNTS_LONG
import time


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

    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3,
                                     size=str(BACKING_IMAGE_EXT4_SIZE),
                                     backing_image=bi_name)
    lht_host_id = get_self_host_id()
    volume.attach(hostId=lht_host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert volume.backingImage == bi_name
    assert volume.size == str(BACKING_IMAGE_EXT4_SIZE)

    random_disk_id = ""
    backing_image = client.by_id_backing_image(bi_name)
    assert backing_image.sourceType == BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD
    assert backing_image.parameters["url"] == bi_url
    assert backing_image.currentChecksum != ""
    assert not backing_image.deletionTimestamp
    assert len(backing_image.diskFileStatusMap) == 3
    for disk_id, status in iter(backing_image.diskFileStatusMap.items()):
        assert status.state == BACKING_IMAGE_STATE_READY
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
    volume1 = create_and_check_volume(client, volume_name1,
                                      num_of_replicas=3,
                                      size=str(BACKING_IMAGE_EXT4_SIZE),
                                      backing_image=bi_name)
    volume1.attach(hostId=lht_host_id)
    volume1 = wait_for_volume_healthy(client, volume_name1)
    assert volume1.backingImage == bi_name
    assert volume1.size == str(BACKING_IMAGE_EXT4_SIZE)

    backing_image = client.by_id_backing_image(bi_name)
    assert backing_image.sourceType == BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD
    assert backing_image.parameters["url"] == bi_url
    assert backing_image.currentChecksum != ""
    assert not backing_image.deletionTimestamp
    assert len(backing_image.diskFileStatusMap) == 3
    for disk_id, status in iter(backing_image.diskFileStatusMap.items()):
        assert status.state == BACKING_IMAGE_STATE_READY

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
    volume2 = create_and_check_volume(client, volume_name2,
                                      num_of_replicas=3,
                                      size=str(BACKING_IMAGE_EXT4_SIZE),
                                      backing_image=bi_name)
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
def test_snapshot_prune_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        snapshot_prune_test(client, volume_name, BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_snapshot_prune_and_coalesce_simultaneously_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        snapshot_prune_and_coalesce_simultaneously(
            client, volume_name, BACKING_IMAGE_NAME)
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
        backupstore_cleanup(client)


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
        backupstore_cleanup(client)


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
        backupstore_cleanup(client)


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
        backupstore_cleanup(client)


@pytest.mark.backing_image  # NOQA
@pytest.mark.recurring_job  # NOQA
def test_recurring_job_labels_with_backing_image(set_random_backupstore, client, random_labels, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        recurring_job_labels_test(client, random_labels, volume_name,
                                  str(BACKING_IMAGE_EXT4_SIZE),
                                  BACKING_IMAGE_NAME)
        cleanup_all_recurring_jobs(client)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)
        backupstore_cleanup(client)


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
       2. there are 2 entries in the backing image disk file status map,
          and both are state `ready`.
    6. Directly mount the volume (without making filesystem) to a directory.
       Then verify the content of the backing image by checking the existence
       of the directory `<Mount point>/guests/`.
    7. Write random data to the mount point then verify the data.
    8. Unmount the host disk. Then verify:
       1. The replica in the host disk will be failed.
       2. The disk state in the backing image will become `unknown`.
    9. Remount the host disk to another path. Then create another Longhorn disk
       based on the migrated path (disk migration).
    10. Verify the following.
        1. The disk added in step3 (before the migration) should
           be "unschedulable".
        2. The disk added in step9 (after the migration) should
           become "schedulable".
        3. The failed replica will be reused. And the replica DiskID as well as
           the disk path is updated.
        4. The 2-replica volume r/w works fine.
        5. The disk state in the backing image will become `ready` again.
    11. Do cleanup.
    """


@pytest.mark.backing_image  # NOQA
def test_exporting_backing_image_from_volume(client, volume_name):  # NOQA
    """
    1. Create and attach the 1st volume.
    2. Make a filesystem for the 1st volume.
    3. Export this volume to the 1st backing image
       via the backing image creation HTTP API. And the export type is qcow2.
    4. Create and attach the 2nd volume which uses the 1st backing image.
    5. Make sure the 2nd volume can be directly mount.
    6. Write random data to the mount point then get the checksum.
    7. Unmount and detach the 2nd volume.
    8. Export the 2nd volume as the 2nd backing image.
       Remember to set the export type to qcow2.
    9. Create and attach the 3rd volume which uses the 2nd backing image.
    10. Directly mount the 3rd volume. Then verify the data in the 3rd volume
        is the same as that of the 2nd volume.
    11. Do cleanup.
    """

    # Step1, Step2
    hostId = get_self_host_id()
    volume1_name = "vol1"
    volume1 = create_and_check_volume(
        client, volume_name=volume1_name, size=str(1 * Gi))

    volume1 = volume1.attach(hostId=hostId)
    volume1 = wait_for_volume_healthy(client, volume1_name)

    # Step3
    backing_img1_name = 'bi-test1'
    backing_img1 = client.create_backing_image(
            name=backing_img1_name,
            sourceType=BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME,
            parameters={"export-type": "qcow2", "volume-name": volume1_name},
            expectedChecksum="")

    # Step4
    volume2_name = "vol2"
    volume2 = create_and_check_volume(
        client, volume_name=volume2_name, size=str(1 * Gi),
        backing_image=backing_img1["name"])
    volume2 = volume2.attach(hostId=hostId)
    volume2 = wait_for_volume_healthy(client, volume2_name, 300)

    # Step5, 6
    data2 = write_volume_random_data(volume2)

    # Step7
    volume2.detach()
    volume2 = wait_for_volume_detached(client, volume2_name)

    # Step8
    backing_img2 = client.create_backing_image(
            name="bi-test2",
            sourceType=BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME,
            parameters={"export-type": "qcow2", "volume-name": volume2_name},
            expectedChecksum="")

    # Step9
    volume3_name = "vol3"
    volume3 = create_and_check_volume(
        client, volume_name=volume3_name, size=str(1 * Gi),
        backing_image=backing_img2["name"])
    volume3 = volume3.attach(hostId=hostId)
    volume3 = wait_for_volume_healthy(client, volume3_name, 300)

    # Step10
    check_volume_data(volume3, data2)

@pytest.mark.backing_image  # NOQA
@pytest.mark.parametrize("bi_url", [BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL]) # NOQA
def test_backing_image_auto_resync(bi_url, client, volume_name):  # NOQA
    """
    1. Create a backing image.
    2. Create and attach a 3-replica volume using the backing image.
    3. Wait for the attachment complete.
    4. Manually remove the backing image on the current node.
    5. Wait for the file state in the disk/on this node become failed.
    6. Wait for the file recovering automatically.
    7. Validate the volume.
    """
    # Step 1
    create_backing_image_with_matching_url(
              client, BACKING_IMAGE_NAME, bi_url)

    # Step 2
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3,
                                     size=str(BACKING_IMAGE_EXT4_SIZE),
                                     backing_image=BACKING_IMAGE_NAME)

    # Step 3
    lht_host_id = get_self_host_id()
    volume.attach(hostId=lht_host_id)
    volume = wait_for_volume_healthy(client, volume_name)
    assert volume.backingImage == BACKING_IMAGE_NAME
    assert volume.size == str(BACKING_IMAGE_EXT4_SIZE)

    # Step 4
    subprocess.check_output(['rm', '-rf', '/var/lib/longhorn/backing-images/'])

    # Step 5
    disk_uuid = get_disk_uuid()
    wait_for_backing_image_in_disk_fail(client, BACKING_IMAGE_NAME, disk_uuid)

    # Step 6
    wait_for_backing_image_status(client, BACKING_IMAGE_NAME,
                                  BACKING_IMAGE_STATE_READY)

    # Step 7
    volume = wait_for_volume_healthy(client, volume_name)
    assert volume.backingImage == BACKING_IMAGE_NAME
    assert volume.size == str(BACKING_IMAGE_EXT4_SIZE)


@pytest.mark.backing_image  # NOQA
def test_backing_image_cleanup(core_api, client):  # NOQA
    """
    1. Create multiple backing image.
    2. Create and attach multiple 3-replica volume using those backing image.
    3. Wait for the attachment complete.
    4. Delete the volumes then the backing images.
    5. Verify all backing image manager pods will be terminated when the last
       backing image is gone.
    6. Repeat step1 to step5 for multiple times. Make sure each time the test
       is using the same the backing image namings.
    """
    for i in range(3):
        backing_image_cleanup(core_api, client)


def backing_image_cleanup(core_api, client): # NOQA
    # Step 1
    backing_img1_name = 'bi-test1'
    create_backing_image_with_matching_url(
            client, backing_img1_name, BACKING_IMAGE_QCOW2_URL)

    backing_img2_name = 'bi-test2'
    create_backing_image_with_matching_url(
            client, backing_img2_name, BACKING_IMAGE_RAW_URL)

    # Step 2
    lht_host_id = get_self_host_id()
    volume1 = create_and_check_volume(client, "vol-1",
                                      size=str(1 * Gi),
                                      backing_image=backing_img1_name)

    volume2 = create_and_check_volume(client, "vol-2",
                                      size=str(1 * Gi),
                                      backing_image=backing_img2_name)

    # Step 3
    volume1.attach(hostId=lht_host_id)
    volume1 = wait_for_volume_healthy(client, volume1.name)
    volume2.attach(hostId=lht_host_id)
    volume2 = wait_for_volume_healthy(client, volume2.name)
    assert volume1.backingImage == backing_img1_name
    assert volume2.backingImage == backing_img2_name

    # Step 4
    cleanup_all_volumes(client)
    cleanup_all_backing_images(client)

    # Step 5
    for i in range(RETRY_EXEC_COUNTS):
        exist = False
        pods = core_api.list_namespaced_pod(LONGHORN_NAMESPACE)
        for pod in pods.items:
            if "backing-image-manager" in pod.metadata.name:
                exist = True
                time.sleep(RETRY_INTERVAL)
                continue
        if exist is False:
            break

    assert exist is False


@pytest.mark.backing_image  # NOQA
@pytest.mark.parametrize("bi_url", [BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL]) # NOQA
def test_backing_image_with_wrong_md5sum(bi_url, client): # NOQA

    backing_image_wrong_checksum = \
            BACKING_IMAGE_QCOW2_CHECKSUM[1:] + BACKING_IMAGE_QCOW2_CHECKSUM[0]

    client.create_backing_image(name=BACKING_IMAGE_NAME,
                                sourceType=BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD,
                                parameters={"url": bi_url},
                                expectedChecksum=backing_image_wrong_checksum)

    wait_for_backing_image_status(client, BACKING_IMAGE_NAME,
                                  BACKING_IMAGE_STATE_FAILED_AND_CLEANUP)


def test_volume_wait_for_backing_image_condition(client): # NOQA
    """
    Test the volume condition "WaitForBackingImage"

    Given
    - Create a BackingImage

    When
    - Creating the Volume with the BackingImage while it is still in progress

    Then
    - The condition "WaitForBackingImage" of the Volume
      would be first True and then change to False when
      the BackingImage is ready and all the replicas are in running state.
    """
    # Create a large volume and export as backingimage
    lht_host_id = get_self_host_id()

    volume1_name = "vol1"
    volume1 = create_and_check_volume(client, volume1_name,
                                      num_of_replicas=3,
                                      size=str(1 * Gi))
    volume1.attach(hostId=lht_host_id)
    volume1 = wait_for_volume_healthy(client, volume1_name)
    volume_endpoint = get_volume_endpoint(volume1)
    write_volume_dev_random_mb_data(volume_endpoint, 1, 500)
    vol1_cksum = get_device_checksum(volume_endpoint)

    backing_img_name = 'bi-test'
    backing_img = client.create_backing_image(
            name=backing_img_name,
            sourceType=BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME,
            parameters={"export-type": "qcow2", "volume-name": volume1_name},
            expectedChecksum="")

    # Create volume with that backing image
    volume2_name = "vol2"
    volume2 = create_and_check_volume(client, volume2_name,
                                      size=str(1 * Gi),
                                      backing_image=backing_img["name"])

    volume2.attach(hostId=lht_host_id)

    if check_backing_image_disk_map_status(client,
                                           backing_img_name,
                                           1,
                                           BACKING_IMAGE_STATE_IN_PROGRESS):
        volume2 = client.by_id_volume(volume2_name)
        assert volume2.conditions.WaitForBackingImage.status == "True"

    # Check volume healthy, and backing image ready
    volume2 = wait_for_volume_healthy(client, volume2_name, RETRY_COUNTS_LONG)
    assert volume2.conditions.WaitForBackingImage.status == "False"
    check_backing_image_disk_map_status(client, backing_img_name, 3, "ready")

    volume_endpoint = get_volume_endpoint(volume2)
    vol2_cksum = get_device_checksum(volume_endpoint)
    assert vol1_cksum == vol2_cksum
