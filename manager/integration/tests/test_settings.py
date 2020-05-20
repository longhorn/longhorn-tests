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

    LONGHORN_NAMESPACE, SETTING_TAINT_TOLERATION,
    RETRY_COUNTS, RETRY_INTERVAL_LONG,
)

from test_infra import wait_for_node_up_longhorn

KUBERNETES_DEFAULT_TOLERATION = "kubernetes.io"


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
    client = get_longhorn_api_client()
    apps_api = get_apps_api_client()
    core_api = get_core_api_client()
    count = len(client.list_node())

    setting = client.by_id_setting(SETTING_TAINT_TOLERATION)

    with pytest.raises(Exception) as e:
        client.update(setting,
                      value=KUBERNETES_DEFAULT_TOLERATION + ":NoSchedule")
    assert "is considered as the key of Kubernetes default tolerations" \
           in str(e.value)
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

    volume_name = "test-toleration-vol"
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

    client = get_longhorn_api_client()

    ei = get_default_engine_image(client)
    ei_name = ei["name"]

    wait_for_engine_image_state(client, ei_name, "ready")
    volume = client.by_id_volume(volume_name)

    node = get_self_host_id()
    wait_for_node_up_longhorn(node, client)

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

    client = get_longhorn_api_client()

    ei = get_default_engine_image(client)
    ei_name = ei["name"]

    wait_for_engine_image_state(client, ei_name, "ready")

    node = get_self_host_id()
    wait_for_node_up_longhorn(node, client)

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=node)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_data(volume, data2)
    data3 = write_volume_random_data(volume)
    check_volume_data(volume, data3)

    cleanup_volume(client, volume)


def wait_for_toleration_update(core_api, apps_api, count, set_tolerations):  # NOQA
    updated = False

    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL_LONG)
        updated = True

        da_list = apps_api.list_namespaced_daemon_set(LONGHORN_NAMESPACE).items
        for da in da_list:
            if da.status.updated_number_scheduled != count:
                updated = False
                break
        if not updated:
            continue

        dp_list = apps_api.list_namespaced_deployment(LONGHORN_NAMESPACE).items
        for dp in dp_list:
            if dp.status.updated_replicas != dp.spec.replicas:
                updated = False
                break
        if not updated:
            continue

        im_pod_list = core_api.list_namespaced_pod(
            LONGHORN_NAMESPACE,
            label_selector="longhorn.io/component=instance-manager").items
        if len(im_pod_list) != 2 * count:
            updated = False
            continue

        for p in im_pod_list:
            if p.status.phase != "Running":
                updated = False
                break
        if not updated:
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

        client = get_longhorn_api_client()
        images = client.list_engine_image()
        assert len(images) == 1
        if images[0].state != "ready":
            updated = False
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


@pytest.mark.skip(reason="TODO")
def test_setting_guaranteed_engine_cpu():
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
    pass
