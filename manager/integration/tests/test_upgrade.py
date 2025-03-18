import pytest
import subprocess
import time
import copy
import os

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
from common import reset_disks_for_all_nodes
from common import SETTING_V2_DATA_ENGINE, DATA_SIZE_IN_MB_1
from common import create_and_wait_deployment, get_deployment_pod_names
from common import write_pod_volume_random_data
from common import make_deployment_with_pvc # NOQA
from common import wait_deployment_replica_ready
from common import v2_data_engine_cr_supported
from common import get_instance_manager_names
from common import LONGHORN_NAMESPACE
from common import RETRY_COUNTS, RETRY_INTERVAL
from test_orphan import create_orphaned_directories_on_host
from test_orphan import delete_orphans
from backupstore import set_backupstore_s3
from backupstore import set_backupstore_nfs, mount_nfs_backupstore


def wait_for_engine_image_upgraded(client, volume_name, engine_image_name): # NOQA
    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    if hasattr(engine, 'engineImage'):
        upgraded = False
        for i in range(RETRY_COUNTS):
            print(f"Waiting for {volume_name} ei '{engine.engineImage}' \
                  upgraded to {engine_image_name} ... ({i})")
            if engine.engineImage == engine_image_name:
                upgraded = True
                break
            else:
                time.sleep(RETRY_INTERVAL)
                volume = client.by_id_volume(volume_name)
                engine = get_volume_engine(volume)
        assert upgraded, \
               f"assert volume {volume_name} engine image upgraded to \
                 {engine_image_name}, but it's {engine.engineImage}"
    else:
        upgraded = False
        for i in range(RETRY_COUNTS):
            print(f"Waiting for {volume_name} engine image '{engine.image}' \
                  upgraded to {engine_image_name} ... ({i})")
            if engine.image == engine_image_name:
                upgraded = True
                break
            else:
                time.sleep(RETRY_INTERVAL)
                volume = client.by_id_volume(volume_name)
                engine = get_volume_engine(volume)
        assert upgraded, \
               f"assert volume {volume_name} engine image upgraded to \
                 {engine_image_name}, but it's {engine.image}"
    upgraded = False
    for i in range(RETRY_COUNTS):
        print(f"Waiting for {volume_name} current image \
                '{engine.currentImage}' \
                upgraded to {engine_image_name} ... ({i})")
        if engine.currentImage == engine_image_name:
            upgraded = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            engine = get_volume_engine(volume)
    assert upgraded, \
           f"assert volume {volume_name} current image upgraded to \
             {engine_image_name}, but it's {engine.currentImage}"


def longhorn_upgrade(upgrade_to_transient_version=False):

    if upgrade_to_transient_version:
        upgrade_function = "install_longhorn_transient"
    else:
        upgrade_function = "install_longhorn_custom"

    longhorn_install_method = os.getenv('LONGHORN_INSTALL_METHOD', 'manifest')

    if longhorn_install_method == "manifest":
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
    elif longhorn_install_method == "helm":
        command = "./pipelines/utilities/longhorn_helm_chart.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
    elif longhorn_install_method == "rancher":
        command = "./pipelines/utilities/longhorn_rancher_chart.sh"
        upgrade_function = "upgrade_longhorn_transient" \
            if upgrade_to_transient_version else "upgrade_longhorn_custom"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
    elif longhorn_install_method == "flux":
        command = "./pipelines/utilities/flux.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
    elif longhorn_install_method == "argocd":
        command = "./pipelines/utilities/argocd.sh"
        upgrade_function = "upgrade_longhorn_transient" \
            if upgrade_to_transient_version else "upgrade_longhorn_custom"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
    elif longhorn_install_method == "fleet":
        command = "./pipelines/utilities/fleet.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)

    process.wait()
    if process.returncode == 0:
        longhorn_upgraded = True

    else:
        longhorn_upgraded = False

    return longhorn_upgraded


