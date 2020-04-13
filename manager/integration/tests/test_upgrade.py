import pytest
import subprocess

from common import SIZE
from common import volume_name  # NOQA
from common import create_and_check_volume
from common import get_self_host_id
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import write_volume_random_data
from common import check_volume_data
from common import get_longhorn_api_client


@pytest.fixture
def upgrade_image_tag(request):
    return request.config.getoption("--upgrade-image-tag")


def longhorn_upgrade(image_tag):
    command = "../scripts/upgrade-longhorn.sh"
    process = subprocess.Popen([command, image_tag], shell=False)
    process.wait()
    if process.returncode == 0:
        longhorn_upgraded = True

    else:
        longhorn_upgraded = False

    return longhorn_upgraded


@pytest.mark.upgrade
def test_upgrade(upgrade_image_tag, volume_name):  # NOQA
    """
    Test Longhorn upgrade

    1. Find the upgrade image tag
    2. Create a volume, generate and write `data` into the volume.
    3. Keep the volume attached, then upgrade Longhorn system.
    4. Detach the volume.
    5. Upgrade the volume to the updated engine image.
    6. Attach the volume and verify `data`
    """
    new_ei_name = "longhornio/longhorn-engine:" + upgrade_image_tag

    client = get_longhorn_api_client()

    host_id = get_self_host_id()

    volume = create_and_check_volume(client,
                                     volume_name,
                                     size=SIZE)

    volume.attach(hostId=host_id)

    volume = wait_for_volume_healthy(client, volume_name)

    data = write_volume_random_data(volume)

    assert longhorn_upgrade(upgrade_image_tag)

    client = get_longhorn_api_client()

    volume = client.by_id_volume(volume_name)

    volume.detach()

    volume = wait_for_volume_detached(client, volume_name)

    engineimages = client.list_engine_image()

    for ei in engineimages:
        if ei.image == new_ei_name:
            new_ei = ei

    volume.engineUpgrade(image=new_ei.image)

    volume.attach(hostId=host_id)

    volume = wait_for_volume_healthy(client, volume_name)

    check_volume_data(volume, data)
