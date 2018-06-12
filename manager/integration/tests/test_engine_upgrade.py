import pytest

import common
from common import clients, volume_name  # NOQA
from common import SIZE
from common import wait_for_volume_state, wait_for_volume_delete
from common import wait_for_volume_engine_image, wait_for_engine_image_state

REPLICA_COUNT = 2


def test_engine_image(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    images = client.list_engine_image()
    assert len(images) == 1
    assert images[0]["default"]
    assert images[0]["state"] == "ready"
    assert images[0]["refCount"] == 0
    assert images[0]["cliVersion"] != 0
    assert images[0]["cliMinVersion"] != 0
    assert images[0]["controllerVersion"] != 0
    assert images[0]["controllerMinVersion"] != 0
    assert images[0]["dataFormatVersion"] != 0
    assert images[0]["dataFormatMinVersion"] != 0
    assert images[0]["gitCommit"] != ""
    assert images[0]["buildDate"] != ""
    default_img = images[0]["image"]

    # delete default image is not allowed
    with pytest.raises(Exception) as e:
        client.delete(images[0])
    assert "the default engine image" in str(e.value)

    # duplicate images
    with pytest.raises(Exception) as e:
        client.create_engine_image(image=default_img)

    engine_upgrade_image = common.get_engine_upgrade_image(client)
    assert engine_upgrade_image != ""

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img["name"]
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")
    assert not new_img["default"]
    assert new_img["state"] == "ready"
    assert new_img["refCount"] == 0
    assert new_img["cliVersion"] != 0
    assert new_img["cliMinVersion"] != 0
    assert new_img["controllerVersion"] != 0
    assert new_img["controllerMinVersion"] != 0
    assert new_img["dataFormatVersion"] != 0
    assert new_img["dataFormatMinVersion"] != 0
    assert new_img["gitCommit"] != ""
    assert new_img["buildDate"] != ""

    client.delete(new_img)


def test_engine_offline_upgrade(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    engine_upgrade_image = common.get_engine_upgrade_image(client)
    assert engine_upgrade_image != ""

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img["name"]
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=REPLICA_COUNT)
    volume = wait_for_volume_state(client, volume_name, "detached")

    assert volume["name"] == volume_name

    original_engine_image = volume["engineImage"]
    assert original_engine_image != engine_upgrade_image

    volume.engineUpgrade(image=engine_upgrade_image)
    volume = wait_for_volume_engine_image(client, volume_name,
                                          engine_upgrade_image)

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    assert volume["controller"]["engineImage"] == engine_upgrade_image
    for replica in volume["replicas"]:
        assert replica["engineImage"] == engine_upgrade_image

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    volume.engineUpgrade(image=original_engine_image)
    volume = wait_for_volume_engine_image(client, volume_name,
                                          original_engine_image)

    assert volume["engineImage"] == original_engine_image

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    assert volume["controller"]["engineImage"] == original_engine_image
    for replica in volume["replicas"]:
        assert replica["engineImage"] == original_engine_image

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)


def test_engine_live_upgrade(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    engine_upgrade_image = common.get_engine_upgrade_image(client)
    assert engine_upgrade_image != ""

    new_img = client.create_engine_image(image=engine_upgrade_image)
    new_img_name = new_img["name"]
    new_img = wait_for_engine_image_state(client, new_img_name, "ready")

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")

    assert volume["name"] == volume_name

    original_engine_image = volume["engineImage"]
    assert original_engine_image != engine_upgrade_image

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume.engineUpgrade(image=engine_upgrade_image)
    volume = wait_for_volume_engine_image(client, volume_name,
                                          engine_upgrade_image)

    assert volume["controller"]["engineImage"] == engine_upgrade_image
    count = 0
    # old replica may be in deletion process
    for replica in volume["replicas"]:
        if replica["engineImage"] == engine_upgrade_image:
            count += 1
    assert count == REPLICA_COUNT

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert len(volume["replicas"]) == REPLICA_COUNT

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume.engineUpgrade(image=original_engine_image)
    volume = wait_for_volume_engine_image(client, volume_name,
                                          original_engine_image)

    assert volume["engineImage"] == original_engine_image

    assert volume["controller"]["engineImage"] == original_engine_image
    count = 0
    # old replica may be in deletion process
    for replica in volume["replicas"]:
        if replica["engineImage"] == original_engine_image:
            count += 1
    assert count == REPLICA_COUNT

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert len(volume["replicas"]) == REPLICA_COUNT

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    client.delete(new_img)


def test_engine_image_incompatible(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    images = client.list_engine_image()
    assert len(images) == 1
    assert images[0]["default"]
    assert images[0]["state"] == "ready"

    cli_v = images[0]["cliVersion"]
    # cli_minv = images[0]["cliMinVersion"]
    ctl_v = images[0]["controllerVersion"]
    ctl_minv = images[0]["controllerMinVersion"]
    data_v = images[0]["dataFormatVersion"]
    data_minv = images[0]["dataFormatMinVersion"]

    fail_cli_v_image = common.get_compatibility_test_image(
            cli_v - 1, cli_v - 1,
            ctl_v, ctl_minv,
            data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_v_image)
    img_name = img["name"]
    img = wait_for_engine_image_state(client, img_name, "incompatible")
    assert img["state"] == "incompatible"
    assert img["cliVersion"] == cli_v - 1
    assert img["cliMinVersion"] == cli_v - 1
    client.delete(img)

    fail_cli_minv_image = common.get_compatibility_test_image(
            cli_v + 1, cli_v + 1,
            ctl_v, ctl_minv,
            data_v, data_minv)
    img = client.create_engine_image(image=fail_cli_minv_image)
    img_name = img["name"]
    img = wait_for_engine_image_state(client, img_name, "incompatible")
    assert img["state"] == "incompatible"
    assert img["cliVersion"] == cli_v + 1
    assert img["cliMinVersion"] == cli_v + 1
    client.delete(img)
