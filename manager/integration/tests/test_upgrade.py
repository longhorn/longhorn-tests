import os
import pytest
import subprocess
import time

from common import SIZE
from common import volume_name  # NOQA
from common import create_and_check_volume
from common import get_self_host_id
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import wait_for_volume_degraded
from common import wait_for_volume_replica_count
from common import write_volume_random_data
from common import check_volume_data
from common import get_longhorn_api_client
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
from common import generate_random_data
from common import VOLUME_RWTEST_SIZE
from common import write_pod_volume_data
from common import read_volume_data
from common import settings_reset # NOQA
from common import client, core_api # NOQA
from common import SETTING_DISABLE_REVISION_COUNTER
from common import update_setting
from common import delete_replica_on_test_node


@pytest.fixture
def upgrade_longhorn_repo_url(request):
    return request.config.getoption("--upgrade-lh-repo-url")


@pytest.fixture
def upgrade_longhorn_repo_branch(request):
    return request.config.getoption("--upgrade-lh-repo-branch")


@pytest.fixture
def upgrade_longhorn_manager_image(request):
    return request.config.getoption("--upgrade-lh-manager-image")


@pytest.fixture
def upgrade_longhorn_engine_image(request):
    return request.config.getoption("--upgrade-lh-engine-image")


@pytest.fixture
def upgrade_longhorn_instance_manager_image(request):
    return request.config.getoption("--upgrade-lh-instance-manager-image")


@pytest.fixture
def upgrade_longhorn_share_manager_image(request):
    return request.config.getoption("--upgrade-lh-share-manager-image")


@pytest.fixture
def upgrade_longhorn_backing_image_manager_image(request):
    return request.config.getoption("--upgrade-lh-backing-image-manager-image")


def get_longhorn_upgrade_type():
    return [os.environ.get('LONGHORN_UPGRADE_TYPE', '')]


def create_volume_and_wrte_date(client, volume_name):  # NOQA
    """
    1. Create and attach a volume
    2. Write the data to volume
    """
    # Step 1
    volume = create_and_check_volume(client,
                                     volume_name,
                                     size=SIZE)
    volume = volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    # Step 2
    volume_data = write_volume_random_data(volume)

    return volume, volume_data


@pytest.fixture(params=get_longhorn_upgrade_type())
def longhorn_upgrade_type():
    # add parameter "from_stable" or "from_transient" to test_upgrade test case
    # to distinguish them in the junit report.
    pass


def longhorn_upgrade(longhorn_repo_url,
                     longhorn_repo_branch,
                     longhorn_manager_image,
                     longhorn_engine_image,
                     longhorn_instance_manager_image,
                     longhorn_share_manager_image,
                     longhorn_backing_image_manager_image):

    command = "../scripts/upgrade-longhorn.sh"
    process = subprocess.Popen([command,
                                longhorn_repo_url,
                                longhorn_repo_branch,
                                longhorn_manager_image,
                                longhorn_engine_image,
                                longhorn_instance_manager_image,
                                longhorn_share_manager_image,
                                longhorn_backing_image_manager_image],
                               shell=False)
    process.wait()
    if process.returncode == 0:
        longhorn_upgraded = True

    else:
        longhorn_upgraded = False

    return longhorn_upgraded


