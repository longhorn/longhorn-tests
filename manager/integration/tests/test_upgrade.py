import os
import pytest
import subprocess
import time

from common import create_volume_and_write_data
from common import volume_name  # NOQA
from common import get_self_host_id
from common import wait_for_volume_creation
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
from common import statefulset, rwx_statefulset # NOQA
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
from common import get_volume_engine
from common import create_backup
from common import BACKUP_BLOCK_SIZE, DEFAULT_VOLUME_SIZE, Gi
from common import create_backing_image_with_matching_url
from common import BACKING_IMAGE_NAME, BACKING_IMAGE_QCOW2_URL
from common import create_recurring_jobs, check_recurring_jobs
from common import create_and_check_volume
from common import system_backup_wait_for_state
from common import create_support_bundle
from common import wait_for_support_bundle_state
from common import get_backupstores
from common import monitor_restore_progress
from common import wait_for_volume_recurring_job_update
from common import get_volume_name
from common import system_backup_feature_supported
from common import system_backups_cleanup
from test_orphan import create_orphaned_directories_on_host
from test_orphan import delete_orphans
from backupstore import set_backupstore_s3
from backupstore import set_backupstore_nfs, mount_nfs_backupstore


@pytest.fixture
def longhorn_install_method(request):
    return request.config.getoption("--lh-install-method")


@pytest.fixture
def rancher_hostname(request):
    return request.config.getoption("--rancher-hostname")


@pytest.fixture
def rancher_access_key(request):
    return request.config.getoption("--rancher-access-key")


@pytest.fixture
def rancher_secret_key(request):
    return request.config.getoption("--rancher-secret-key")


@pytest.fixture
def rancher_chart_install_version(request):
    return request.config.getoption("--rancher-chart-install-version")


@pytest.fixture
def longhorn_repo(request):
    return request.config.getoption("--longhorn-repo")


@pytest.fixture
def flux_helm_chart_url(request):
    return request.config.getoption("--flux-helm-chart-url")


@pytest.fixture
def flux_helm_chart_version(request):
    return request.config.getoption("--flux-helm-chart-version")


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


@pytest.fixture(params=get_longhorn_upgrade_type())
def longhorn_upgrade_type():
    # add parameter "from_stable" or "from_transient" to test_upgrade test case
    # to distinguish them in the junit report.
    pass


def longhorn_upgrade(longhorn_install_method,
                     rancher_hostname,
                     rancher_access_key,
                     rancher_secret_key,
                     rancher_chart_install_version,
                     longhorn_repo,
                     flux_helm_chart_url,
                     flux_helm_chart_version,
                     longhorn_repo_url,
                     longhorn_repo_branch,
                     longhorn_manager_image,
                     longhorn_engine_image,
                     longhorn_instance_manager_image,
                     longhorn_share_manager_image,
                     longhorn_backing_image_manager_image):

    if longhorn_install_method == "manifest":
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
    elif longhorn_install_method == "helm":
        command = "./pipelines/helm/scripts/upgrade-longhorn.sh"
        process = subprocess.Popen([command,
                                    longhorn_repo_url,
                                    longhorn_repo_branch,
                                    longhorn_manager_image,
                                    longhorn_engine_image,
                                    longhorn_instance_manager_image,
                                    longhorn_share_manager_image,
                                    longhorn_backing_image_manager_image],
                                   shell=False)
    elif longhorn_install_method == "rancher":
        command = "./pipelines/rancher/scripts/upgrade-longhorn.sh"
        process = subprocess.Popen([command,
                                    rancher_hostname,
                                    rancher_access_key,
                                    rancher_secret_key,
                                    rancher_chart_install_version,
                                    longhorn_repo],
                                   shell=False)
    elif longhorn_install_method == "flux":
        command = "./pipelines/flux/scripts/upgrade-longhorn.sh"
        process = subprocess.Popen([command,
                                    flux_helm_chart_url,
                                    flux_helm_chart_version],
                                   shell=False)
    elif longhorn_install_method == "argocd":
        command = "./pipelines/argocd/scripts/upgrade-longhorn.sh"
        process = subprocess.Popen([command,
                                    longhorn_repo_url,
                                    longhorn_repo_branch],
                                   shell=False)

    process.wait()
    if process.returncode == 0:
        longhorn_upgraded = True

    else:
        longhorn_upgraded = False

    return longhorn_upgraded


