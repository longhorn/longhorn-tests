import pytest

import common
import time
from common import client, core_api, volume_name # NOQA
from common import SIZE
from common import check_volume_data, get_self_host_id
from common import wait_for_volume_current_image, wait_for_volume_delete
from common import wait_for_volume_detached
from common import wait_for_engine_image_deletion
from common import wait_for_engine_image_ref_count, wait_for_engine_image_state
from common import get_volume_engine, write_volume_random_data
from common import check_volume_endpoint
from common import wait_for_volume_replicas_mode
from common import pod_make  # NOQA
from common import create_pv_for_volume, create_pvc_for_volume
from common import create_pvc_spec
from common import create_and_check_volume, create_and_wait_pod
from common import delete_and_wait_pod
from common import write_pod_volume_random_data, get_pod_data_md5sum
from common import copy_pod_volume_data
from common import Gi
from common import get_engine_image_status_value
from common import update_setting, wait_for_volume_healthy
from common import get_volume_endpoint, write_volume_dev_random_mb_data
from common import wait_for_rebuild_complete, RETRY_COUNTS, RETRY_INTERVAL
from common import wait_for_rebuild_start
from common import create_backup, wait_for_backup_restore_completed
from common import SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT
from test_settings import delete_replica_on_test_node
from backupstore import set_random_backupstore # NOQA

REPLICA_COUNT = 2
ENGINE_IMAGE_TEST_REPEAT_COUNT = 5

# Size in MiB
RANDOM_DATA_SIZE_SMALL = 100
RANDOM_DATA_SIZE_LARGE = 800


def test_engine_image(client, core_api, volume_name):  # NOQA
    """
    Test Engine Image deployment

    1. List Engine Images and validate basic properities.
    2. Try deleting default engine image and it should fail.
    3. Try creating a duplicate engine image as default and it should fail
    4. Get upgrade test image for the same versions
    5. Test if the upgrade test image can be deployed and deleted correctly
    """
    # can be leftover
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    ei_state = get_engine_image_status_value(client, default_img_name)

    images = client.list_engine_image()
    assert len(images) == 1
    assert images[0].default
    assert images[0].state == ei_state
    assert images[0].refCount == 0
    assert images[0].gitCommit != ""
    assert images[0].buildDate != ""

    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion

    assert cli_v != 0
    assert cli_minv != 0
    assert ctl_v != 0
    assert ctl_minv != 0
    assert data_v != 0
    assert data_minv != 0

    # delete default image is not allowed
    with pytest.raises(Exception) as e:
        client.delete(images[0])
    assert "the default engine image" in str(e.value)

    # duplicate images
    with pytest.raises(Exception) as e:
        client.create_engine_image(image=default_img.image)

    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    # test if engine image can be created and cleaned up successfully
    for _ in range(ENGINE_IMAGE_TEST_REPEAT_COUNT):
        new_img = client.create_engine_image(image=engine_upgrade_image)
        new_img_name = new_img.name
        new_img = wait_for_engine_image_state(client,
                                              new_img_name,
                                              ei_state)
        assert not new_img.default
        assert new_img.state == ei_state
        assert new_img.refCount == 0
        assert new_img.cliAPIVersion != 0
        assert new_img.cliAPIMinVersion != 0
        assert new_img.controllerAPIVersion != 0
        assert new_img.controllerAPIMinVersion != 0
        assert new_img.dataFormatVersion != 0
        assert new_img.dataFormatMinVersion != 0
        assert new_img.gitCommit != ""
        assert new_img.buildDate != ""

        client.delete(new_img)
        wait_for_engine_image_deletion(client, core_api, new_img.name)


@pytest.mark.coretest   # NOQA
def test_engine_offline_upgrade(client, core_api, volume_name):  # NOQA
    """
    Test engine offline upgrade

    1. Get a compatible engine image with the default engine image, and deploy
    2. Create a volume using the default engine image
    3. Attach the volume and write `data` into it
    4. Detach the volume and upgrade the volume engine to the new engine image
    5. Make sure the new engine image reference count has increased to 1
    6. Make sure we cannot delete the new engine image now (due to reference)
    7. Attach the volume and verify it's using the new image
    8. Verify the data. And verify engine and replicas' engine image changed
    9. Detach the volume
    10. Upgrade to the old engine image
    11. Verify the volume's engine image has been upgraded
    12. Attach the volume and verify the `data`
    """
    engine_offline_upgrade_test(client, core_api, volume_name)