@pytest.mark.upgrade  # NOQA
def test_upgrade(longhorn_upgrade_type,
                 upgrade_longhorn_repo_url,
                 upgrade_longhorn_repo_branch,
                 upgrade_longhorn_manager_image,
                 upgrade_longhorn_engine_image,
                 upgrade_longhorn_instance_manager_image,
                 upgrade_longhorn_share_manager_image,
                 upgrade_longhorn_backing_image_manager_image,
                 client, core_api, volume_name, csi_pv, # NOQA
                 pvc, pod_make, statefulset, storage_class): # NOQA
    """
    Test Longhorn upgrade

    TODO
    The test will cover both volume has revision counter enabled and
    disabled cases.

    Prerequisite:
      - Disable Auto Salvage Setting

    1. Find the upgrade image tag
    2. Create a volume, generate and write data into the volume.
        1. Create vol_revision_enabled with revision counter enabled case.
        2. Create vol_revision_disabled with revision counter disabled case.
        3. Create vol_rebuild for replica rebuilding after system upgrade
           & engine live upgrade
    3. Create a Pod using a volume, generate and write data
    4. Create a StatefulSet with 2 replicas
       generate and write data to their volumes
    5. Keep all volumes attached
    6. Upgrade Longhorn system.
    7. Check Pod and StatefulSet didn't restart after system upgrade
    8. Check all volumes data
    9. Write all volumes data after system upgrade
    10. Check data written to all volumes after system upgrade
    11. Detach the vol_revision_enabled & vol_revision_disabled,
        and Delete Pod, and StatefulSet to detach theirvolumes
    12. Upgrade all volumes engine images
    13. Attach the volume, and recreate Pod, and StatefulSet
    14. Check All volumes data
    15. Delete one replica for vol_rebuild to trigger the rebuilding
    16. Verify the vol_rebuild is still healthy
    """
    longhorn_repo_url = upgrade_longhorn_repo_url
    longhorn_repo_branch = upgrade_longhorn_repo_branch
    longhorn_manager_image = upgrade_longhorn_manager_image
    longhorn_engine_image = upgrade_longhorn_engine_image
    longhorn_instance_manager_image = upgrade_longhorn_instance_manager_image
    longhorn_share_manager_image = upgrade_longhorn_share_manager_image
    longhorn_backing_image_manager_image = \
        upgrade_longhorn_backing_image_manager_image

    host_id = get_self_host_id()
    pod_data_path = "/data/test"

    # Disable Auto Salvage Setting
    update_setting(client, SETTING_AUTO_SALVAGE, "false")

    # 2-1 Create vol_revision_enabled with revision counter enabled
    # attached to a node
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "true")
    vol_revision_enabled_name = 'vol-revision-enabled'
    vol_revision_enabled, vol_revision_enabled_data_before_sys_upgrade = \
        create_volume_and_wrte_date(client, vol_revision_enabled_name)

    # 2-2 Create vol_revision_disabled with revision counter disable
    # attached to a node
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "false")
    vol_revision_disabled_name = 'vol-revision-disabled'
    vol_revision_disabled, vol_revision_disabled_data_before_sys_upgrade = \
        create_volume_and_wrte_date(client, vol_revision_disabled_name)

    # 2-3 Create vol_rebuild for replica rebuilding after system upgrade
    # & engine live upgrade
    vol_rebuild_name = 'vol-rebuild'
    vol_rebuild, vol_rebuild_data_before_sys_upgrade = \
        create_volume_and_wrte_date(client, vol_rebuild_name)

    # Create Volume used by Pod
    pod_volume_name = 'lh-vol-pod-test'
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
    # upgrade Longhorn manager
    assert longhorn_upgrade(longhorn_repo_url,
                            longhorn_repo_branch,
                            longhorn_manager_image,
                            longhorn_engine_image,
                            longhorn_instance_manager_image,
                            longhorn_share_manager_image,
                            longhorn_backing_image_manager_image)

    client = get_longhorn_api_client()

    # wait for 1 minute before checking pod restarts
    time.sleep(60)

    # Check Pod and StatefulSet didn't restart after upgrade
    pod = core_api.read_namespaced_pod(name=pod_name,
                                       namespace='default')
    assert pod.status.container_statuses[0].restart_count == 0

    for sspod_info in statefulset_pod_info:
        sspod = core_api.read_namespaced_pod(name=sspod_info['pod_name'],
                                             namespace='default')
        assert \
            sspod.status.container_statuses[0].restart_count == 0

    # Check all volumes data after system upgrade
    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_before_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_before_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_before_sys_upgrade)

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum

    # Write data to all volumes after system upgrade
    for sspod_info in statefulset_pod_info:
        sspod_info['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api,
                              sspod_info['pod_name'],
                              sspod_info['data'])

    vol_revision_enabled_data_after_sys_upgrade = \
        write_volume_random_data(vol_revision_enabled)
    vol_revision_disabled_data_after_sys_upgrade = \
        write_volume_random_data(vol_revision_disabled)
    vol_rebuild_data_after_sys_upgrade = \
        write_volume_random_data(vol_rebuild)

    # Check data written to all volumes
    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_after_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_after_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_after_sys_upgrade)

    # Detach the vol_revision_enabled & vol_revision_disabled,
    # and Delete Pod, and StatefulSet to detach theirvolumes

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

    volumes = client.list_volume()
    for v in volumes:
        if v.name != vol_rebuild_name:
            volume = client.by_id_volume(v.name)
            volume.detach(hostId="")
            wait_for_volume_detached(client, v.name)

    engineimages = client.list_engine_image()
    for ei in engineimages:
        if ei.image == longhorn_engine_image:
            new_ei = ei

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

    for v in volumes:
        if v.name == vol_revision_enabled_name or \
                v.name == vol_revision_disabled_name:
            volume = client.by_id_volume(v.name)
            volume.attach(hostId=host_id)
            wait_for_volume_healthy(client, v.name)

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum

    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_after_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_after_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_after_sys_upgrade)

    # Delete one healthy replica for vol_rebuild to trigger the rebuilding
    delete_replica_on_test_node(client, vol_rebuild_name)
    # Make sure vol_rebuild replica is deleted
    replica_count = 2
    vol_rebuild = wait_for_volume_replica_count(client, vol_rebuild_name,
                                                replica_count)
    # vol_rebuild will become degraded and start replica rebuilding
    # Wait for replica rebuilding to complete
    # Verify the vol_rebuild is still healthy
    vol_rebuild = wait_for_volume_degraded(client, vol_rebuild_name)
    assert vol_rebuild.robustness == "degraded"
    vol_rebuild = wait_for_volume_healthy(client, vol_rebuild_name)
    assert vol_rebuild.robustness == "healthy"
    assert len(vol_rebuild.replicas) == 3


# Need add this test case into test_upgrade()
# https://github.com/longhorn/longhorn/issues/4726
@pytest.mark.skip(reason="TODO")  # NOQA
def test_upgrade_with_auto_upgrade_latest_engine_enabled():
    """
    1. Deploy Longhorn stable version
    2. Set Concurrent Automatic Engine Upgrade Per Node Limit to > 0
    3. Create a volume and attach it
    4. Deploy longhornio/longhorn-engine:master-head and wait for it
       to be deployed. This step is to make sure to expose the race condition
       that Longhorn tries auto engine upgrade while the new default IM is
       still starting
    5. Upgrade Longhorn to master-head
    6. Observe volume engine image upgrade success.
    """
