import time
import pytest

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

    LONGHORN_NAMESPACE,
    SETTING_TAINT_TOLERATION,
    SETTING_GUARANTEED_ENGINE_CPU,
    SETTING_GUARANTEED_ENGINE_MANAGER_CPU,
    SETTING_GUARANTEED_REPLICA_MANAGER_CPU,
    SETTING_PRIORITY_CLASS,
    SIZE, RETRY_COUNTS, RETRY_INTERVAL, RETRY_INTERVAL_LONG,
)

from test_infra import wait_for_node_up_longhorn

KUBERNETES_DEFAULT_TOLERATION = "kubernetes.io"


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
    if len(im_pod_list) != 2 * count:
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


def test_setting_toleration():
    """
    Test toleration setting

    1. Set `taint-toleration` to "key1=value1:NoSchedule; key2:InvalidEffect"
    2. Verify the request fails
    3. Create a volume and attach it.
    4. Set `taint-toleration` to "key1=value1:NoSchedule; key2:NoExecute".
    5. Verify that cannot update toleration setting when any volume is attached
    6. Generate and write `data1` into the volume
    7. Detach the volume.
    8. Set `taint-toleration` to "key1=value1:NoSchedule; key2:NoExecute".
    9. Wait for all the Longhorn system components to restart with new
       toleration
    10. Verify that UI, manager, and drive deployer don't restart and
       don't have new toleration
    11. Attach the volume again and verify the volume `data1`.
    12. Generate and write `data2` to the volume.
    13. Detach the volume.
    14. Clean the `toleration` setting.
    15. Wait for all the Longhorn system components to restart with no
        toleration
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

    volume_name = "test-toleration-vol"  # NOQA
    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)
    with pytest.raises(Exception) as e:
        client.update(setting, value=setting_value_str)
    assert 'cannot modify toleration setting before all volumes are detached' \
           in str(e.value)

    data1 = write_volume_random_data(volume)
    check_volume_data(volume, data1)

    volume.detach(hostId="")
    wait_for_volume_detached(client, volume_name)

    setting = client.update(setting, value=setting_value_str)
    assert setting.value == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dicts)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data1)
    data2 = write_volume_random_data(volume)
    check_volume_data(volume, data2)
    volume.detach(hostId="")
    wait_for_volume_detached(client, volume_name)

    # cleanup
    setting_value_str = ""
    setting_value_dicts = []
    setting = client.by_id_setting(SETTING_TAINT_TOLERATION)
    setting = client.update(setting, value=setting_value_str)
    assert setting.value == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dicts)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data2)
    data3 = write_volume_random_data(volume)
    check_volume_data(volume, data3)

    cleanup_volume(client, volume)


def test_setting_toleration_extra(core_api, apps_api):  # NOQA
    """
    Steps:
    1. Set Kubernetes Taint Toleration to:
       `ex.com/foobar:NoExecute;ex.com/foobar:NoSchedule`
    2. Verify that all system components have the 2 tolerations
       `ex.com/foobar:NoExecute; ex.com/foobar:NoSchedule`
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration
    3. Set Kubernetes Taint Toleration to:
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
    4. Verify that all system components have the the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
       and don't have the 2 tolerations
       `ex.com/foobar:NoExecute;ex.com/foobar:NoSchedule`
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration
    5. Set Kubernetes Taint Toleration to special value:
       `:`
    6. Verify that all system components have the toleration with
       `operator: Exists` and other field of the toleration are empty.
       Verify that all system components don't have the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
       Verify that UI, manager, and drive deployer don't restart and
       don't have toleration
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
        client = get_longhorn_api_client()  # NOQA
        taint_toleration = client.by_id_setting(SETTING_TAINT_TOLERATION)
        updated = client.update(taint_toleration,
                                value=setting["value"])
        assert updated.value == setting["value"]

        node_count = len(client.list_node())
        wait_for_toleration_update(core_api, apps_api, node_count,
                                   setting["expect"], chk_removed_tolerations)
        chk_removed_tolerations = setting["expect"]