def engine_offline_upgrade_test(client, core_api, volume_name, backing_image=""):  # NOQA
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img.name
    ei_status_value = get_engine_image_status_value(client, new_img_name)
    new_img = wait_for_engine_image_state(client,
                                          new_img_name,
                                          ei_status_value)
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT,
                                  backingImage=backing_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    # expected refCount is equal to 1 volume + 1 engine + number of replicas
    expect_ref_count = 2 + REPLICA_COUNT
    default_img = wait_for_engine_image_ref_count(client,
                                                  default_img_name,
                                                  expect_ref_count)

    original_engine_image = default_img.image

    assert volume.name == volume_name
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    assert volume.backingImage == backing_image

    # Before our upgrade, write data to the volume first.
    host_id = get_self_host_id()
    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    data = write_volume_random_data(volume)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.engineUpgrade(image=engine_upgrade_image)
    volume = wait_for_volume_current_image(client, volume_name,
                                           engine_upgrade_image)
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    new_img = wait_for_engine_image_ref_count(client,
                                              new_img_name,
                                              expect_ref_count)

    # cannot delete a image in use
    with pytest.raises(Exception) as e:
        client.delete(new_img)
    assert "while being used" in str(e.value)

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    assert engine.currentImage == engine_upgrade_image
    for replica in volume.replicas:
        assert replica.engineImage == engine_upgrade_image
        assert replica.currentImage == engine_upgrade_image

    check_volume_data(volume, data)

    volume = volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.engineUpgrade(image=original_engine_image)
    volume = wait_for_volume_current_image(client, volume_name,
                                           original_engine_image)
    engine = get_volume_engine(volume)
    assert volume.engineImage == original_engine_image
    assert engine.engineImage == original_engine_image
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image

    default_img = wait_for_engine_image_ref_count(client,
                                                  default_img_name,
                                                  expect_ref_count)
    new_img = wait_for_engine_image_ref_count(client, new_img_name, 0)

    volume = volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image
        assert replica.currentImage == original_engine_image

    check_volume_data(volume, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)
    wait_for_engine_image_deletion(client, core_api, new_img.name)


@pytest.mark.coretest   # NOQA
def test_engine_live_upgrade(client, core_api, volume_name):  # NOQA
    """
    Test engine live upgrade

    1. Deploy a compatible new engine image
    2. Create a volume (with the old default engine image)
    3. Attach the volume and write `data` to it
    4. Upgrade the volume when it's attached, to the new engine image
    5. Wait until the upgrade completed, verify the volume engine image changed
    6. Wait for new replica mode update then check the engine status.
    7. Verify the reference count of the new engine image changed
    8. Verify all engine and replicas' engine image changed
    9. Check volume `data`
    10. Detach the volume. Check engine and replicas's engine image again.
    11. Attach the volume.
    12. Check engine/replica engine image. Check data after reattach.
    13. Live upgrade to the original engine image,
    14. Wait for new replica mode update then check the engine status.
    15. Check old and new engine image reference count (new 0, old 1)
    16. Verify all the engine and replica images should be the old image
    17. Check volume data
    18. Detach the volume. Make sure engine and replica images are old image
    """
    engine_live_upgrade_test(client, core_api, volume_name)