def test_upgrade(longhorn_upgrade_type,
                 longhorn_install_method,
                 rancher_hostname,
                 rancher_access_key,
                 rancher_secret_key,
                 rancher_chart_install_version,
                 longhorn_repo,
                 flux_helm_chart_url,
                 flux_helm_chart_version,
                 upgrade_longhorn_repo_url,
                 upgrade_longhorn_repo_branch,
                 upgrade_longhorn_manager_image,
                 upgrade_longhorn_engine_image,
                 upgrade_longhorn_instance_manager_image,
                 upgrade_longhorn_share_manager_image,
                 upgrade_longhorn_backing_image_manager_image,
                 client, core_api, volume_name, csi_pv, # NOQA
                 pvc, pod_make, statefulset, rwx_statefulset, storage_class): # NOQA
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
    6. Create custom resources
    7. Upgrade Longhorn system.
    8. Check Pod and StatefulSet didn't restart after system upgrade
    9. Check all volumes data
    10. Write all volumes data after system upgrade
    11. Check data written to all volumes after system upgrade
    12. Detach the vol_revision_enabled & vol_revision_disabled,
        and Delete Pod, and StatefulSet to detach theirvolumes
    13. Upgrade all volumes engine images
    14. Attach the volume, and recreate Pod, and StatefulSet
    15. Verify the volume's engine image has been upgraded
    16. Check All volumes data
    17. Delete one replica for vol_rebuild to trigger the rebuilding
    18. Verify the vol_rebuild is still healthy
    """
    longhorn_install_method = longhorn_install_method
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
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "false")
    vol_revision_enabled_name = 'vol-revision-enabled'
    vol_revision_enabled, vol_revision_enabled_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_revision_enabled_name)

    # 2-2 Create vol_revision_disabled with revision counter disable
    # attached to a node
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "true")
    vol_revision_disabled_name = 'vol-revision-disabled'
    vol_revision_disabled, vol_revision_disabled_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_revision_disabled_name)

    # 2-3 Create vol_rebuild for replica rebuilding after system upgrade
    # & engine live upgrade
    vol_rebuild_name = 'vol-rebuild'
    vol_rebuild, vol_rebuild_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_rebuild_name)

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

    # create custom resources
    # orphan
    create_orphaned_directories_on_host(
        client.by_id_volume(pod_volume_name),
        ["/var/lib/longhorn"],
        1)
    # snapshot and backup
    backup_stores = get_backupstores()
    if backup_stores[0] == "s3":
        set_backupstore_s3(client)
    elif backup_stores[0] == "nfs":
        set_backupstore_nfs(client)
        mount_nfs_backupstore(client)
    backup_vol_name = "backup-vol"
    backup_vol = create_and_check_volume(
        client,
        backup_vol_name,
        2,
        str(DEFAULT_VOLUME_SIZE * Gi))
    backup_vol.attach(hostId=host_id)
    backup_vol = wait_for_volume_healthy(client, backup_vol_name)
    data0 = {'pos': 0, 'len': BACKUP_BLOCK_SIZE,
             'content': generate_random_data(BACKUP_BLOCK_SIZE)}
    _, backup, _, _ = create_backup(client, backup_vol_name, data0)
    # system backup
    if system_backup_feature_supported(client):
        system_backup_name = "test-system-backup"
        client.create_system_backup(Name=system_backup_name)
        system_backup_wait_for_state("Ready", system_backup_name, client)
    # support bundle
    resp = create_support_bundle(client)
    node_id = resp['id']
    name = resp['name']
    wait_for_support_bundle_state("ReadyForDownload", node_id, name, client)
    # backing image
    create_backing_image_with_matching_url(
        client,
        BACKING_IMAGE_NAME,
        BACKING_IMAGE_QCOW2_URL)
    # recurring job
    job_name = "snapshot1"
    recurring_jobs = {
        job_name: {
            "task": "snapshot",
            "groups": [],
            "cron": "* * * * *",
            "retain": 2,
            "concurrency": 1,
            "labels": {},
        }
    }
    create_recurring_jobs(client, recurring_jobs)
    check_recurring_jobs(client, recurring_jobs)
    backup_vol.recurringJobAdd(name=job_name, isGroup=False)
    wait_for_volume_recurring_job_update(backup_vol,
                                         jobs=[job_name],
                                         groups=["default"])
    # share manager
    rwx_statefulset_name = rwx_statefulset['metadata']['name']
    create_and_wait_statefulset(rwx_statefulset)
    rwx_statefulset_pod_name = rwx_statefulset_name + '-0'
    rwx_pvc_name = \
        rwx_statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name']\
        + '-' + rwx_statefulset_name + '-0'
    rwx_pv_name = get_volume_name(core_api, rwx_pvc_name)
    rwx_test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, rwx_statefulset_pod_name,
                          rwx_test_data, filename='test1')


    input("Press Enter to continue...")




    # upgrade Longhorn manager
    assert longhorn_upgrade(longhorn_install_method,
                            rancher_hostname,
                            rancher_access_key,
                            rancher_secret_key,
                            rancher_chart_install_version,
                            longhorn_repo,
                            flux_helm_chart_url,
                            flux_helm_chart_version,
                            longhorn_repo_url,
                            longhorn_repo_branch,
                            longhorn_manager_image,
                            longhorn_engine_image,
                            longhorn_instance_manager_image,
                            longhorn_share_manager_image,
                            longhorn_backing_image_manager_image)

    client = get_longhorn_api_client()

    # wait for 1 minute before checking pod restarts
    time.sleep(60)

    # restore backup after upgrade
    restore_vol_name = "restore-vol"
    client.create_volume(name=restore_vol_name,
                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                         numberOfReplicas=2,
                         fromBackup=backup.url)
    wait_for_volume_creation(client, restore_vol_name)
    monitor_restore_progress(client, restore_vol_name)
    wait_for_volume_detached(client, restore_vol_name)

    # read rwx volume data
    assert rwx_test_data == \
        read_volume_data(core_api, rwx_statefulset_pod_name, filename='test1')

    # delete orphan
    delete_orphans(client)

    # delete system backup
    if system_backup_feature_supported(client):
        system_backups_cleanup(client)

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

    # Upgrade all volumes engine images
    volumes = client.list_volume()
    for v in volumes:
        if v.name != vol_rebuild_name and \
           v.name != backup_vol_name and \
           v.name != rwx_pv_name:
            volume = client.by_id_volume(v.name)
            volume.detach()
            # when upgrading from v1.4.x to v1.5.x, attached volumes without
            # any workload pod will be automatically added the volumeAttachment
            # ticket with the ID "longhorn-ui". Therefore, we need to use that
            # ticket ID for detach call here
            volume.detach(attachmentID="longhorn-ui")
            wait_for_volume_detached(client, v.name)

    engineimages = client.list_engine_image()
    for ei in engineimages:
        if ei.image == longhorn_engine_image:
            new_ei = ei

    for v in volumes:
        if v.name != restore_vol_name:
            volume = client.by_id_volume(v.name)
            volume.engineUpgrade(image=new_ei.image)

    # Recreate Pod, and StatefulSet
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

    # Attach the volume
    for v in volumes:
        if v.name == vol_revision_enabled_name or \
                v.name == vol_revision_disabled_name:
            volume = client.by_id_volume(v.name)
            volume.attach(hostId=host_id)
            wait_for_volume_healthy(client, v.name)

    # Verify volume's engine image has been upgraded
    for v in volumes:
        if v.name != restore_vol_name:
            volume = client.by_id_volume(v.name)
            engine = get_volume_engine(volume)
            if hasattr(engine, 'engineImage'):
                print("Checking engineImage...")
                assert engine.engineImage == new_ei.image
            else:
                print("Checking image...")
                assert engine.image == new_ei.image
            assert engine.currentImage == new_ei.image

    # Check All volumes data
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
