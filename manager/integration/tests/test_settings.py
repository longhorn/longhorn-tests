import time
import pytest
import os
import subprocess
import yaml

from backupstore import set_random_backupstore  # NOQA

from common import (  # NOQA
    get_longhorn_api_client, get_self_host_id,
    get_core_api_client, get_apps_api_client,
    create_and_check_volume, cleanup_volume,
    wait_for_volume_healthy, wait_for_volume_detached,
    write_volume_random_data, check_volume_data,
    get_default_engine_image,
    wait_for_engine_image_state,
    wait_for_instance_manager_desire_state,
    generate_volume_name,
    wait_for_volume_condition_scheduled,
    client, core_api, settings_reset,
    apps_api, scheduling_api, priority_class, volume_name,
    get_engine_image_status_value,
    create_volume, create_volume_and_backup, cleanup_volume_by_name,
    wait_for_volume_restoration_completed, wait_for_backup_restore_completed,
    get_engine_host_id, wait_for_instance_manager_count,
    Gi, Mi,

    LONGHORN_NAMESPACE,
    SETTING_TAINT_TOLERATION,
    SETTING_GUARANTEED_INSTANCE_MANAGER_CPU,
    SETTING_PRIORITY_CLASS,
    SETTING_DEFAULT_REPLICA_COUNT,
    SETTING_BACKUP_TARGET,
    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET,
    SETTING_BACKUPSTORE_POLL_INTERVAL,
    SETTING_CONCURRENT_VOLUME_BACKUP_RESTORE,
    SETTING_V1_DATA_ENGINE,
    RETRY_COUNTS_SHORT, RETRY_COUNTS, RETRY_INTERVAL, RETRY_INTERVAL_LONG,
    update_setting, BACKING_IMAGE_QCOW2_URL, BACKING_IMAGE_NAME,
    create_backing_image_with_matching_url, BACKING_IMAGE_EXT4_SIZE,
    check_backing_image_disk_map_status, wait_for_volume_delete,
    wait_for_node_update,
    crash_replica_processes, wait_for_engine_image_ref_count,
    get_volume_engine, wait_for_volume_current_image,
    wait_for_rebuild_start, wait_for_rebuild_complete,
    wait_for_volume_degraded, write_volume_dev_random_mb_data,
    get_volume_endpoint, RETRY_EXEC_COUNTS, RETRY_SNAPSHOT_INTERVAL,
    SETTING_DEGRADED_AVAILABILITY,
    delete_replica_on_test_node,
    DATA_ENGINE, SETTING_V2_DATA_ENGINE
)

from backupstore import SETTING_BACKUP_TARGET_NOT_SUPPORTED
from backupstore import backupstore_get_backup_target

from test_infra import wait_for_node_up_longhorn

KUBERNETES_DEFAULT_TOLERATION = "kubernetes.io"
BACKING_IMAGE_CLEANUP_WAIT_INTERVAL = "50"

DEFAULT_SETTING_CONFIGMAP_NAME = "longhorn-default-setting"
DEFAULT_RESOURCE_CONFIGMAP_NAME = "longhorn-default-resource" # NOQA
DEFAULT_SETTING_YAML_NAME = "default-setting.yaml"
DEFAULT_RESOURCE_YAML_NAME = "default-resource.yaml"


def check_workload_update(core_api, apps_api, count):  # NOQA
    da_list = apps_api.list_namespaced_daemon_set(LONGHORN_NAMESPACE).items
    for da in da_list:
        if da.status.updated_number_scheduled != count:
            return False

    dp_list = apps_api.list_namespaced_deployment(LONGHORN_NAMESPACE).items
    for dp in dp_list:
        if dp.status.updated_replicas != dp.spec.replicas:
            return False

    im_pod_list = core_api.list_namespaced_pod(
        LONGHORN_NAMESPACE,
        label_selector="longhorn.io/component=instance-manager").items
    if len(im_pod_list) != count:
        return False

    for p in im_pod_list:
        if p.status.phase != "Running":
            return False

    client = get_longhorn_api_client()  # NOQA
    images = client.list_engine_image()
    assert len(images) == 1
    ei_state = get_engine_image_status_value(client, images[0].name)
    if images[0].state != ei_state:
        return False

    return True


def wait_for_longhorn_node_ready():
    client = get_longhorn_api_client()  # NOQA

    ei = get_default_engine_image(client)
    ei_name = ei["name"]
    ei_state = get_engine_image_status_value(client, ei_name)
    wait_for_engine_image_state(client, ei_name, ei_state)

    node = get_self_host_id()
    wait_for_node_up_longhorn(node, client)

    return client, node


