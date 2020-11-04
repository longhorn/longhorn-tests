import pytest
import subprocess
import time

from common import SIZE
from common import volume_name  # NOQA
from common import create_and_check_volume
from common import get_self_host_id
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import write_volume_random_data
from common import check_volume_data
from common import get_longhorn_api_client
from common import get_core_api_client
from common import prepare_pod_with_data_in_mb
from common import update_statefulset_manifests
from common import create_storage_class
from common import create_and_wait_statefulset
from common import get_statefulset_pod_info
from common import get_apps_api_client
from common import delete_and_wait_pod
from common import wait_statefulset
from common import create_pvc_spec
from common import create_and_wait_pod
from common import get_pod_data_md5sum
from common import pod_make, csi_pv, pvc # NOQA
from common import statefulset # NOQA
from common import storage_class # NOQA
from common import SETTING_AUTO_SALVAGE
from common import generate_volume_name
from common import generate_random_data
from common import VOLUME_RWTEST_SIZE
from common import write_pod_volume_data
from common import read_volume_data
from common import settings_reset # NOQA


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
def test_upgrade(upgrade_image_tag, settings_reset, volume_name, csi_pv, pvc, pod_make, statefulset, storage_class): # NOQA
    """
    Test Longhorn upgrade

    TODO
    The test will cover both volume has revision counter enabled and
    disabled cases.

    Prerequisite:
      - Disable Auto Salvage Setting

    1. Find the upgrade image tag
    2. Create a volume, generate and write data into the volume.
        1. Create a volume with revision counter enabled case.
        2. Create a volume with revision counter disabled case.
    3. Create a Pod using a volume, generate and write data
    4. Create a StatefulSet with 2 replicas,
       generate and write data to their volumes
    5. Keep all volumes attached
    6. Upgrade Longhorn system.
    7. Check Pod and StatefulSet didn't restart after upgrade
    8. Check All volumes data
    9. Write data to StatefulSet pods, and Attached volume
    10. Check data written to StatefulSet pods, and attached volume.
    11. Detach the volume, and Delete Pod, and
        StatefulSet to detach theirvolumes
    12. Upgrade all volumes engine images.
    13. Attach the volume, and recreate Pod, and StatefulSet
    14. Check All volumes data
    """
    new_ei_name = "longhornio/longhorn-engine:" + upgrade_image_tag

    client = get_longhorn_api_client()
    core_api = get_core_api_client()
    host_id = get_self_host_id()
    pod_data_path = "/data/test"

    pod_volume_name = generate_volume_name()

    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="false")

    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "false"

    # Create Volume attached to a node.
    volume1 = create_and_check_volume(client,
                                      volume_name,
                                      size=SIZE)
    volume1.attach(hostId=host_id)
    volume1 = wait_for_volume_healthy(client, volume_name)
    volume1_data = write_volume_random_data(volume1)

    # Create Volume used by Pod
    pod_name, pv_name, pvc_name, pod_md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make, pod_volume_name,
                                    data_path=pod_data_path,
                                    add_liveness_probe=False)

    # Create multiple volumes used by StatefulSet
    statefulset_name = 'statefulset-upgrade-test'
    update_statefulset_manifests(statefulset,
                                 storage_class,
                                 statefulset_name)
    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)
    statefulset_pod_info = get_statefulset_pod_info(core_api, statefulset)

    for sspod_info in statefulset_pod_info:
        sspod_info['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api,
                              sspod_info['pod_name'],
                              sspod_info['data'])

    # upgrade Longhorn
    assert longhorn_upgrade(upgrade_image_tag)

    client = get_longhorn_api_client()

    # wait for 1 minute before checking pod restarts
    time.sleep(60)

    pod = core_api.read_namespaced_pod(name=pod_name,
                                       namespace='default')
    assert pod.status.container_statuses[0].restart_count == 0

    for sspod_info in statefulset_pod_info:
        sspod = core_api.read_namespaced_pod(name=sspod_info['pod_name'],
                                             namespace='default')
        assert \
            sspod.status.container_statuses[0].restart_count == 0

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum

    check_volume_data(volume1, volume1_data)

    for sspod_info in statefulset_pod_info:
        sspod_info['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api,
                              sspod_info['pod_name'],
                              sspod_info['data'])

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    volume1 = client.by_id_volume(volume_name)
    volume1_data = write_volume_random_data(volume1)
    check_volume_data(volume1, volume1_data)

    statefulset['spec']['replicas'] = replicas = 0
    apps_api = get_apps_api_client()

    apps_api.patch_namespaced_stateful_set(
        name=statefulset_name,
        namespace='default',
        body={
            'spec': {
                'replicas': replicas
            }
        })

    delete_and_wait_pod(core_api, pod_name)

    volume = client.by_id_volume(volume_name)
    volume.detach()

    volumes = client.list_volume()

    for v in volumes:
        wait_for_volume_detached(client, v.name)

    engineimages = client.list_engine_image()

    for ei in engineimages:
        if ei.image == new_ei_name:
            new_ei = ei

    volumes = client.list_volume()

    for v in volumes:
        volume = client.by_id_volume(v.name)
        volume.engineUpgrade(image=new_ei.image)

    statefulset['spec']['replicas'] = replicas = 2
    apps_api = get_apps_api_client()

    apps_api.patch_namespaced_stateful_set(
        name=statefulset_name,
        namespace='default',
        body={
            'spec': {
                'replicas': replicas
            }
        })

    wait_statefulset(statefulset)

    pod = pod_make(name=pod_name)
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    volume1 = client.by_id_volume(volume_name)
    volume1.attach(hostId=host_id)
    volume1 = wait_for_volume_healthy(client, volume_name)

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum

    check_volume_data(volume1, volume1_data)
