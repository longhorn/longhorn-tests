import pytest

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

from common import BACKING_IMAGE_NAME, BACKING_IMAGE_QCOW2_URL, \
    BACKING_IMAGE_RAW_URL, BACKING_IMAGE_EXT4_SIZE


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
        backing_image.backingImageCleanup(diks=[random_disk_id])
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
def test_backup_with_backing_image(client, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        backup_test(client, volume_name, str(BACKING_IMAGE_EXT4_SIZE),
                    BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.coretest   # NOQA
@pytest.mark.backing_image  # NOQA
def test_backup_labels_with_backing_image(client, random_labels, volume_name):  # NOQA
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
def test_ha_backup_deletion_recovery(client, volume_name):  # NOQA
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
def test_csi_backup_with_backing_image(client, core_api, csi_pv, pvc, pod_make):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        csi_backup_test(client, core_api, csi_pv, pvc, pod_make,
                        BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)


@pytest.mark.backing_image
@pytest.mark.recurring_job
def test_recurring_job_labels_with_backing_image(client, random_labels, volume_name):  # NOQA
    for bi_url in (BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_RAW_URL):
        create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, bi_url)
        recurring_job_labels_test(client, random_labels, volume_name,
                                  str(BACKING_IMAGE_EXT4_SIZE),
                                  BACKING_IMAGE_NAME)
        cleanup_all_volumes(client)
        cleanup_all_backing_images(client)