@pytest.mark.v2_volume_test  # NOQA
def test_setting_toleration(client):  # NOQA
    """
    Test toleration setting

    1.  Set `taint-toleration` to "key1=value1:NoSchedule; key2:InvalidEffect".
    2.  Verify the request fails.
    3.  Create a volume and attach it.
    4.  Set `taint-toleration` to "key1=value1:NoSchedule; key2:NoExecute".
    5.  Verify that can update toleration setting when any volume is attached.
    6.  Generate and write `data1` into the volume.
    7.  Detach the volume.
    8.  Set `taint-toleration` to "key1=value1:NoSchedule; key2:NoExecute".
    9.  Wait for all the Longhorn system components to restart with new
        toleration.
    10. Verify that UI, manager, and drive deployer don't restart and
        don't have new toleration.
    11. Attach the volume again and verify the volume `data1`.
    12. Generate and write `data2` to the volume.
    13. Detach the volume.
    14. Clean the `toleration` setting.
    15. Wait for all the Longhorn system components to restart with no
        toleration.
    16. Attach the volume and validate `data2`.
    17. Generate and write `data3` to the volume.
    """
    client = get_longhorn_api_client()  # NOQA
    apps_api = get_apps_api_client()  # NOQA
    core_api = get_core_api_client()  # NOQA
    count = len(client.list_node())

    setting = client.by_id_setting(SETTING_TAINT_TOLERATION)

    with pytest.raises(Exception) as e:
        client.update(setting,
                      value="key1=value1:NoSchedule; key2:InvalidEffect")
    assert 'invalid effect' in str(e.value)

    volume_name = "test-toleration-vol"  # NOQA
    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    setting_value_str = "key1=value1:NoSchedule; key2:NoExecute"
    setting_value_dicts = [
        {
            "key": "key1",
            "value": "value1",
            "operator": "Equal",
            "effect": "NoSchedule"
        },
        {
            "key": "key2",
            "value": None,
            "operator": "Exists",
            "effect": "NoExecute"
        },
    ]
    update_setting(client, SETTING_TAINT_TOLERATION, setting_value_str)

    data1 = write_volume_random_data(volume)
    check_volume_data(volume, data1)

    volume.detach()
    wait_for_volume_detached(client, volume_name)

    wait_for_toleration_update(core_api, apps_api, count, setting_value_dicts)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data1)
    data2 = write_volume_random_data(volume)
    check_volume_data(volume, data2)
    volume.detach()
    wait_for_volume_detached(client, volume_name)

    # cleanup
    setting_value_str = ""
    setting_value_dicts = []
    update_setting(client, SETTING_TAINT_TOLERATION, setting_value_str)
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dicts)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data2)
    data3 = write_volume_random_data(volume)
    check_volume_data(volume, data3)

    cleanup_volume(client, volume)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_toleration_extra(client, core_api, apps_api):  # NOQA
    """
    Steps:
    1. Set Kubernetes Taint Toleration to:
       `ex.com/foobar:NoExecute;ex.com/foobar:NoSchedule`.
    2. Verify that all system components have the 2 tolerations
       `ex.com/foobar:NoExecute; ex.com/foobar:NoSchedule`.
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration.
    3. Set Kubernetes Taint Toleration to:
       `node-role.kubernetes.io/controlplane=true:NoSchedule`.
    4. Verify that all system components have the the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`,
       and don't have the 2 tolerations
       `ex.com/foobar:NoExecute;ex.com/foobar:NoSchedule`.
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration.
    5. Set Kubernetes Taint Toleration to special value:
       `:`.
    6. Verify that all system components have the toleration with
       `operator: Exists` and other field of the toleration are empty.
       Verify that all system components don't have the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`.
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration.
    7. Clear Kubernetes Taint Toleration

    Note: system components are workloads other than UI, manager, driver
    deployer
    """
    settings = [
        {
            "value": "ex.com/foobar:NoExecute;ex.com/foobar:NoSchedule",
            "expect": [
                {
                    "key": "ex.com/foobar",
                    "value": None,
                    "operator": "Exists",
                    "effect": "NoExecute"
                },
                {
                    "key": "ex.com/foobar",
                    "value": None,
                    "operator": "Exists",
                    "effect": "NoSchedule"
                },
            ],
        },
        {
            "value": "node-role.kubernetes.io/controlplane=true:NoSchedule",
            "expect": [
                {
                    "key": "node-role.kubernetes.io/controlplane",
                    "value": "true",
                    "operator": "Equal",
                    "effect": "NoSchedule"
                },
            ],
        },
        # Skip the this special toleration for now because it makes
        # Longhorn deploy manager pods on control/etcd nodes
        # and the control/etcd nodes become "down" after the test
        # clear this toleration.
        # We will enable this test once we implement logic for
        # deleting failed nodes.
        # {
        #     "value": ":",
        #     "expect": [
        #         {
        #             "key": None,
        #             "value": None,
        #             "operator": "Exists",
        #             "effect": None,
        #         },
        #     ]
        # },
        {
            "value": "",
            "expect": [],
        },
    ]

    chk_removed_tolerations = []
    for setting in settings:
        update_setting(get_longhorn_api_client(),
                       SETTING_TAINT_TOLERATION,
                       setting["value"])

        node_count = len(get_longhorn_api_client().list_node())
        wait_for_toleration_update(core_api, apps_api, node_count,
                                   setting["expect"], chk_removed_tolerations)
        chk_removed_tolerations = setting["expect"]


def wait_for_toleration_update(core_api, apps_api, count,  # NOQA
                               expected_tolerations,
                               chk_removed_tolerations=[]):
    not_managed_apps = [
        "csi-attacher",
        "csi-provisioner",
        "csi-resizer",
        "csi-snapshotter",
        "longhorn-csi-plugin",
        "longhorn-driver-deployer",
        "longhorn-manager",
        "longhorn-ui",
    ]
    updated = False
    for _ in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL_LONG)

        updated = True
        if not check_workload_update(core_api, apps_api, count):
            updated = False
            continue

        pod_list = core_api.list_namespaced_pod(LONGHORN_NAMESPACE).items
        for p in pod_list:
            managed_by = p.metadata.labels.get('longhorn.io/managed-by', '')
            if str(managed_by) != "longhorn-manager":
                continue
            else:
                app_name = str(p.metadata.labels.get('app', ''))
                assert app_name not in not_managed_apps

            if p.status.phase != "Running" \
                or not check_tolerations_set(p.spec.tolerations,
                                             expected_tolerations,
                                             chk_removed_tolerations):
                updated = False
                break
        if updated:
            break
    assert updated


def check_tolerations_set(current_toleration_list, expected_tolerations,
                          chk_removed_tolerations=[]):
    found = 0
    unexpected = 0
    for t in current_toleration_list:
        current_toleration = {
            "key": t.key,
            "value": t.value,
            "operator": t.operator,
            "effect": t.effect
        }
        for expected in expected_tolerations:
            if current_toleration == expected:
                found += 1

        for removed in chk_removed_tolerations:
            if current_toleration == removed:
                unexpected += 1
    return len(expected_tolerations) == found and unexpected == 0