def engine_live_upgrade_test(client, core_api, volume_name, backing_image=""):  # NOQA
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img.name
    ei_status_value = get_engine_image_status_value(client, new_img_name)
    new_img = wait_for_engine_image_state(client,
                                          new_img_name,
                                          ei_status_value)
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=REPLICA_COUNT,
                         backingImage=backing_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    # ei refCount is equal to 1 volume + 1 engine and REPLICA_COUNT replicas
    expected_ref_count = 2 + len(volume.replicas)
    wait_for_engine_image_ref_count(client,
                                    default_img_name,
                                    expected_ref_count)

    assert volume.name == volume_name
    assert volume.backingImage == backing_image

    original_engine_image = volume.engineImage
    assert original_engine_image != engine_upgrade_image

    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image
        assert replica.currentImage == original_engine_image

    data = write_volume_random_data(volume)

    volume.engineUpgrade(image=engine_upgrade_image)
    wait_for_volume_current_image(client, volume_name, engine_upgrade_image)
    # Need to wait for Longhorn to get and update the mode for new replicas
    volume = wait_for_volume_replicas_mode(client, volume_name, "RW")
    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    check_volume_endpoint(volume)

    wait_for_engine_image_ref_count(client, default_img_name, 0)

    # ei refCount is equal to 1 volume + 1 engine and REPLICA_COUNT replicas
    expected_ref_count = 2 + len(volume.replicas)
    wait_for_engine_image_ref_count(client,
                                    new_img_name,
                                    expected_ref_count)

    count = 0
    # old replica may be in deletion process
    for replica in volume.replicas:
        if replica.currentImage == engine_upgrade_image:
            count += 1
    assert count == REPLICA_COUNT

    check_volume_data(volume, data)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == REPLICA_COUNT
    assert volume.engineImage == engine_upgrade_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    for replica in volume.replicas:
        assert replica.engineImage == engine_upgrade_image

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)
    assert volume.engineImage == engine_upgrade_image
    assert volume.currentImage == engine_upgrade_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    assert engine.currentImage == engine_upgrade_image
    check_volume_endpoint(volume)
    for replica in volume.replicas:
        assert replica.engineImage == engine_upgrade_image
        assert replica.currentImage == engine_upgrade_image

    # Make sure detaching didn't somehow interfere with the data.
    check_volume_data(volume, data)

    volume.engineUpgrade(image=original_engine_image)
    wait_for_volume_current_image(client, volume_name,
                                  original_engine_image)
    volume = wait_for_volume_replicas_mode(client, volume_name, "RW")
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image
    check_volume_endpoint(volume)

    # ei refCount is equal to 1 volume + 1 engine and REPLICA_COUNT replicas
    expected_ref_count = 2 + len(volume.replicas)
    wait_for_engine_image_ref_count(client,
                                    default_img_name,
                                    expected_ref_count)
    new_img = wait_for_engine_image_ref_count(client, new_img_name, 0)

    assert volume.engineImage == original_engine_image

    count = 0
    # old replica may be in deletion process
    for replica in volume.replicas:
        if replica.engineImage == original_engine_image:
            count += 1
    assert count == REPLICA_COUNT

    check_volume_data(volume, data)

    volume.detach()
    volume = common.wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == REPLICA_COUNT

    assert volume.engineImage == original_engine_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)
    wait_for_engine_image_deletion(client, core_api, new_img.name)


def test_engine_image_incompatible(client, core_api, volume_name):  # NOQA
    """
    Test incompatible engine images

    1. Deploy incompatible engine images
    2. Make sure their state are `incompatible` once deployed.
    """
    images = client.list_engine_image()
    assert len(images) == 1
    ei_status_value = get_engine_image_status_value(client, images[0].name)
    assert images[0].default
    assert images[0].state == ei_status_value

    cli_v = images[0].cliAPIVersion
    cli_minv = images[0].cliAPIMinVersion
    ctl_v = images[0].controllerAPIVersion
    ctl_minv = images[0].controllerAPIMinVersion
    data_v = images[0].dataFormatVersion
    data_minv = images[0].dataFormatMinVersion

    fail_cli_v_image = common.get_compatibility_test_image(
        cli_minv - 1, cli_minv - 1,
        ctl_v, ctl_minv,
        data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_v_image)
    img = wait_for_engine_image_state(client, img.name, "incompatible")
    assert img.state == "incompatible"
    assert img.cliAPIVersion == cli_minv - 1
    assert img.cliAPIMinVersion == cli_minv - 1
    client.delete(img)
    wait_for_engine_image_deletion(client, core_api, img.name)

    fail_cli_minv_image = common.get_compatibility_test_image(
            cli_v + 1, cli_v + 1,
            ctl_v, ctl_minv,
            data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_minv_image)
    img = wait_for_engine_image_state(client, img.name, "incompatible")
    assert img.state == "incompatible"
    assert img.cliAPIVersion == cli_v + 1
    assert img.cliAPIMinVersion == cli_v + 1
    client.delete(img)
    wait_for_engine_image_deletion(client, core_api, img.name)


def test_engine_live_upgrade_rollback(client, core_api, volume_name):  # NOQA
    """
    Test engine live upgrade rollback

    1. Deploy `wrong_engine_upgrade_image` compatible upgrade engine image
        1. It's not functional but compatible per metadata.
    2. Create a volume with default engine image
    3. Attach it and write `data` into it.
    4. Live upgrade to the `wrong_engine_upgrade_image`
    5. Try to wait for the engine upgrade to complete. Expect it to timeout.
    6. Rollback by upgrading to the `original_engine_image`
    7. Make sure the rollback succeed and volume/engine engines are rolled back
    8. Wait for new replica mode update then check the engine status.
    9. Check the volume `data`.
    10. Live upgrade to the `wrong_engine_upgrade_image` again.
    11. Live upgrade will still fail.
    12. Detach the volume.
    13. The engine image for the volume will now be upgraded (since the `wrong`
    image is still compatible)
    14. Upgrade to the `original_engine_image` when detached
    15. Attach the volume and check states and `data`.
    """
    engine_live_upgrade_rollback_test(client, core_api, volume_name)


