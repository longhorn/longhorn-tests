import pytest

from common import clients, volume_name  # NOQA
from common import SIZE
from common import wait_for_volume_state, wait_for_volume_delete
from common import wait_for_volume_engine_image

from conftest import engine_upgrade_image  # NOQA

@pytest.mark.engine_upgrade  # NOQA
def test_engine_upgrade_offline(clients, volume_name,   # NOQA
                                engine_upgrade_image):  # NOQA
    assert engine_upgrade_image != ""

    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
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