def test_instance_manager_cpu_reservation(client, core_api):  # NOQA
    """
    Test if the CPU requests of instance manager pods are controlled by
    the settings and the node specs correctly.

    1. On node 1, set `node.instanceManagerCPURequest` to 150.
       --> The IM pods on this node will be restarted. And the CPU requests
       of these IM pods matches the above milli value.
    2. Change the new setting `Guaranteed Instance Manager CPU` to 10,
       Then wait for all IM pods except for the pods on node 1 restarting.
       --> The CPU requests of the restarted IM pods equals to
           the new setting value multiply the kube node allocatable CPU.
    3. Set the new settings to 0.
       --> All IM pods except for the pod on node 1 will be restarted without
        CPU requests.
    4. Set the fields on node 1 to 0.
       --> The IM pods on node 1 will be restarted without CPU requests.
    5. Set the new setting to a values smaller than 40.
       Then wait for all IM pods restarting.
       --> The CPU requests of all IM pods equals to
           the new setting value multiply the kube node allocatable CPU.
    6. Set the new setting to a value greater than 40.
       --> The setting update should fail.
    7. Create a volume, verify everything works as normal

    Note: use fixture to restore the setting into the original state
    """

    instance_managers = client.list_instance_manager()

    host_node_name = get_self_host_id()
    host_node = client.by_id_node(host_node_name)
    other_ims = []
    for im in instance_managers:
        if im.nodeID == host_node_name:
            im_on_host = im
        else:
            other_ims.append(im)
    assert im_on_host

    host_kb_node = core_api.read_node(host_node_name)
    if host_kb_node.status.allocatable["cpu"].endswith('m'):
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"][:-1])
    else:
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"])*1000

    client.update(host_node, allowScheduling=True,
                  instanceManagerCPURequest=150)
    time.sleep(5)
    guaranteed_instance_manager_cpu_setting_check(
        client, core_api, [im_on_host], "Running", True, "150m")

    update_setting(client, SETTING_GUARANTEED_INSTANCE_MANAGER_CPU, "10")
    time.sleep(5)
    guaranteed_instance_manager_cpu_setting_check(
        client, core_api, other_ims, "Running", True,
        str(int(allocatable_millicpu*10/100)) + "m")

    update_setting(client, SETTING_GUARANTEED_INSTANCE_MANAGER_CPU, "0")
    time.sleep(5)
    guaranteed_instance_manager_cpu_setting_check(
        client, core_api, other_ims, "Running", True, "")

    ims = other_ims
    ims.append(im_on_host)

    host_node = client.by_id_node(host_node_name)
    client.update(host_node, allowScheduling=True,
                  instanceManagerCPURequest=0)
    time.sleep(5)
    guaranteed_instance_manager_cpu_setting_check(
        client, core_api, ims, "Running", True, "")

    update_setting(client, SETTING_GUARANTEED_INSTANCE_MANAGER_CPU, "20")
    time.sleep(5)
    guaranteed_instance_manager_cpu_setting_check(
        client, core_api, ims, "Running", True,
        str(int(allocatable_millicpu*20/100)) + "m")

    with pytest.raises(Exception) as e:
        setting = client.by_id_setting(SETTING_GUARANTEED_INSTANCE_MANAGER_CPU)
        client.update(setting, value="41")
    assert "should be less than 40" in \
           str(e.value)

    # Create a volume to test
    vol_name = generate_volume_name()
    volume = create_and_check_volume(client, vol_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, vol_name)
    assert len(volume.replicas) == 3
    data = write_volume_random_data(volume)
    check_volume_data(volume, data)
    cleanup_volume(client, volume)


def guaranteed_instance_manager_cpu_setting_check(  # NOQA
        client, core_api, instance_managers, state, desire, cpu_val):  # NOQA
    """
    We check if instance managers are in the desired state with
    correct setting
    desire is for reflect the state we are looking for.
    If desire is True, meanning we need the state to be the same.
    Otherwise, we are looking for the state to be different.
    e.g. 'Pending', 'OutofCPU', 'Terminating' they are all 'Not Running'.
    """

    # Give sometime to k8s to update the instance manager status
    for im in instance_managers:
        wait_for_instance_manager_desire_state(client, core_api,
                                               im.name, state, desire)

    if desire:
        # Verify guaranteed CPU set correctly
        for im in instance_managers:
            pod = core_api.read_namespaced_pod(name=im.name,
                                               namespace=LONGHORN_NAMESPACE)
            if cpu_val:
                assert (pod.spec.containers[0].resources.requests['cpu'] ==
                        cpu_val)
            else:
                assert (not pod.spec.containers[0].resources.requests)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_priority_class(client, core_api, apps_api, scheduling_api, priority_class, volume_name):  # NOQA
    """
    Test that the Priority Class setting is validated and utilized correctly.

    1. Verify that the name of a non-existent Priority Class cannot be used
    for the Setting.
    2. Create a new Priority Class in Kubernetes.
    3. Create and attach a Volume.
    4. Verify that the Priority Class Setting can be updated with an attached
       volume.
    5. Generate and write `data1`.
    6. Detach the Volume.
    7. Update the Priority Class Setting to the new Priority Class.
    8. Wait for all the Longhorn system components to restart with the new
       Priority Class.
    9. Verify that UI, manager, and drive deployer don't have Priority Class
    10. Attach the Volume and verify `data1`.
    11. Generate and write `data2`.
    12. Unset the Priority Class Setting.
    13. Wait for all the Longhorn system components to restart with the new
        Priority Class.
    14. Verify that UI, manager, and drive deployer don't have Priority Class
    15. Attach the Volume and verify `data2`.
    16. Generate and write `data3`.

    Note: system components are workloads other than UI, manager, driver
     deployer
    """
    client = get_longhorn_api_client()  # NOQA
    count = len(client.list_node())
    name = priority_class['metadata']['name']
    setting = client.by_id_setting(SETTING_PRIORITY_CLASS)

    with pytest.raises(Exception) as e:
        client.update(setting, value=name)
    assert 'failed to get priority class ' in str(e.value)

    scheduling_api.create_priority_class(priority_class)

    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    update_setting(client, SETTING_PRIORITY_CLASS, name)

    data1 = write_volume_random_data(volume)
    check_volume_data(volume, data1)

    volume.detach()
    wait_for_volume_detached(client, volume_name)

    wait_for_priority_class_update(core_api, apps_api, count, priority_class)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data1)
    data2 = write_volume_random_data(volume)
    check_volume_data(volume, data2)
    volume.detach()
    wait_for_volume_detached(client, volume_name)

    update_setting(client, SETTING_PRIORITY_CLASS, '')
    wait_for_priority_class_update(core_api, apps_api, count)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data2)
    data3 = write_volume_random_data(volume)
    check_volume_data(volume, data3)

    cleanup_volume(client, volume)


