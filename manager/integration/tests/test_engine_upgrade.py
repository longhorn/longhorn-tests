import pytest

import common
from common import client, core_api, volume_name  # NOQA
from common import SIZE
from common import check_volume_data, get_self_host_id
from common import wait_for_volume_current_image, wait_for_volume_delete
from common import wait_for_engine_image_deletion
from common import wait_for_engine_image_ref_count, wait_for_engine_image_state
from common import get_volume_engine, write_volume_random_data
from common import wait_for_volume_replicas_mode

REPLICA_COUNT = 2
ENGINE_IMAGE_TEST_REPEAT_COUNT = 5


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

    images = client.list_engine_image()
    assert len(images) == 1
    assert images[0].default
    assert images[0].state == "ready"
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
    for i in range(ENGINE_IMAGE_TEST_REPEAT_COUNT):
        new_img = client.create_engine_image(image=engine_upgrade_image)
        new_img_name = new_img.name
        new_img = wait_for_engine_image_state(client, new_img_name, "ready")
        assert not new_img.default
        assert new_img.state == "ready"
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


def engine_offline_upgrade_test(client, core_api, volume_name, base_image=""):  # NOQA
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
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT,
                                  baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)
    default_img = wait_for_engine_image_ref_count(client, default_img_name, 1)

    original_engine_image = default_img.image

    assert volume.name == volume_name
    assert volume.engineImage == original_engine_image
    assert volume.currentImage == original_engine_image
    assert volume.baseImage == base_image

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
    new_img = wait_for_engine_image_ref_count(client, new_img_name, 1)

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

    default_img = wait_for_engine_image_ref_count(client, default_img_name, 1)
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


def engine_live_upgrade_test(client, core_api, volume_name, base_image=""):  # NOQA
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
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2, baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)
    wait_for_engine_image_ref_count(client, default_img_name, 1)

    assert volume.name == volume_name
    assert volume.baseImage == base_image

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
    assert engine.endpoint != ""

    wait_for_engine_image_ref_count(client, default_img_name, 0)
    wait_for_engine_image_ref_count(client, new_img_name, 1)

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
    assert engine.endpoint != ""
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
    assert engine.endpoint != ""

    wait_for_engine_image_ref_count(client, default_img_name, 1)
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
    assert images[0].default
    assert images[0].state == "ready"

    cli_v = images[0].cliAPIVersion
    # cli_minv = images[0].cliAPIMinVersion
    ctl_v = images[0].controllerAPIVersion
    ctl_minv = images[0].controllerAPIMinVersion
    data_v = images[0].dataFormatVersion
    data_minv = images[0].dataFormatMinVersion

    fail_cli_v_image = common.get_compatibility_test_image(
            cli_v - 1, cli_v - 1,
            ctl_v, ctl_minv,
            data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_v_image)
    img_name = img.name
    img = wait_for_engine_image_state(client, img_name, "incompatible")
    assert img.state == "incompatible"
    assert img.cliAPIVersion == cli_v - 1
    assert img.cliAPIMinVersion == cli_v - 1
    client.delete(img)
    wait_for_engine_image_deletion(client, core_api, img.name)

    fail_cli_minv_image = common.get_compatibility_test_image(
            cli_v + 1, cli_v + 1,
            ctl_v, ctl_minv,
            data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_minv_image)
    img_name = img.name
    img = wait_for_engine_image_state(client, img_name, "incompatible")
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


def engine_live_upgrade_rollback_test(client, core_api, volume_name, base_image=""):  # NOQA
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
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")
    assert new_img.refCount == 0
    assert new_img.noRefSince != ""

    default_img = common.get_default_engine_image(client)
    default_img_name = default_img.name

    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2, baseImage=base_image)
    volume = common.wait_for_volume_detached(client, volume_name)
    wait_for_engine_image_ref_count(client, default_img_name, 1)
    assert volume.baseImage == base_image

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
    assert engine.endpoint != ""
    for replica in volume.replicas:
        assert replica.engineImage == original_engine_image
        assert replica.currentImage == original_engine_image

    check_volume_data(volume, data)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)
    wait_for_engine_image_deletion(client, core_api, new_img.name)