@pytest.mark.upgrade  # NOQA
def test_upgrade(client, core_api, volume_name, csi_pv, # NOQA
                 pvc, pod_make, statefulset, rwx_statefulset, storage_class, # NOQA
                 make_deployment_with_pvc): # NOQA
    """
    Test Longhorn upgrade

    TODO
    The test will cover both volume has revision counter enabled and
    disabled cases.

    Prerequisite:
      - Disable Auto Salvage Setting

    0. Add block disks
    1. Find the upgrade image tag
    2. Create a volume, generate and write data into the volume.
        1. Create vol_revision_enabled with revision counter enabled case.
        2. Create vol_revision_disabled with revision counter disabled case.
        3. Create vol_rebuild for replica rebuilding after system upgrade
           & engine live upgrade
        4. Create strict local volume strict_local_vol
        5. Create vol_detached, never attached before upgrade
        6. Create vol_detached_with_data
        7. Create v2 volumes
            1. Create vol_v2
            2. Create vol_detached_v2, never attached before upgrade
            3. Dynamic provisioned a v2 volume with deployment
    3. Create a Pod using a volume, generate and write data
    4. Create a StatefulSet with 2 replicas
       generate and write data to their volumes
    5. Keep all volumes attached, except vol_detached, vol_detached_with_data,
       vol_v2_detached, vol_v2.
    6. Create custom resources
       1. v2 data engine custom resources
           1. backup
           2. backing image
    7. Upgrade Longhorn system.
    8. Check Pod and StatefulSet, v1 instance manager pod didn't restart after
       system upgrade
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
    v2_data_engine_crs_before_upgrade = \
        v2_data_engine_cr_supported(client)
    if v2_data_engine_crs_before_upgrade:
        # This test case is always executed in the pipeline, and the pipeline
        # environment is guaranteed to have block devices.
        # Therefore, forcefully add block disks here regardless of the value
        # of the RUN_V2_TEST environment variable to test Longhorn upgrade
        # with v2 volume exist.
        update_setting(client, SETTING_V2_DATA_ENGINE, "true")
        reset_disks_for_all_nodes(client, add_block_disks=True)

    host_id = get_self_host_id()
    pod_data_path = "/data/test"
    instance_managers_shoud_not_restart = []

    # Disable Auto Salvage Setting
    update_setting(client, SETTING_AUTO_SALVAGE, "false")

    # 2-1 Create vol_revision_enabled with revision counter enabled
    # attached to a node
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "false")
    vol_revision_enabled_name = 'vol-revision-enabled'
    vol_revision_enabled, vol_revision_enabled_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_revision_enabled_name,
                                     data_engine="v1")

    # 2-2 Create vol_revision_disabled with revision counter disable
    # attached to a node
    update_setting(client, SETTING_DISABLE_REVISION_COUNTER, "true")
    vol_revision_disabled_name = 'vol-revision-disabled'
    vol_revision_disabled, vol_revision_disabled_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_revision_disabled_name,
                                     data_engine="v1")

    # 2-3 Create vol_rebuild for replica rebuilding after system upgrade
    # & engine live upgrade
    vol_rebuild_name = 'vol-rebuild'
    vol_rebuild, vol_rebuild_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_rebuild_name,
                                     data_engine="v1")

    # Create vol_detached_with_data
    vol_detached_with_data_name = "vol-detached-with-data"
    vol_detached_with_data, vol_detached_data_before_sys_upgrade = \
        create_volume_and_write_data(client, vol_detached_with_data_name,
                                     data_engine="v1")
    vol_detached_with_data.detach()
    vol_detached_with_data = \
        wait_for_volume_detached(client,
                                 vol_detached_with_data_name)

    # Create Volume used by Pod
    pod_volume_name = 'lh-vol-pod-test'
    test_pod_pvc = copy.deepcopy(pvc)
    pod_name, pv_name, pvc_name, pod_md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, test_pod_pvc,
                                    pod_make, pod_volume_name,
                                    data_path=pod_data_path,
                                    add_liveness_probe=False,
                                    data_engine="v1")

    # Create multiple volumes used by StatefulSet
    statefulset_name = 'statefulset-upgrade-test'
    update_statefulset_manifests(statefulset,
                                 storage_class,
                                 statefulset_name)
    create_storage_class(storage_class, data_engine="v1")
    create_and_wait_statefulset(statefulset)
    statefulset_pod_info = get_statefulset_pod_info(core_api, statefulset)

    for sspod_info in statefulset_pod_info:
        sspod_info['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api,
                              sspod_info['pod_name'],
                              sspod_info['data'])

    # get all v1 instance manager pod names
    instance_manager_names =  \
        get_instance_manager_names(client, data_engine="v1")
    instance_managers_shoud_not_restart.extend(instance_manager_names)

    # Create strict-local volume
    strict_local_vol_name = 'vol-strict-local'
    strict_local_vol = client.create_volume(
        name=strict_local_vol_name,
        size=str(2 * Gi),
        numberOfReplicas=1,
        dataLocality="strict-local")
    strict_local_vol = wait_for_volume_detached(client, strict_local_vol_name)
    strict_local_vol.attach(hostId=host_id)
    strict_local_vol = wait_for_volume_healthy(client, strict_local_vol_name)
    strict_local_vol_data_before_sys_upgrade = \
        write_volume_random_data(strict_local_vol)

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
    backup_vol = create_and_check_volume(client, backup_vol_name,
                                         num_of_replicas=2,
                                         size=str(DEFAULT_VOLUME_SIZE * Gi),
                                         data_engine="v1")
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

    # Create vol_detached, never attached before upgrade
    # system backup will attach the volume, create volume here to avoid attach
    vol_detached_name = "vol-detached"
    vol_detached = create_and_check_volume(client, vol_detached_name,
                                           data_engine="v1")

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

    # v2 data engine CRs
    if v2_data_engine_crs_before_upgrade:
        v2_backing_image_name = BACKING_IMAGE_NAME + "-v2"
        create_backing_image_with_matching_url(
            client,
            v2_backing_image_name,
            BACKING_IMAGE_QCOW2_URL,
            dataEngine="v2")

        vol_detached_v2_name = "vol-detached-v2"
        vol_detached_v2 = create_and_check_volume(client, vol_detached_v2_name,
                                                  data_engine="v2")

        vol_v2_name = "vol-v2"
        vol_v2, vol_v2_data_before_sys_upgrade = \
            create_volume_and_write_data(client, vol_v2_name, data_engine="v2")
        vol_v2.detach()
        vol_v2 = wait_for_volume_detached(client, vol_v2_name)

        v2_data_sc_name = "longhorn-v2-data-engine-test"
        v2_storage_class = copy.deepcopy(storage_class)
        v2_storage_class['metadata']['name'] = v2_data_sc_name
        create_storage_class(v2_storage_class, data_engine="v2")

        v2_pv_name = 'v2-volume-test-pv'
        v2_pvc_name = 'v2-volume-test-pvc'
        v2_pvc = copy.deepcopy(pvc)
        v2_pvc['metadata']['name'] = v2_pvc_name
        v2_pvc['spec']['storageClassName'] = \
            v2_storage_class['metadata']['name']

        v2_deployment_name = v2_pvc_name + "-dep"
        core_api.create_namespaced_persistent_volume_claim(
            body=v2_pvc, namespace='default')
        v2_deployment = make_deployment_with_pvc(v2_deployment_name,
                                                 v2_pvc_name)
        apps_api = get_apps_api_client()
        create_and_wait_deployment(apps_api, v2_deployment)

        pod_names = get_deployment_pod_names(core_api, v2_deployment)
        write_pod_volume_random_data(core_api, pod_names[0], "/data/test",
                                     DATA_SIZE_IN_MB_1)
        v2_dep_data = read_volume_data(core_api, pod_names[0], 'default')

        v2_deployment['spec']['replicas'] = 0
        apps_api.patch_namespaced_deployment(body=v2_deployment,
                                             namespace='default',
                                             name=v2_deployment["metadata"]["name"]) # NOQA

        v2_pv_name = get_volume_name(core_api, v2_pvc_name)
        wait_for_volume_detached(client, v2_pv_name)

        # Create v2 volume backup
        backup_vol_v2_name = "backup-vol-v2"
        backup_vol_v2 = create_and_check_volume(client, backup_vol_v2_name,
                                                num_of_replicas=2,
                                                size=str(DEFAULT_VOLUME_SIZE * Gi), # NOQA
                                                data_engine="v2")
        backup_vol_v2.attach(hostId=host_id)
        backup_vol_v2 = wait_for_volume_healthy(client, backup_vol_v2_name)
        data2 = {'pos': 0, 'len': BACKUP_BLOCK_SIZE,
                 'content': generate_random_data(BACKUP_BLOCK_SIZE)}
        _, backup2, _, _ = create_backup(client, backup_vol_v2_name, data2)

        backup_vol_v2.detach()
        backup_vol_v2 = wait_for_volume_detached(client, backup_vol_v2_name)

    longhorn_transient_version = os.getenv('LONGHORN_TRANSIENT_VERSION', '')
    if longhorn_transient_version and len(longhorn_transient_version) > 0:
        # upgrade Longhorn manager to transient version
        assert longhorn_upgrade(upgrade_to_transient_version=True)

        # wait for 1 minute before checking pod restarts
        time.sleep(60)

    # upgrade Longhorn manager
    assert longhorn_upgrade()

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
        read_volume_data(
            core_api,
            rwx_statefulset_pod_name,
            filename='test1'), \
        f"assert rwx statefulset {rwx_statefulset_pod_name} data intact"

    # delete orphan
    delete_orphans(client)

    # delete system backup
    if system_backup_feature_supported(client):
        system_backups_cleanup(client)

    # Check Pod and StatefulSet didn't restart after upgrade
    pod = core_api.read_namespaced_pod(name=pod_name,
                                       namespace='default')
    assert pod.status.container_statuses[0].restart_count == 0, \
        f"assert pod {pod_name} didn't restart after upgrade"

    for sspod_info in statefulset_pod_info:
        sspod = core_api.read_namespaced_pod(name=sspod_info['pod_name'],
                                             namespace='default')
        assert sspod.status.container_statuses[0].restart_count == 0, \
            f"assert pod {sspod_info['pod_name']} didn't restart after upgrade"

    # check instance manager should not restart after upgrade
    for instance_manager_name in instance_managers_shoud_not_restart:
        pod = core_api.read_namespaced_pod(name=instance_manager_name,
                                           namespace=LONGHORN_NAMESPACE)
        assert pod.status.container_statuses[0].restart_count == 0, \
            f"assert pod {instance_manager_name} didn't restart after upgrade"

    # Attach all detached volume after system upgrade
    vol_detached = client.by_id_volume(vol_detached_name)
    vol_detached.attach(hostId=host_id)
    vol_detached = wait_for_volume_healthy(client, vol_detached_name)

    vol_detached_with_data = client.by_id_volume(vol_detached_with_data_name)
    vol_detached_with_data.attach(hostId=host_id)
    vol_detached_with_data = \
        wait_for_volume_healthy(client, vol_detached_with_data_name)

    # Check all volumes data after system upgrade
    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_before_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_before_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_before_sys_upgrade)
    check_volume_data(strict_local_vol,
                      strict_local_vol_data_before_sys_upgrade)
    check_volume_data(vol_detached_with_data,
                      vol_detached_data_before_sys_upgrade)

    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data'], \
            f"assert pod {sspod_info['pod_name']} data intact after upgrade"

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum, \
        f"assert pod {pod_name} data intact after upgrade"

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
    strict_local_vol_data_after_sys_upgrade = \
        write_volume_random_data(strict_local_vol)
    vol_detached_data_after_sys_upgrade = \
        write_volume_random_data(vol_detached_with_data)

    # Check data written to all volumes
    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data'], \
            f"assert data can be written to {sspod_info['pod_name']} \
              after upgrade"

    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_after_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_after_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_after_sys_upgrade)
    check_volume_data(vol_detached_with_data,
                      vol_detached_data_after_sys_upgrade)
    # Check data written to strict-local volume
    check_volume_data(strict_local_vol,
                      strict_local_vol_data_after_sys_upgrade)

    # Detach the vol_revision_enabled & vol_revision_disabled,
    # and Delete Pod, and StatefulSet to detach their volumes

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
           v.name != rwx_pv_name and \
           v.dataEngine != "v2":
            print(f"Detaching volume {v.name}")
            volume = client.by_id_volume(v.name)
            volume.detach()
            # when upgrading from v1.4.x to v1.5.x, attached volumes without
            # any workload pod will be automatically added the volumeAttachment
            # ticket with the ID "longhorn-ui". Therefore, we need to use that
            # ticket ID for detach call here
            volume.detach(attachmentID="longhorn-ui")
            wait_for_volume_detached(client, v.name)
            print(f"Detached volume {v.name}")

    engineimages = client.list_engine_image()
    # the longhorn engine image to be upgraded to
    # it should be defined,
    # so os.environ is used to throw error if it's not found
    longhorn_engine_image = os.environ['CUSTOM_LONGHORN_ENGINE_IMAGE']
    print(f"target longhorn engine image = {longhorn_engine_image}")
    print("listing available longhorn engine images:")
    for ei in engineimages:
        print(f"{ei.image}")
        if ei.image == longhorn_engine_image:
            new_ei = ei

    for v in volumes:
        if v.name != restore_vol_name and \
           v.dataEngine != "v2":
            volume = client.by_id_volume(v.name)
            volume.engineUpgrade(image=new_ei.image)
            print(f"Upgrading volume {v.name} engine image")

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
    volumes_to_attach = [vol_revision_enabled_name,
                         vol_revision_disabled_name,
                         strict_local_vol_name,
                         vol_detached_with_data_name,
                         vol_detached_name]
    for v in volumes:
        if v.name in volumes_to_attach:
            volume = client.by_id_volume(v.name)
            volume.attach(hostId=host_id)
            wait_for_volume_healthy(client, v.name)

    # Verify volume's engine image has been upgraded
    for v in volumes:
        if v.name != restore_vol_name and \
           v.dataEngine != "v2":
            wait_for_engine_image_upgraded(client, v.name, new_ei.image)

    # Check All volumes data
    for sspod_info in statefulset_pod_info:
        resp = read_volume_data(core_api, sspod_info['pod_name'])
        assert resp == sspod_info['data']

    res_pod_md5sum = get_pod_data_md5sum(core_api, pod_name, pod_data_path)
    assert res_pod_md5sum == pod_md5sum, \
        f"assert pod {pod_name} data intact after engine upgrade"

    check_volume_data(vol_revision_enabled,
                      vol_revision_enabled_data_after_sys_upgrade)
    check_volume_data(vol_revision_disabled,
                      vol_revision_disabled_data_after_sys_upgrade)
    check_volume_data(vol_rebuild,
                      vol_rebuild_data_after_sys_upgrade)
    check_volume_data(strict_local_vol,
                      strict_local_vol_data_after_sys_upgrade)
    check_volume_data(vol_detached_with_data,
                      vol_detached_data_after_sys_upgrade)

    def test_replica_rebuilding(client, volume_name):
        # Delete one healthy replica for vol_rebuild to trigger the rebuilding
        delete_replica_on_test_node(client, volume_name)
        # Make sure vol_rebuild replica is deleted
        replica_count = 2
        vol_rebuild = wait_for_volume_replica_count(client, volume_name,
                                                    replica_count)
        # vol_rebuild will become degraded and start replica rebuilding
        # Wait for replica rebuilding to complete
        # Verify the vol_rebuild is still healthy
        vol_rebuild = wait_for_volume_degraded(client, volume_name)
        assert vol_rebuild.robustness == "degraded", \
            f"assert volume {volume_name} degraded after replica deleted"
        vol_rebuild = wait_for_volume_healthy(client, volume_name)
        assert vol_rebuild.robustness == "healthy", \
            f"assert volume {volume_name} rebuilt and recovered to healthy"
        assert len(vol_rebuild.replicas) == 3, \
            f"assert volume {volume_name} replica count = 3"

    test_replica_rebuilding(client, vol_rebuild_name)

    # v2 data engine CRs
    if v2_data_engine_crs_before_upgrade:
        restore_vol_v2_name = "restore-vol-v2"
        client.create_volume(name=restore_vol_v2_name,
                             size=str(DEFAULT_VOLUME_SIZE * Gi),
                             numberOfReplicas=2,
                             fromBackup=backup2.url,
                             dataEngine="v2")
        wait_for_volume_creation(client, restore_vol_v2_name)
        monitor_restore_progress(client, restore_vol_v2_name)
        wait_for_volume_detached(client, restore_vol_v2_name)

        vol_detached_v2 = client.by_id_volume(vol_detached_v2_name)
        vol_detached_v2.attach(hostId=host_id)
        vol_detached_v2 = wait_for_volume_healthy(client, vol_detached_v2_name)

        vol_v2 = client.by_id_volume(vol_v2_name)
        vol_v2.attach(hostId=host_id)
        vol_v2 = wait_for_volume_healthy(client, vol_v2_name)

        check_volume_data(vol_v2,
                          vol_v2_data_before_sys_upgrade)

        vol_v2_data_after_sys_upgrade = write_volume_random_data(vol_v2)
        check_volume_data(vol_v2, vol_v2_data_after_sys_upgrade)

        # Scale up deployment v2 and check data
        v2_deployment['spec']['replicas'] = 1
        apps_api.patch_namespaced_deployment(body=v2_deployment,
                                             namespace='default',
                                             name=v2_deployment_name)
        wait_deployment_replica_ready(apps_api, v2_deployment_name, 1)
        pod_names = get_deployment_pod_names(core_api, v2_deployment)
        assert read_volume_data(core_api, pod_names[0], 'default')\
            == v2_dep_data

        test_replica_rebuilding(client, vol_v2_name)


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