def check_priority_class(pod, priority_class=None):  # NOQA
    if priority_class:
        return pod.spec.priority == priority_class['value'] and \
               pod.spec.priority_class_name == \
               priority_class['metadata']['name']
    else:
        return pod.spec.priority == 0 and pod.spec.priority_class_name == ''


def wait_for_priority_class_update(core_api, apps_api, count, priority_class=None):  # NOQA
    updated = False

    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL_LONG)
        updated = True

        if not check_workload_update(core_api, apps_api, count):
            updated = False
            continue

        pod_list = core_api.list_namespaced_pod(LONGHORN_NAMESPACE).items
        for p in pod_list:
            if p.status.phase != "Running" and \
                    not check_priority_class(p, priority_class):
                updated = False
                break
        if not updated:
            continue

        if updated:
            break

    assert updated


@pytest.mark.backing_image  # NOQA
def test_setting_backing_image_auto_cleanup(client, core_api, volume_name):  # NOQA
    """
    Test that the Backing Image Cleanup Wait Interval setting works correctly.

    The default value of setting `BackingImageCleanupWaitInterval` is 60.

    1. Clean up the backing image work directory so that the current case
       won't be intervened by previous tests.
    2. Create a backing image.
    3. Create multiple volumes using the backing image.
    4. Attach all volumes, Then:
        1. Wait for all volumes can become running.
        2. Verify the correct in all volumes.
        3. Verify the backing image disk status map.
        4. Verify the only backing image file in each disk is reused by
           multiple replicas. The backing image file path is
           `<Data path>/<The backing image name>/backing`
    5. Unschedule test node to guarantee when replica removed from test node,
       no new replica can be rebuilt on the test node.
    6. Remove all replicas in one disk.
       Wait for 50 seconds.
       Then verify nothing changes in the backing image disk state map
       (before the cleanup wait interval is passed).
    7. Modify `BackingImageCleanupWaitInterval` to a small value. Then verify:
        1. The download state of the disk containing no replica becomes
           terminating first, and the entry will be removed from the map later.
        2. The related backing image file is removed.
        3. The download state of other disks keep unchanged.
           All volumes still work fine.
    8. Delete all volumes. Verify that there will only remain 1 entry in the
       backing image disk map
    9. Delete the backing image.
    """

    # Step 1
    subprocess.check_call(["rm", "-rf", "/var/lib/longhorn/backing-images"])

    # Step 2
    create_backing_image_with_matching_url(
            client, BACKING_IMAGE_NAME, BACKING_IMAGE_QCOW2_URL)

    # Step 3
    volume_names = [
        volume_name + "-1",
        volume_name + "-2",
        volume_name + "-3"
    ]

    for volume_name in volume_names:
        create_and_check_volume(client, volume_name,
                                num_of_replicas=3,
                                size=str(BACKING_IMAGE_EXT4_SIZE),
                                backing_image=BACKING_IMAGE_NAME)

    # Step 4
    lht_host_id = get_self_host_id()
    for volume_name in volume_names:
        volume = client.by_id_volume(volume_name)
        volume.attach(hostId=lht_host_id)
    for volume_name in volume_names:
        volume = wait_for_volume_healthy(client, volume_name)
        assert volume.backingImage == BACKING_IMAGE_NAME

    backing_image = client.by_id_backing_image(BACKING_IMAGE_NAME)
    assert len(backing_image.diskFileStatusMap) == 3
    for disk_id, status in iter(backing_image.diskFileStatusMap.items()):
        assert status.state == "ready"

    backing_images_in_disk = os.listdir("/var/lib/longhorn/backing-images")
    assert len(backing_images_in_disk) == 1
    assert os.path.exists("/var/lib/longhorn/backing-images/{}/backing"
                          .format(backing_images_in_disk[0]))
    assert os.path.exists("/var/lib/longhorn/backing-images/{}/backing.cfg"
                          .format(backing_images_in_disk[0]))

    # Step 5
    current_host = client.by_id_node(id=lht_host_id)
    client.update(current_host, allowScheduling=False)
    wait_for_node_update(client, lht_host_id, "allowScheduling", False)

    # Step 6
    for volume_name in volume_names:
        volume = client.by_id_volume(volume_name)
        for replica in volume.replicas:
            if replica.hostId == lht_host_id:
                replica_name = replica.name
                volume.replicaRemove(name=replica_name)
    # This wait interval should be smaller than the setting value.
    # Otherwise, the backing image files may be cleaned up.
    time.sleep(int(BACKING_IMAGE_CLEANUP_WAIT_INTERVAL))
    check_backing_image_disk_map_status(client, BACKING_IMAGE_NAME, 3, "ready")

    # Step 7
    update_setting(client, "backing-image-cleanup-wait-interval", "1")
    check_backing_image_disk_map_status(client, BACKING_IMAGE_NAME, 2, "ready")

    for i in range(RETRY_EXEC_COUNTS):
        try:
            backing_images_in_disk = os.listdir(
                "/var/lib/longhorn/backing-images")
            assert len(backing_images_in_disk) == 0
        except Exception:
            time.sleep(RETRY_INTERVAL)

    # Step 8
    for volume_name in volume_names:
        volume = client.by_id_volume(volume_name)
        client.delete(volume)
        wait_for_volume_delete(client, volume_name)

    check_backing_image_disk_map_status(client, BACKING_IMAGE_NAME, 1, "ready")