def engine_live_upgrade_rollback_test(client, core_api, volume_name, backing_image=""):  # NOQA
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    wrong_engine_upgrade_image = common.get_compatibility_test_image(
            cli_v, cli_minv,
            ctl_v, ctl_minv,
            data_v, data_minv)
    new_img = client.create_engine_image(image=wrong_engine_upgrade_image)
    new_img_name = new_img.name
    ei_status_value = get_engine_image_status_value(client, new_img_name)
    new_img = wait_for_engine_image_state(client,
                                          new_img_name,
                                          ei_status_value)
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=REPLICA_COUNT,
                         backingImage=backing_image)
    volume = common.wait_for_volume_detached(client, volume_name)

    # ei refCount is 1 volume + 1 engine + REPLICA_COUNT replicas
    expected_ref_count = 2 + len(volume.replicas)
    wait_for_engine_image_ref_count(client,
                                    default_img_name,
                                    expected_ref_count)
    assert volume.backingImage == backing_image

    original_engine_image = volume.engineImage
    assert original_engine_image != wrong_engine_upgrade_image

    host_id = get_self_host_id()
    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    data = write_volume_random_data(volume)

    volume.engineUpgrade(image=wrong_engine_upgrade_image)
    volume = client.by_id_volume(volume.name)
    assert volume.engineImage == wrong_engine_upgrade_image
    assert volume.currentImage == original_engine_image

    with pytest.raises(Exception):
        # this will timeout
        wait_for_volume_current_image(client, volume_name,
                                      wrong_engine_upgrade_image)

    # rollback
    volume.engineUpgrade(image=original_engine_image)
    wait_for_volume_current_image(client, volume_name,
                                  original_engine_image)
    volume = wait_for_volume_replicas_mode(client, volume_name, "RW")
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image

    volume = common.wait_for_volume_replica_count(client, volume_name,
                                                  REPLICA_COUNT)

    check_volume_data(volume, data)

    assert volume.state == common.VOLUME_STATE_ATTACHED
    assert volume.robustness == common.VOLUME_ROBUSTNESS_HEALTHY

    # try again, this time let's try detach
    volume.engineUpgrade(image=wrong_engine_upgrade_image)
    volume = client.by_id_volume(volume.name)
    assert volume.engineImage == wrong_engine_upgrade_image
    assert volume.currentImage == original_engine_image

    with pytest.raises(Exception):
        # this will timeout
        wait_for_volume_current_image(client, volume_name,
                                      wrong_engine_upgrade_image)

    volume.detach()
    volume = wait_for_volume_current_image(client, volume_name,
                                           wrong_engine_upgrade_image)
    # all the images would be updated
    assert volume.engineImage == wrong_engine_upgrade_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == wrong_engine_upgrade_image
    volume = common.wait_for_volume_replica_count(client, volume_name,
                                                  REPLICA_COUNT)
    for replica in volume.replicas:
        assert replica.engineImage == wrong_engine_upgrade_image

    # upgrade to the correct image when offline
    volume.engineUpgrade(image=original_engine_image)
    volume = wait_for_volume_current_image(client, volume_name,
                                           original_engine_image)
    volume = client.by_id_volume(volume.name)
    assert volume.engineImage == original_engine_image

    volume.attach(hostId=host_id)
    common.wait_for_volume_healthy(client, volume_name)
    volume = wait_for_volume_replicas_mode(client, volume_name, "RW")
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image
    check_volume_endpoint(volume)
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image
        assert replica.currentImage == original_engine_image

    check_volume_data(volume, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)
    wait_for_engine_image_deletion(client, core_api, new_img.name)