def wait_for_toleration_update(core_api, apps_api, count,  # NOQA
                               expected_tolerations,
                               chk_removed_tolerations=[]):
    updated = False
    for _ in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL_LONG)

        updated = True
        if not check_workload_update(core_api, apps_api, count):
            updated = False
            continue

        pod_list = core_api.list_namespaced_pod(LONGHORN_NAMESPACE).items
        for p in pod_list:
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

    1. Try to change the deprecated setting `Guaranteed Engine CPU`.
       --> The setting update should fail.
    2. Pick up node 1, set `node.engineManagerCPURequest` and
       `node.replicaManagerCPURequest` to 150 and 250, respectively.
       --> The IM pods on this node will be restarted. And the CPU requests
       of these IM pods matches the above milli value.
    3. Change the new settings `Guaranteed Engine Manager CPU` and
       `Guaranteed Replica Manager CPU` to 10 and 20, respectively.
       Then wait for all IM pods except for the pods on node 1 restarting.
       --> The CPU requests of the restarted IM pods equals to
           the new setting value multiply the kube node allocatable CPU.
    4. Set the both new settings to 0.
       --> All IM pods except for the pod on node 1 will be restarted without
        CPU requests.
    5. Set the fields on node 1 to 0.
       --> The IM pods on node 1 will be restarted without CPU requests.
    6. Set the both new settings to 2 random values,
       and the sum of the 2 values is small than 40.
       Then wait for all IM pods restarting.
       --> The CPU requests of all IM pods equals to
           the new setting value multiply the kube node allocatable CPU.
    7. Set the both new settings to 2 random values,
       and the single value or the sum of the 2 values is greater than 40.
       --> The setting update should fail.
    8. Create a volume, verify everything works as normal

    Note: use fixture to restore the setting into the original state
    """

    instance_managers = client.list_instance_manager()
    deprecated_setting = client.by_id_setting(SETTING_GUARANTEED_ENGINE_CPU)
    with pytest.raises(Exception) as e:
        client.update(deprecated_setting, value="0.1")

    host_node_name = get_self_host_id()
    host_node = client.by_id_node(host_node_name)
    other_ems, other_rms = [], []
    for im in instance_managers:
        if im.managerType == "engine":
            if im.nodeID == host_node_name:
                em_on_host = im
            else:
                other_ems.append(im)
        else:
            if im.nodeID == host_node_name:
                rm_on_host = im
            else:
                other_rms.append(im)
    assert em_on_host and rm_on_host
    host_kb_node = core_api.read_node(host_node_name)
    if host_kb_node.status.allocatable["cpu"].endswith('m'):
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"][:-1])
    else:
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"])*1000

    client.update(host_node, allowScheduling=True,
                  engineManagerCPURequest=150, replicaManagerCPURequest=250)
    time.sleep(5)
    guaranteed_engine_cpu_setting_check(
        client, core_api, [em_on_host], "Running", True, "150m")
    guaranteed_engine_cpu_setting_check(
        client, core_api, [rm_on_host], "Running", True, "250m")

    em_setting = client.by_id_setting(SETTING_GUARANTEED_ENGINE_MANAGER_CPU)
    client.update(em_setting, value="10")
    rm_setting = client.by_id_setting(SETTING_GUARANTEED_REPLICA_MANAGER_CPU)
    client.update(rm_setting, value="20")
    time.sleep(5)
    guaranteed_engine_cpu_setting_check(
        client, core_api, other_ems, "Running", True,
        str(int(allocatable_millicpu*10/100)) + "m")
    guaranteed_engine_cpu_setting_check(
        client, core_api, other_rms, "Running", True,
        str(int(allocatable_millicpu*20/100)) + "m")

    em_setting = client.by_id_setting(SETTING_GUARANTEED_ENGINE_MANAGER_CPU)
    client.update(em_setting, value="0")
    rm_setting = client.by_id_setting(SETTING_GUARANTEED_REPLICA_MANAGER_CPU)
    client.update(rm_setting, value="0")
    time.sleep(5)
    guaranteed_engine_cpu_setting_check(
        client, core_api, other_ems, "Running", True, "")
    guaranteed_engine_cpu_setting_check(
        client, core_api, other_rms, "Running", True, "")

    ems, rms = other_ems, other_rms
    ems.append(em_on_host)
    rms.append(rm_on_host)

    host_node = client.by_id_node(host_node_name)
    client.update(host_node, allowScheduling=True,
                  engineManagerCPURequest=0, replicaManagerCPURequest=0)
    time.sleep(5)
    guaranteed_engine_cpu_setting_check(
        client, core_api, ems, "Running", True, "")
    guaranteed_engine_cpu_setting_check(
        client, core_api, rms, "Running", True, "")

    client.update(em_setting, value="20")
    rm_setting = client.by_id_setting(SETTING_GUARANTEED_REPLICA_MANAGER_CPU)
    client.update(rm_setting, value="15")
    time.sleep(5)
    guaranteed_engine_cpu_setting_check(
        client, core_api, ems, "Running", True,
        str(int(allocatable_millicpu*20/100)) + "m")
    guaranteed_engine_cpu_setting_check(
        client, core_api, rms, "Running", True,
        str(int(allocatable_millicpu*15/100)) + "m")

    with pytest.raises(Exception) as e:
        client.update(em_setting, value="41")
    assert "should be between 0 to 40" in \
           str(e.value)

    em_setting = client.by_id_setting(SETTING_GUARANTEED_ENGINE_MANAGER_CPU)
    with pytest.raises(Exception) as e:
        client.update(em_setting, value="35")
    assert "The sum should not be smaller than 0% or greater than 40%" in \
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


def guaranteed_engine_cpu_setting_check(  # NOQA
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


def test_setting_priority_class(core_api, apps_api, scheduling_api, priority_class, volume_name):  # NOQA
    """
    Test that the Priority Class setting is validated and utilized correctly.

    1. Verify that the name of a non-existent Priority Class cannot be used
    for the Setting.
    2. Create a new Priority Class in Kubernetes.
    3. Create and attach a Volume.
    4. Verify that the Priority Class Setting cannot be updated with an
    attached Volume.
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

    with pytest.raises(Exception) as e:
        client.update(setting, value=name)
    assert 'cannot modify priority class setting before all volumes are ' \
           'detached' in str(e.value)

    data1 = write_volume_random_data(volume)
    check_volume_data(volume, data1)

    volume.detach(hostId="")
    wait_for_volume_detached(client, volume_name)

    setting = client.update(setting, value=name)
    assert setting.value == name

    wait_for_priority_class_update(core_api, apps_api, count, priority_class)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data1)
    data2 = write_volume_random_data(volume)
    check_volume_data(volume, data2)
    volume.detach(hostId="")
    wait_for_volume_detached(client, volume_name)

    setting = client.by_id_setting(SETTING_PRIORITY_CLASS)
    setting = client.update(setting, value='')
    assert setting.value == ''
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