def test_setting_concurrent_rebuild_limit(client, core_api, volume_name):  # NOQA
    """
    Test if setting Concurrent Replica Rebuild Per Node Limit works correctly.

    The default setting value is 0, which means no limit.

    Case 1 - the setting will limit the rebuilding correctly:
    1. Set `ConcurrentReplicaRebuildPerNodeLimit` to 1.
    2. Create 2 volumes then attach both volumes.
    3. Write a large amount of data into both volumes,
       so that the rebuilding will take a while.
    4. Delete one replica for volume 1 then the replica on the same node for
       volume 2 to trigger (concurrent) rebuilding.
    5. Verify the new replica of volume 2 won't be started until volume 1
       rebuilding complete.
       And the new replica of volume 2 will be started immediately once
       the 1st rebuilding is done.
    6. Wait for rebuilding complete then repeat step 4.
    7. Set `ConcurrentReplicaRebuildPerNodeLimit` to 0 or 2 while the volume 1
       rebuilding is still in progress.
       Then the new replica of volume 2 will be started immediately before
       the 1st rebuilding is done.
    8. Wait for rebuilding complete then repeat step 4.
    9. Set `ConcurrentReplicaRebuildPerNodeLimit` to 1
    10. Crash the replica process of volume 1 while the rebuilding is
        in progress.
        Then the rebuilding of volume 2 will be started, and the rebuilding of
        volume 1 will wait for the volume 2 becoming healthy.

   (There is no need to clean up the above 2 volumes.)

    Case 2 - the setting won't intervene normal attachment:
    1. Set `ConcurrentReplicaRebuildPerNodeLimit` to 1.
    2. Make volume 1 state attached and healthy while volume 2 is detached.
    3. Delete one replica for volume 1 to trigger the rebuilding.
    4. Attach then detach volume 2. The attachment/detachment should succeed
       even if the rebuilding in volume 1 is still in progress.
   """
    # Step 1-1
    update_setting(client,
                   "concurrent-replica-rebuild-per-node-limit",
                   "1")

    # Step 1-2
    volume1_name = "test-vol-1"  # NOQA
    volume1 = create_and_check_volume(client, volume1_name, size=str(4 * Gi))
    volume1.attach(hostId=get_self_host_id())
    volume1 = wait_for_volume_healthy(client, volume1_name)

    volume2_name = "test-vol-2"  # NOQA
    volume2 = create_and_check_volume(client, volume2_name, size=str(4 * Gi))
    volume2.attach(hostId=get_self_host_id())
    volume2 = wait_for_volume_healthy(client, volume2_name)

    # Step 1-3
    volume1_endpoint = get_volume_endpoint(volume1)
    volume2_endpoint = get_volume_endpoint(volume2)
    write_volume_dev_random_mb_data(volume1_endpoint,
                                    1, 3500, 5)
    write_volume_dev_random_mb_data(volume2_endpoint,
                                    1, 3500, 5)

    # Step 1-4, 1-5
    delete_replica_on_test_node(client, volume1_name)
    wait_for_rebuild_start(client, volume1_name)
    delete_replica_on_test_node(client, volume2_name)

    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1_name)
        volume2 = client.by_id_volume(volume2_name)

        if volume1.rebuildStatus == []:
            break

        assert volume1.rebuildStatus[0].state == "in_progress"
        assert volume2.rebuildStatus == []

        time.sleep(RETRY_INTERVAL)

    wait_for_rebuild_complete(client, volume1_name)
    wait_for_rebuild_start(client, volume2_name)
    wait_for_rebuild_complete(client, volume2_name)

    # Step 1-6
    wait_for_volume_healthy(client, volume1_name)
    wait_for_volume_healthy(client, volume2_name)

    # Step 1-7
    delete_replica_on_test_node(client, volume1_name)
    delete_replica_on_test_node(client, volume2_name)
    update_setting(client,
                   "concurrent-replica-rebuild-per-node-limit",
                   "2")

    # In a 2 minutes retry loop:
    # verify that volume 2 start rebuilding while volume 1 is still rebuilding
    concourent_build = False
    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1_name)
        volume2 = client.by_id_volume(volume2_name)
        try:
            if volume1.rebuildStatus[0].state == "in_progress" and \
                    volume2.rebuildStatus[0].state == "in_progress":
                concourent_build = True
                break
        except: # NOQA
            pass
        time.sleep(RETRY_SNAPSHOT_INTERVAL)
    assert concourent_build is True

    # Step 1-8
    wait_for_rebuild_complete(client, volume1_name)
    wait_for_rebuild_complete(client, volume2_name)

    # Step 1-9
    update_setting(client,
                   "concurrent-replica-rebuild-per-node-limit",
                   "1")

    # Step 1-10
    delete_replica_on_test_node(client, volume1_name)
    wait_for_rebuild_start(client, volume1_name)
    volume1 = client.by_id_volume(volume1_name)
    current_node = get_self_host_id()
    replicas = []
    for r in volume1.replicas:
        if r["hostId"] == current_node:
            replicas.append(r)

    assert len(replicas) > 0
    crash_replica_processes(client, core_api, volume1_name, replicas)
    delete_replica_on_test_node(client, volume2_name)

    # While one volume is rebuilding, verify another volume is not
    # rebuilding and stuck in degrading state
    rebuild_started = False
    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1_name)
        volume2 = client.by_id_volume(volume2_name)

        if volume1.rebuildStatus == [] and \
                volume2.rebuildStatus == [] and \
                rebuild_started is False:
            continue
        elif volume1.rebuildStatus == [] and \
                volume2.rebuildStatus == [] and \
                rebuild_started is True:
            break
        elif volume2.rebuildStatus == []:
            assert volume1.rebuildStatus[0].state == "in_progress"
            rebuild_started = True
        elif volume1.rebuildStatus == []:
            assert volume2.rebuildStatus[0].state == "in_progress"
            rebuild_started = True

        time.sleep(RETRY_INTERVAL)

    wait_for_rebuild_complete(client, volume2_name)
    wait_for_rebuild_complete(client, volume1_name)

    # Step 2-1
    # Step 2-2
    wait_for_volume_healthy(client, volume1_name)
    wait_for_volume_healthy(client, volume2_name)

    volume2 = client.by_id_volume(volume2_name)
    lht_host_id = get_self_host_id()
    volume2.detach(hostId=lht_host_id)

    # Step 2-2
    delete_replica_on_test_node(client, volume1_name)
    wait_for_rebuild_start(client, volume1_name)

    # Step 2-3
    volume2 = client.by_id_volume(volume2_name)
    volume2.attach(hostId=lht_host_id)

    # In a 2 minutes retry loop:
    # verify that we can see the case: volume2 becomes healthy while
    # volume1 is rebuilding
    expect_case = False
    for i in range(RETRY_COUNTS):
        volume1 = client.by_id_volume(volume1_name)
        volume2 = client.by_id_volume(volume2_name)

        try:
            if volume1.rebuildStatus[0].state == "in_progress" and \
                    volume2["robustness"] == "healthy":
                expect_case = True
                break
        except: # NOQA
            pass
        time.sleep(RETRY_INTERVAL)
    assert expect_case is True

    wait_for_volume_healthy(client, volume1_name)
    volume2.detach(hostId=lht_host_id)
    wait_for_volume_detached(client, volume2_name)

    volume2.attach(hostId=lht_host_id)
    wait_for_volume_healthy(client, volume2_name)