@pytest.mark.coretest   # NOQA
def test_engine_live_upgrade_with_intensive_data_writing(client, core_api, volume_name, pod_make):  # NOQA
    """
    Test engine live upgrade with intensive data writing

    1. Deploy a compatible new engine image
    2. Create a volume(with the old default engine image) with /PV/PVC/Pod
       and wait for pod to be deployed.
    3. Write data to a tmp file in the pod and get the md5sum
    4. Upgrade the volume to the new engine image without waiting.
    5. Keep copying data from the tmp file to the volume
       during the live upgrade.
    6. Wait until the upgrade completed, verify the volume engine image changed
    7. Wait for new replica mode update then check the engine status.
    8. Verify all engine and replicas' engine image changed
    9. Verify the reference count of the new engine image changed
    10. Check the existing data.
        Then write new data to the upgraded volume and get the md5sum.
    11. Delete the pod and wait for the volume detached.
        Then check engine and replicas's engine image again.
    12. Recreate the pod.
    13. Check if the attached volume is state `healthy`
        rather than `degraded`.
    14. Check the data.
    """
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img.name
    ei_status_value = get_engine_image_status_value(client, new_img_name)
    new_img = wait_for_engine_image_state(client,
                                          new_img_name,
                                          ei_status_value)
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)
    volume = create_and_check_volume(client, volume_name,
                                     num_of_replicas=3, size=str(1 * Gi))
    original_engine_image = volume.engineImage
    assert original_engine_image != engine_upgrade_image

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    volume = client.by_id_volume(volume_name)
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image
        assert replica.currentImage == original_engine_image

    data_path0 = "/tmp/test"
    data_path1 = "/data/test1"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path0, RANDOM_DATA_SIZE_LARGE)
    original_md5sum1 = get_pod_data_md5sum(core_api, pod_name, data_path0)

    volume.engineUpgrade(image=engine_upgrade_image)
    # Keep writing data to the volume during the live upgrade
    copy_pod_volume_data(core_api, pod_name, data_path0, data_path1)

    # Wait for live upgrade complete
    wait_for_volume_current_image(client, volume_name, engine_upgrade_image)
    volume = wait_for_volume_replicas_mode(client, volume_name, "RW")
    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    check_volume_endpoint(volume)

    wait_for_engine_image_ref_count(client, default_img_name, 0)

    # ei refCount is equal to 1 volume + 1 engine + the number of replicas
    expected_ref_count = 2 + len(volume.replicas)
    wait_for_engine_image_ref_count(client, new_img_name, expected_ref_count)

    volume_file_md5sum1 = get_pod_data_md5sum(
        core_api, pod_name, data_path1)
    assert volume_file_md5sum1 == original_md5sum1

    data_path2 = "/data/test2"
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path2, RANDOM_DATA_SIZE_SMALL)
    original_md5sum2 = get_pod_data_md5sum(core_api, pod_name, data_path2)

    delete_and_wait_pod(core_api, pod_name)
    volume = wait_for_volume_detached(client, volume_name)
    assert len(volume.replicas) == 3
    assert volume.engineImage == engine_upgrade_image
    engine = get_volume_engine(volume)
    assert engine.engineImage == engine_upgrade_image
    for replica in volume.replicas:
        assert replica.engineImage == engine_upgrade_image

    create_and_wait_pod(core_api, pod)
    common.wait_for_volume_healthy(client, volume_name)

    volume_file_md5sum1 = get_pod_data_md5sum(
        core_api, pod_name, data_path1)
    assert volume_file_md5sum1 == original_md5sum1
    volume_file_md5sum2 = get_pod_data_md5sum(
        core_api, pod_name, data_path2)
    assert volume_file_md5sum2 == original_md5sum2


def prepare_auto_upgrade_engine_to_default_version(client): # NOQA
    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 0)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    compatible_img = client.create_engine_image(image=engine_upgrade_image)
    compatible_img_name = compatible_img.name
    ei_status_value = get_engine_image_status_value(client,
                                                    compatible_img_name)
    compatible_img = wait_for_engine_image_state(client,
                                                 compatible_img_name,
                                                 ei_status_value)
    assert compatible_img.refCount == 0
    assert compatible_img.noRefSince != ""

    return default_img, default_img_name, engine_upgrade_image, \
        compatible_img, compatible_img_name


def check_replica_engine(volume, engineimage):

    for replica in volume.replicas:
        if volume["state"] == "attached":
            if volume["robustness"] != "degraded":
                assert replica.running is True

            if replica.running is True:
                assert replica.engineImage == engineimage
                assert replica.currentImage == engineimage
        elif volume["state"] == "detached":
            assert replica.running is False
            assert replica.engineImage == engineimage
            assert replica.currentImage == ""


