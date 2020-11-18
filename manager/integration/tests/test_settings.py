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

    LONGHORN_NAMESPACE, SETTING_TAINT_TOLERATION,
    RETRY_COUNTS, RETRY_INTERVAL_LONG, SETTING_GUARANTEED_ENGINE_CPU,
    SETTING_PRIORITY_CLASS, SIZE, RETRY_INTERVAL
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
    if images[0].state != "ready":
        return False

    return True


def wait_for_longhorn_node_ready():
    client = get_longhorn_api_client()  # NOQA

    ei = get_default_engine_image(client)
    ei_name = ei["name"]

    wait_for_engine_image_state(client, ei_name, "ready")

    node = get_self_host_id()
    wait_for_node_up_longhorn(node, client)

    return client, node


def test_setting_toleration():
    """
    Test toleration setting

    1. Verify that cannot use Kubernetes tolerations for Longhorn setting
    2. Use "key1=value1:NoSchedule; key2:NoExecute" as toleration.
    3. Create a volume and attach it.
    4. Verify that cannot update toleration setting when any volume is attached
    5. Generate and write `data1` into the volume
    6. Detach the volume.
    7. Update setting `toleration` to toleration.
    8. Wait for all the Longhorn components to restart with new toleration
    9. Attach the volume again and verify the volume `data1`.
    10. Generate and write `data2` to the volume.
    11. Detach the volume.
    12. Clean the `toleration` setting.
    13. Wait for all the Longhorn components to restart with no toleration
    14. Attach the volume and validate `data2`.
    15. Generate and write `data3` to the volume.
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
    setting_value_dict = \
        {"key1": {"key": "key1", "value": "value1",
                  "operator": "Equal", "effect": "NoSchedule"},
         "key2": {"key": "key2", "value": None,
                  "operator": "Exists", "effect": "NoExecute"}, }

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

    volume.detach()
    wait_for_volume_detached(client, volume_name)

    setting = client.update(setting, value=setting_value_str)
    assert setting.value == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dict)

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
    setting_value_dict = {}
    setting = client.by_id_setting(SETTING_TAINT_TOLERATION)
    setting = client.update(setting, value=setting_value_str)
    assert setting.value == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dict)

    client, node = wait_for_longhorn_node_ready()

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data2)
    data3 = write_volume_random_data(volume)
    check_volume_data(volume, data3)

    cleanup_volume(client, volume)


@pytest.mark.skip(reason="TODO") # NOQA
def test_setting_toleration_extra():
    """
    Steps:
    1. Set Kubernetes Taint Toleration to:
       `example.com/foobar:NoExecute;example.com/foobar:NoSchedule`
    2. Verify that all components have the 2 tolerations
       `example.com/foobar:NoExecute; example.com/foobar:NoSchedule`
    3. Set Kubernetes Taint Toleration to:
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
    4. Verify that all components have the the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
       and don't have the 2 tolerations
       `example.com/foobar:NoExecute;example.com/foobar:NoSchedule`
    5. Set Kubernetes Taint Toleration to special value:
       `:`
    6. Verify that all components have the toleration with
       `operator: Exists` and other field of the toleration are empty.
       Verify that all components don't have the toleration
       `node-role.kubernetes.io/controlplane=true:NoSchedule`
    7. Clear Kubernetes Taint Toleration

    Note: `components` in this context is referring to all deployments,
       daemonsets, IM pods, recurring jobs in Longhorn system
    """
    pass


def wait_for_toleration_update(core_api, apps_api, count, set_tolerations):  # NOQA
    updated = False

    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL_LONG)
        updated = True

        if not check_workload_update(core_api, apps_api, count):
            updated = False
            continue

        pod_list = core_api.list_namespaced_pod(LONGHORN_NAMESPACE).items
        for p in pod_list:
            if p.status.phase != "Running" or \
                    not check_tolerations_set(p.spec.tolerations,
                                              set_tolerations):
                updated = False
                break
        if not updated:
            continue

        if updated:
            break

    assert updated


def check_tolerations_set(current_toleration_list, set_tolerations):
    current_tolerations = dict()
    for t in current_toleration_list:
        if KUBERNETES_DEFAULT_TOLERATION not in t.key:
            current_tolerations[t.key] = \
                {"key": t.key, "value": t.value,
                 "operator": t.operator, "effect": t.effect}

    return current_tolerations == set_tolerations


def test_setting_guaranteed_engine_cpu(client, core_api):  # NOQA
    """
    Test setting Guaranteed Engine CPU

    Notice any change of the setting will result in all the instance manager
    recreated, no matter if there is any volume attached or not.

    1. Change the setting to `xxx`. Update setting should fail.
    2. Change the setting to `0.1`
    3. Wait for all the IM pods to recreated and become running
    4. Verify every IM pod has guaranteed CPU set correctly to 100m
    5. Change the setting to `0`
    6. Wait for all the IM pods to recreated and become running
    7. Verify every IM pod no longer has guaranteed CPU set
    8. Change the setting to `200m`
    9. Wait for all the IM pods to recreated and become running
    10. Verify every IM pod has guaranteed CPU set to 200m
    11. Change the setting to `10`, means 10 vcpus
    12. Wait for all the IM pods to recreated but unable to run
    13. Verify no IM pod can become running, with guaranteed CPU set to 10
    14. Change the setting to `0.25`
    15. Wait for all the IM pods to recreated and become running
    16. Verify every IM pod has guaranteed CPU set to 250m
    17. Create a volume, verify everything works as normal

    Note: use fixture to restore the setting into the original state
    """
    # Get current guaranteed engine cpu setting and save it to org_setting
    setting = client.by_id_setting(SETTING_GUARANTEED_ENGINE_CPU)

    # Get current running instance managers
    instance_managers = client.list_instance_manager()

    # Set an invalid value, and it should return error
    with pytest.raises(Exception) as e:
        client.update(setting, value="xxx")
    assert "with invalid " + SETTING_GUARANTEED_ENGINE_CPU in \
           str(e.value)

    # Update guaranteed engine cpu setting to 0.1
    guaranteed_engine_cpu_setting_check(client, core_api, setting, "0.1",
                                        "100m", instance_managers,
                                        "Running", True)

    # Update guaranteed engine cpu setting to 0
    guaranteed_engine_cpu_setting_check(client, core_api, setting, "0",
                                        None, instance_managers,
                                        "Running", True)

    # Update guaranteed engine cpu setting to 200m
    guaranteed_engine_cpu_setting_check(client, core_api, setting, "200m",
                                        "200m", instance_managers,
                                        "Running", True)

    # Update guaranteed engine cpu setting to 10
    guaranteed_engine_cpu_setting_check(client, core_api, setting, "10",
                                        None, instance_managers,
                                        "Running", False)

    # Update guaranteed engine cpu setting to 0.25
    guaranteed_engine_cpu_setting_check(client, core_api, setting, "0.25",
                                        "250m", instance_managers,
                                        "Running", True)

    # Create a volume to test
    vol_name = generate_volume_name()
    volume = create_and_check_volume(client, vol_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, vol_name)
    assert len(volume.replicas) == 3

    data = write_volume_random_data(volume)
    check_volume_data(volume, data)


def guaranteed_engine_cpu_setting_check(client, core_api, setting,  # NOQA
                                        val, cpu_val,  # NOQA
                                        instance_managers,  # NOQA
                                        state, desire):  # NOQA
    """
    We check if instance managers are in the desired state with
    correct setting
    desire is for reflect the state we are looking for.
    If desire is True, meanning we need the state to be the same.
    Otherwise, we are looking for the state to be different.
    e.g. 'Pending', 'OutofCPU', 'Terminating' they are all 'Not Running'.
    """
    # Update guaranteed engine cpu setting
    client.update(setting, value=val)

    # Give sometime to k8s to update the instance manager status
    time.sleep(6 * RETRY_INTERVAL)

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
    8. Wait for all the Longhorn workloads to restart with the new Priority
    Class.
    9. Attach the Volume and verify `data1`.
    10. Generate and write `data2`.
    11. Unset the Priority Class Setting.
    12. Wait for all the Longhorn workloads to restart with the new Priority
    Class.
    13. Attach the Volume and verify `data2`.
    14. Generate and write `data3`.
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

    volume.detach()
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
    volume.detach()
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