def setting_concurrent_volume_backup_restore_limit_concurrent_restoring_test(client, volname, is_DR_volumes=False):  # NOQA
    """
    Given Setting concurrent-volume-backup-restore-per-node-limit is 2.
    And Volume (for backup) created.
    And Volume (for backup) has backup with some data.

    When Create some volumes (num_node * setting value * 3) from backup.

    Then Number of restoring volumes per node should be expected based on
         if they are normal volumes or DR volumes.
    """
    update_setting(client, SETTING_DEGRADED_AVAILABILITY, "false")

    concurrent_limit = 2
    update_setting(client, SETTING_CONCURRENT_VOLUME_BACKUP_RESTORE,
                   str(concurrent_limit))

    _, backup = create_volume_and_backup(client, volname + "-with-backup",
                                         1000 * Mi, 600 * Mi)

    nodes = client.list_node()
    restore_volume_names = []
    for i in range(len(nodes) * concurrent_limit * 3):
        name = volname + "-restore-" + str(i)
        restore_volume_names.append(name)

        client.create_volume(name=name, numberOfReplicas=1,
                             fromBackup=backup.url, standby=is_DR_volumes,
                             dataEngine=DATA_ENGINE)

    is_case_tested = False
    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)

        restoring_volume = None
        for name in restore_volume_names:
            volume = client.by_id_volume(name)
            if volume.restoreStatus and volume.restoreStatus[0].progress != 0:
                restoring_volume = volume
                break

        if not restoring_volume:
            continue

        concurrent_count = 0
        restoring_status = restoring_volume.restoreStatus
        if len(restoring_status) != 0 and \
                restoring_status[0].progress != 100:

            restoring_host_id = get_engine_host_id(client,
                                                   restoring_volume.name)

            for restore_volume_name in restore_volume_names:
                if restore_volume_name == restoring_volume.name:
                    concurrent_count += 1
                    continue

                host_id = get_engine_host_id(client, restore_volume_name)
                if host_id != restoring_host_id:
                    continue

                volume = client.by_id_volume(restore_volume_name)
                restore_status = volume.restoreStatus
                if len(restore_status) == 0:
                    continue

                if not restore_status[0].progress or \
                        restore_status[0].progress == 0:
                    continue

                concurrent_count += 1
            if is_DR_volumes:
                if concurrent_count > concurrent_limit:
                    is_case_tested = True
                    break
            else:
                if concurrent_count == concurrent_limit:
                    is_case_tested = True
                    break

    assert is_case_tested, \
        f"Unexpected concurrent count: {concurrent_count}\n"

    for restore_volume_name in restore_volume_names:
        if is_DR_volumes:
            wait_for_backup_restore_completed(client, restore_volume_name,
                                              backup.name)
            continue
        wait_for_volume_restoration_completed(client, restore_volume_name)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_concurrent_volume_backup_restore_limit(set_random_backupstore, client, volume_name):  # NOQA
    """

    Scenario: setting Concurrent Volume Backup Restore Limit
              should limit the concurrent volume backup restoring

    Issue: https://github.com/longhorn/longhorn/issues/4558

    Given/When see:
      setting_concurrent_volume_backup_restore_limit_concurrent_restoring_test

    Then Number of restoring volumes per node not exceed the setting value.
    """
    setting_concurrent_volume_backup_restore_limit_concurrent_restoring_test(
        client, volume_name
    )