def test_auto_upgrade_engine_to_default_version(client): # NOQA
    """
    Steps:

    Preparation:
    1. set up a backup store
    2. Deploy a compatible new engine image

    Test auto upgrade to default engine in attached / detached volume:
    1. Create 2 volumes each of 0.5Gb.
    2. Attach 1 volumes vol-1. Write data to it
    3. Upgrade all volumes to the new engine image
    4. Wait until the upgrades are completed (volumes' engine image changed,
       replicas' mode change to RW for attached volumes, reference count of the
       new engine image changed, all engine and replicas' engine image changed)
    5. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 3
    6. Wait until the upgrades are completed (volumes' engine image changed,
       replica mode change to RW for attached volumes, reference count of the
       new engine image changed, all engine and replicas' engine image changed,
       etc ...)
    7. verify the volumes' data
    """
    # Precondition
    default_img, default_img_name, engine_upgrade_image, \
        _, compatible_img_name = \
        prepare_auto_upgrade_engine_to_default_version(client)

    # Test auto upgrade to default engine in attached / detached volume
    volume1 = client.create_volume(name="vol-1", size=str(1 * Gi),
                                   numberOfReplicas=REPLICA_COUNT)
    volume2 = client.create_volume(name="vol-2", size=str(1 * Gi),
                                   numberOfReplicas=REPLICA_COUNT)
    volume1 = common.wait_for_volume_detached(client, volume1.name)
    volume2 = common.wait_for_volume_detached(client, volume2.name)

    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1.name)
    data = write_volume_random_data(volume1)

    volume1.engineUpgrade(image=engine_upgrade_image)
    volume2.engineUpgrade(image=engine_upgrade_image)

    volume1 = wait_for_volume_current_image(client, volume1.name,
                                            engine_upgrade_image)
    volume2 = wait_for_volume_current_image(client, volume2.name,
                                            engine_upgrade_image)

    volume1 = wait_for_volume_replicas_mode(client, volume1.name, "RW")

    wait_for_engine_image_ref_count(client, default_img_name, 0)

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    wait_for_engine_image_ref_count(client, compatible_img_name, 0)

    wait_for_volume_healthy(client, volume1.name)
    check_volume_data(volume1, data)

    volume1 = client.by_id_volume(volume1.name)
    volume2 = client.by_id_volume(volume2.name)
    assert volume1.engineImage == default_img.image
    assert volume2.engineImage == default_img.image
    check_replica_engine(volume1, default_img.image)
    check_replica_engine(volume2, default_img.image)


def test_auto_upgrade_engine_to_default_version_dr_volume(client, set_random_backupstore): # NOQA
    """
    Steps:

    Preparation:
    1. set up a backup store
    2. Deploy a compatible new engine image

    Test auto upgrade engine to default version in DR volume:
    1. Create a backup for vol-1. Create a DR volume from the backup
    2. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 3
    3. Try to upgrade the DR volume engine's image to the new engine image
    4. Verify that the Longhorn API returns error. Upgrade fails.
    5. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 0
    6. Try to upgrade the DR volume engine's image to the new engine image
    7. Wait until the upgrade are completed (volumes' engine image changed,
       replicas' mode change to RW, reference count of the new engine image
       changed, engine and replicas' engine image changed)
    8. Wait for the DR volume to finish restoring
    9. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 3
    10. In a 2-min retry loop, verify that Longhorn doesn't automatically
       upgrade engine image for DR volume.
    """
    # Precondition
    _, default_img_name, engine_upgrade_image, compatible_img, _ = \
        prepare_auto_upgrade_engine_to_default_version(client)

    volume1 = client.create_volume(name="vol-1", size=str(1 * Gi),
                                   numberOfReplicas=REPLICA_COUNT)
    volume1 = common.wait_for_volume_detached(client, volume1.name)
    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1.name)

    write_volume_random_data(volume1)

    _, b, _, _ = create_backup(client, volume1.name)

    common.cleanup_all_volumes(client)

    # Test auto upgrade engine to default version in DR volume
    dr_volume_name = "dr-expand-" + volume1.name
    dr_volume = client.create_volume(name=dr_volume_name, size=SIZE,
                                     numberOfReplicas=3, fromBackup=b.url,
                                     frontend="", standby=True)

    wait_for_backup_restore_completed(client, dr_volume_name, b.name)

    dr_volume = common.wait_for_volume_healthy_no_frontend(client,
                                                           dr_volume_name)
    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    try:
        dr_volume.engineUpgrade(image=engine_upgrade_image)
        raise ("Engine upgrade should fail when \
               'Concurrent Automatic Engine Upgrade Per Node Limit` \
               is greater than 0")
    except Exception as err:
        print(err)

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "0")

    dr_volume.engineUpgrade(image=engine_upgrade_image)
    dr_volume = wait_for_volume_current_image(client, dr_volume.name,
                                              engine_upgrade_image)
    dr_volume = wait_for_volume_replicas_mode(client, dr_volume.name, "RW")

    wait_for_engine_image_ref_count(client, default_img_name, 0)

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    for i in range(RETRY_COUNTS):
        dr_volume = client.by_id_volume(dr_volume.name)
        assert dr_volume.engineImage == compatible_img.image
        time.sleep(RETRY_INTERVAL)

    check_replica_engine(dr_volume, compatible_img.image)