@pytest.mark.skip(reason="TODO")
@pytest.mark.backing_image  # NOQA
def test_setting_backing_image_auto_cleanup():  # NOQA
    """
    Test that the Backing Image Cleanup Wait Interval setting works correctly.

    The default setting value is 60.

    1. Set `BackingImageCleanupWaitInterval` to default value.
    2. Create a backing image.
    3. Create multiple volumes using the backing image.
    4. Attach all volumes, Then:
        1. Wait for all volumes can become running.
        2. Verify the correct in all volumes.
        3. Verify the backing image disk status map.
        4. Verify the only backing image file in each disk is reused by
           multiple replicas. The backing image file path is
           `<Data path>/<The backing image name>/backing`
    5. Decrease the replica count by 1 for all volumes.
    6. Remove all replicas in one disk.
       Wait for 1 minute.
       Then verify nothing changes in the backing image disk state map
       (before the cleanup wait interval is passed).
    7. Modify `BackingImageCleanupWaitInterval` to a small value. Then verify:
        1. The download state of the disk containing no replica becomes
           terminating first, and the entry will be removed from the map later.
        2. The related backing image file is removed.
        3. The download state of other disks keep unchanged.
           All volumes still work fine.
    8. Delete all volumes. Verify that all states in the backing image disk map
       will become terminating first,
       and all entries will be removed from the map later.
    9. Delete the backing image.
    """