@pytest.mark.v2_volume_test  # NOQA
def test_setting_concurrent_volume_backup_restore_limit_should_not_effect_dr_volumes(set_random_backupstore, client, volume_name):  # NOQA
    """

    Scenario: setting Concurrent Volume Backup Restore Limit
              should not effect DR volumes

    Issue: https://github.com/longhorn/longhorn/issues/4558

    Given/When see:
      setting_concurrent_volume_backup_restore_limit_concurrent_restoring_test

    Then Number of restoring volumes can exceed the setting value.
    """
    setting_concurrent_volume_backup_restore_limit_concurrent_restoring_test(
        client, volume_name, is_DR_volumes=True
    )


def config_map_with_value(configmap_name, setting_names, setting_values, data_yaml_name="default-setting.yaml"): # NOQA
    setting = {}
    num_settings = len(setting_names)
    if num_settings > 0:
        for i in range(num_settings):
            setting.update({setting_names[i]: setting_values[i]})
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": configmap_name,
        },
        "data": {
            data_yaml_name: yaml.dump(setting),
        }
    }


def wait_for_setting_updated(client, name, expected_value):  # NOQA
    for _ in range(RETRY_COUNTS):
        setting = client.by_id_setting(name)
        if setting.value == expected_value:
            return True
        time.sleep(RETRY_INTERVAL)
    return False


def retry_setting_update(client, setting_name, setting_value):  # NOQA
    for i in range(RETRY_COUNTS):
        try:
            update_setting(client, setting_name, setting_value)
        except Exception as e:
            if i < RETRY_COUNTS:
                time.sleep(RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break


def init_longhorn_default_setting_configmap(core_api, client, # NOQA
                                            configmap_name=DEFAULT_SETTING_CONFIGMAP_NAME, # NOQA
                                            data_yaml_name=DEFAULT_SETTING_YAML_NAME): # NOQA
    core_api.delete_namespaced_config_map(name=configmap_name,
                                          namespace='longhorn-system')

    configmap_body = config_map_with_value(configmap_name,
                                           [],
                                           [],
                                           data_yaml_name)
    core_api.create_namespaced_config_map(body=configmap_body,
                                          namespace='longhorn-system')


def update_settings_via_configmap(core_api, client, setting_names, setting_values, request, # NOQA
                                  configmap_name=DEFAULT_SETTING_CONFIGMAP_NAME, # NOQA
                                  data_yaml_name=DEFAULT_SETTING_YAML_NAME):  # NOQA
    configmap_body = config_map_with_value(configmap_name,
                                           setting_names,
                                           setting_values,
                                           data_yaml_name)
    core_api.patch_namespaced_config_map(name=configmap_name,
                                         namespace='longhorn-system',
                                         body=configmap_body)

    def reset_default_settings():
        if configmap_name == DEFAULT_SETTING_CONFIGMAP_NAME:
            setting_names = [SETTING_DEFAULT_REPLICA_COUNT,
                             SETTING_BACKUP_TARGET,
                             SETTING_TAINT_TOLERATION]
            setting_values = ["3", "", ""]
        elif configmap_name == DEFAULT_RESOURCE_CONFIGMAP_NAME:
            setting_names = [SETTING_BACKUP_TARGET,
                             SETTING_BACKUP_TARGET_CREDENTIAL_SECRET,
                             SETTING_BACKUPSTORE_POLL_INTERVAL]
            setting_values = ["", "", "300"]
        configmap_body = config_map_with_value(configmap_name,
                                               setting_names,
                                               setting_values,
                                               data_yaml_name)
        core_api.patch_namespaced_config_map(name=configmap_name,
                                             namespace='longhorn-system',
                                             body=configmap_body)
    request.addfinalizer(reset_default_settings)


def validate_settings(core_api, client, setting_names, setting_values):  # NOQA
    num_settings = len(setting_names)
    for i in range(num_settings):
        name = setting_names[i]
        value = setting_values[i]
        assert wait_for_setting_updated(client, name, value)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_replica_count_update_via_configmap(client, core_api, request):  # NOQA
    """
    Test the default-replica-count setting via configmap
    1. Get default-replica-count value
    2. Initialize longhorn-default-setting configmap
    3. Verify default-replica-count is not changed
    4. Update longhorn-default-setting configmap with a new
       default-replica-count value
    5. Verify the updated settings
    6. Update default-replica-count setting CR with the old value
    """

    # Step 1
    client = get_longhorn_api_client()  # NOQA
    old_setting = client.by_id_setting(SETTING_DEFAULT_REPLICA_COUNT)

    # Step 2
    init_longhorn_default_setting_configmap(core_api, client)

    # Step 3
    assert wait_for_setting_updated(client,
                                    SETTING_DEFAULT_REPLICA_COUNT,
                                    old_setting.value)

    # Step 4
    replica_count = "1"
    update_settings_via_configmap(core_api,
                                  client,
                                  [SETTING_DEFAULT_REPLICA_COUNT],
                                  [replica_count],
                                  request)
    # Step 5
    validate_settings(core_api,
                      client,
                      [SETTING_DEFAULT_REPLICA_COUNT],
                      [replica_count])
    # Step 6
    retry_setting_update(client,
                         SETTING_DEFAULT_REPLICA_COUNT,
                         old_setting.definition.default)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_backup_target_update_via_configmap(client, core_api, request):  # NOQA
    """
    Test the backup target setting via configmap
    1. Initialize longhorn-default-setting configmap
    2. Update longhorn-default-setting configmap with a new backup-target
       value
    3. Verify the updated settings
    """
    # Check whether the config map `longhorn-default-resource` is created
    lh_cms = core_api.list_namespaced_config_map(namespace='longhorn-system')
    cm_names = [config_map.metadata.name for config_map in lh_cms.items]
    if DEFAULT_RESOURCE_CONFIGMAP_NAME in cm_names:
        config_map_name = DEFAULT_RESOURCE_CONFIGMAP_NAME
        data_yaml_name = DEFAULT_RESOURCE_YAML_NAME
    else:
        config_map_name = DEFAULT_SETTING_CONFIGMAP_NAME
        data_yaml_name = DEFAULT_SETTING_YAML_NAME

    # Step 1
    client = get_longhorn_api_client()  # NOQA
    init_longhorn_default_setting_configmap(core_api,
                                            client,
                                            configmap_name=config_map_name,
                                            data_yaml_name=data_yaml_name)

    # Step 2
    target = "s3://backupbucket-invalid@us-east-1/backupstore"
    update_settings_via_configmap(core_api,
                                  client,
                                  [SETTING_BACKUP_TARGET],
                                  [target],
                                  request,
                                  configmap_name=config_map_name,
                                  data_yaml_name=data_yaml_name)
    # Step 3
    try:
        validate_settings(core_api,
                          client,
                          [SETTING_BACKUP_TARGET],
                          [target])
    except Exception as e:
        if SETTING_BACKUP_TARGET_NOT_SUPPORTED in str(e):
            wait_backup_target_url_updated(client, target)
        else:
            raise e


def wait_backup_target_url_updated(client, target): # NOQA
    updated = False
    for _ in range(RETRY_COUNTS_SHORT):
        backup_target_url = backupstore_get_backup_target(client)
        if backup_target_url == target:
            updated = True
            break
        time.sleep(RETRY_INTERVAL)
    assert updated


@pytest.mark.v2_volume_test  # NOQA
def test_setting_update_with_invalid_value_via_configmap(client, core_api, request):  # NOQA
    """
    Test the default settings update with invalid value via configmap
    1. Create an attached volume
    2. Initialize longhorn-default-setting configmap containing
       valid and invalid settings
    3. Update longhorn-default-setting configmap with invalid settings.
       The invalid settings SETTING_TAINT_TOLERATION will be updated
    4. The changes will be applied once the volumes are detached. (To Do)
    5. Validate the default settings values.
    """
    # Check whether the config map `longhorn-default-resource` is created
    backup_cm_created = False
    lh_cms = core_api.list_namespaced_config_map(namespace='longhorn-system')
    cm_names = [config_map.metadata.name for config_map in lh_cms.items]
    if DEFAULT_RESOURCE_CONFIGMAP_NAME in cm_names:
        backup_cm_created = True
        bt_config_map_name = DEFAULT_RESOURCE_CONFIGMAP_NAME
        bt_data_yaml_name = DEFAULT_RESOURCE_YAML_NAME

    # Step 1
    client = get_longhorn_api_client() # NOQA
    lht_hostId = get_self_host_id()

    vol_name = generate_volume_name()
    volume = create_volume(client, vol_name, str(Gi), lht_hostId, 3)

    volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, vol_name)

    # Step 2
    init_longhorn_default_setting_configmap(core_api, client)

    # Step 3
    target = "s3://backupbucket-invalid@us-east-1/backupstore"
    update_settings_via_configmap(core_api,
                                  client,
                                  [SETTING_TAINT_TOLERATION],
                                  ["key1=value1:NoSchedule"],
                                  request)
    # Step 4
    validate_settings(core_api,
                      client,
                      [SETTING_TAINT_TOLERATION],
                      ["key1=value1:NoSchedule"])

    if backup_cm_created:
        init_longhorn_default_setting_configmap(
            core_api,
            client,
            configmap_name=bt_config_map_name,
            data_yaml_name=bt_data_yaml_name)
        update_settings_via_configmap(core_api,
                                      client,
                                      [SETTING_BACKUP_TARGET],
                                      [target],
                                      request,
                                      configmap_name=bt_config_map_name,
                                      data_yaml_name=bt_data_yaml_name)
        wait_backup_target_url_updated(client, target)

    cleanup_volume_by_name(client, vol_name)