def test_auto_upgrade_engine_to_default_version_expanding_volume(client): # NOQA
    """
    Steps:

    Preparation:
    1. set up a backup store
    2. Deploy a compatible new engine image

    Test auto upgrade engine to default version in expanding volume:
    1. set concurrent-automatic-engine-upgrade-per-node-limit setting to 0
    2. Upgrade vol-1 to the new engine image
    3. Wait until the upgrade are completed (volumes' engine image changed,
       replicas' mode change to RW, reference count of the new engine image
       changed, engine and replicas' engine image changed)
    4. Expand the vol-0 from 1Gb to 5GB
    5. Wait for the vol-0 to start expanding
    6. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 3
    7. While vol-0 is expanding, verify that its engine is not upgraded to
       the default engine image
    8. Wait for the expansion to finish and vol-0 is detached
    9. Verify that Longhorn upgrades vol-0's engine to the default version
    """
    # Precondition
    default_img, default_img_name, engine_upgrade_image, \
        compatible_img, compatible_img_name = \
        prepare_auto_upgrade_engine_to_default_version(client)

    # Test auto upgrade engine to default version in expanding volume
    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "0")

    volume1 = client.create_volume(name="vol-1", size=str(1 * Gi),
                                   numberOfReplicas=REPLICA_COUNT)
    volume1 = common.wait_for_volume_detached(client, volume1.name)
    volume1.engineUpgrade(image=engine_upgrade_image)
    wait_for_engine_image_ref_count(client, default_img_name, 0)
    volume1.expand(size=str(5 * Gi))

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    # check volume is expanding
    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1.name)
        engine = get_volume_engine(volume1)
        assert volume1.engineImage == compatible_img.image

        if engine.size != volume1.size and volume1.state == "detached":
            break

        time.sleep(RETRY_INTERVAL)

    wait_for_engine_image_ref_count(client, compatible_img_name, 0)
    volume1 = client.by_id_volume(volume1.name)
    assert volume1.engineImage == default_img.image


def test_auto_upgrade_engine_to_default_version_degraded_volume(client): # NOQA
    """
    Steps:

    Preparation:
    1. set up a backup store
    2. Deploy a compatible new engine image

    Test auto upgrade engine to default version in degraded volume:
    1. set concurrent-automatic-engine-upgrade-per-node-limit setting to 0
    2. Upgrade vol-1 (an healthy attached volume) to the new engine image
    3. Wait until the upgrade are completed (volumes' engine image changed,
       replicas' mode change to RW, reference count of the new engine image
       changed, engine and replicas' engine image changed)
    4. Increase number of replica count to 4 to make the volume degraded
    5. Set concurrent-automatic-engine-upgrade-per-node-limit setting to 3
    6. In a 2-min retry loop, verify that Longhorn doesn't automatically
       upgrade engine image for vol-1.
    """
    # Precondition
    _, default_img_name, engine_upgrade_image, compatible_img, _ = \
        prepare_auto_upgrade_engine_to_default_version(client)

    # Test auto upgrade engine to default version in degraded volume
    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "0")

    volume1 = client.create_volume(name="vol-1", size=str(1 * Gi),
                                   numberOfReplicas=REPLICA_COUNT)
    volume1 = common.wait_for_volume_detached(client, volume1.name)
    volume1.engineUpgrade(image=engine_upgrade_image)
    volume1 = wait_for_volume_current_image(client, volume1.name,
                                            engine_upgrade_image)
    wait_for_engine_image_ref_count(client, default_img_name, 0)

    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1.name)
    volume1.updateReplicaCount(replicaCount=4)
    volume1 = common.wait_for_volume_degraded(client, volume1.name)

    update_setting(client,
                   SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT,
                   "3")

    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1.name)
        assert volume1.engineImage == compatible_img.image
        time.sleep(RETRY_INTERVAL)

    check_replica_engine(volume1, compatible_img.image)