@pytest.mark.v2_volume_test  # NOQA
def test_setting_data_engine(client, request): # NOQA
    """
    Test that the v1 data engine setting works correctly.
    1. Create a volume and attach it.
    2. Set v1 data engine setting to false. The setting should be rejected.
    3. Detach the volume.
    4. Set v1 data engine setting to false again. The setting should be
       accepted. Then, attach the volume. The volume is unable to attach.
    5. set v1 data engine setting to true. The setting should be accepted.
    6. Attach the volume.
    """
    if DATA_ENGINE == "v1":
        setting_data_engine = SETTING_V1_DATA_ENGINE
    elif DATA_ENGINE == "v2":
        setting_data_engine = SETTING_V2_DATA_ENGINE
    setting = client.by_id_setting(setting_data_engine)

    # Step 1
    volume_name = "test-{0}-vol".format(DATA_ENGINE)  # NOQA
    volume = create_and_check_volume(client, volume_name)

    def finalizer():
        cleanup_volume(client, volume)
        update_setting(client, setting_data_engine, "true")

    request.addfinalizer(finalizer)

    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    # Step 2
    with pytest.raises(Exception) as e:
        client.update(setting, value="false")
    assert 'cannot apply {0}-data-engine setting to Longhorn workloads when ' \
        'there are attached {0} volumes'.format(DATA_ENGINE) in str(e.value)

    # Step 3
    volume.detach()
    wait_for_volume_detached(client, volume_name)

    # Step 4
    update_setting(client, setting_data_engine, "false")

    count = wait_for_instance_manager_count(client, 0)
    assert count == 0

    volume.attach(hostId=get_self_host_id())
    with pytest.raises(Exception) as e:
        wait_for_volume_healthy(client, volume_name)
    assert 'volume[key]=detached' in str(e.value)

    # Step 5
    update_setting(client, setting_data_engine, "true")
    nodes = client.list_node()
    count = wait_for_instance_manager_count(client, len(nodes))
    assert count == len(nodes)

    # Step 6
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)