def test_engine_live_upgrade_while_replica_concurrent_rebuild(client, # NOQA
                                                               volume_name): # NOQA
    """
    Test the ConcurrentReplicaRebuildPerNodeLimit won't affect volume
    live upgrade:
    1. Set `ConcurrentReplicaRebuildPerNodeLimit` to 1.
    2. Create 2 volumes then attach both volumes.
    3. Write a large amount of data into both volumes,
       so that the rebuilding will take a while.
    4. Deploy a compatible engine image and wait for ready.
    5. Make volume 1 and volume 2 state attached and healthy.
    6. Delete one replica for volume 1 to trigger the rebuilding.
    7. Do live upgrade for volume 2. The upgrade should work fine
       even if the rebuilding in volume 1 is still in progress.
    """
    update_setting(client,
                   "concurrent-replica-rebuild-per-node-limit",
                   "1")

    volume1_name = "test-vol-1"  # NOQA
    volume1 = create_and_check_volume(client, volume1_name, size=str(4 * Gi))
    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1_name)

    volume2_name = "test-vol-2"  # NOQA
    volume2 = create_and_check_volume(client, volume2_name, size=str(4 * Gi))
    volume2.attach(hostId=get_self_host_id())
    volume2 = wait_for_volume_healthy(client, volume2_name)

    volume1_endpoint = get_volume_endpoint(volume1)
    volume2_endpoint = get_volume_endpoint(volume2)
    write_volume_dev_random_mb_data(volume1_endpoint,
                                    1, 3500)
    write_volume_dev_random_mb_data(volume2_endpoint,
                                    1, 3500)

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    # Total ei.refCount of the two volumes is
    # 2 volumes + 2 engines + all replicas
    expected_ref_count = 4 + len(volume1.replicas) + len(volume2.replicas)
    default_img = wait_for_engine_image_ref_count(client,
                                                  default_img_name,
                                                  expected_ref_count)
    cli_v = default_img.cliAPIVersion
    cli_minv = default_img.cliAPIMinVersion
    ctl_v = default_img.controllerAPIVersion
    ctl_minv = default_img.controllerAPIMinVersion
    data_v = default_img.dataFormatVersion
    data_minv = default_img.dataFormatMinVersion
    engine_upgrade_image = common.get_upgrade_test_image(cli_v, cli_minv,
                                                         ctl_v, ctl_minv,
                                                         data_v, data_minv)

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img.name
    ei_status_value = get_engine_image_status_value(client, new_img_name)
    new_img = wait_for_engine_image_state(client,
                                          new_img_name,
                                          ei_status_value)
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    volume2 = client.by_id_volume(volume2_name)

    original_engine_image = volume2.engineImage
    assert original_engine_image != engine_upgrade_image

    delete_replica_on_test_node(client, volume1_name)
    wait_for_rebuild_start(client, volume1_name)

    assert volume2.engineImage == original_engine_image
    assert volume2.currentImage == original_engine_image
    volume2 = client.by_id_volume(volume2_name)
    engine = get_volume_engine(volume2)
    assert engine.engineImage == original_engine_image
    assert engine.currentImage == original_engine_image

    volume2.engineUpgrade(image=engine_upgrade_image)

    # In a 2 minutes retry loop:
    # verify that we see the case, volume 2 finished upgrading while volume 1
    # is still rebuilding
    # volume 2 finished upgrading if it meet the condition:
    # *it is healthy
    # *currentImage of volume2 == engine_upgrade_image

    expect_case = False
    # Check rebuild started and engine image deploying
    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1_name)
        try:
            if volume1.rebuildStatus[0].state == "in_progress":
                expect_case = True
                break
            else:
                continue
        except: # NOQA
            pass
        time.sleep(RETRY_INTERVAL)
    assert expect_case is True

    expect_case = False
    # Check volume2 engine upgrade success
    for i in range(RETRY_COUNTS):
        volume2 = client.by_id_volume(volume2_name)
        if volume2.currentImage == engine_upgrade_image and \
                volume2["robustness"] == "healthy" and \
                len(volume2.replicas) == 3:
            expect_case = True
            break
        time.sleep(RETRY_INTERVAL)
    assert expect_case is True

    volume2 = client.by_id_volume(volume2_name)
    engine = get_volume_engine(volume2)
    assert engine.engineImage == engine_upgrade_image
    wait_for_rebuild_complete(client, volume1_name)

    # Total ei.refCount of one volumes is equal to
    # 1 volumes + 1 engine + all replicas
    expected_ref_count = 2 + len(volume1.replicas)
    wait_for_engine_image_ref_count(client,
                                    default_img_name,
                                    expected_ref_count)
    expected_ref_count = 2 + len(volume2.replicas)
    wait_for_engine_image_ref_count(client,
                                    new_img_name,
                                    expected_ref_count)

    for replica in volume2.replicas:
        assert replica.engineImage == engine_upgrade_image
        assert replica.currentImage == engine_upgrade_image
