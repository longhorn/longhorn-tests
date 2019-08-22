import time
import pytest

from common import (  # NOQA
    get_longhorn_api_client, get_self_host_id,
    get_core_api_client, get_apps_api_client,
    create_and_check_volume, wait_for_volume_healthy,
    cleanup_volume,

    LONGHORN_NAMESPACE, SETTING_TAINT_TOLERATION,
    RETRY_COUNTS, RETRY_INTERVAL_LONG,
)

KUBERNETES_DEFAULT_TOLERATION = "kubernetes.io"


def test_toleration_setting():
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
                      value="key1=value1:NoSchedule, key2:InvalidEffect")
    assert 'invalid effect' in str(e.value)

    setting_value_str = "key1=value1:NoSchedule, key2:NoExecute"
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
    cleanup_volume(client, volume)

    setting = client.update(setting, value=setting_value_str)
    assert setting["value"] == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dict)

    # cleanup
    new_client = get_longhorn_api_client()
    setting_value_str = ""
    setting_value_dict = {}
    setting = new_client.by_id_setting(SETTING_TAINT_TOLERATION)
    setting = new_client.update(setting, value=setting_value_str)
    assert setting["value"] == setting_value_str
    wait_for_toleration_update(core_api, apps_api, count, setting_value_dict)


def wait_for_toleration_update(core_api, apps_api, count, set_tolerations):  # NOQA
    updated = False

    for i in range(RETRY_COUNTS):
        da_list = apps_api.list_namespaced_daemon_set(LONGHORN_NAMESPACE).items
        for da in da_list:
            if da.status.updated_number_scheduled != count:
                time.sleep(RETRY_INTERVAL_LONG)
                continue

        dp_list = apps_api.list_namespaced_deployment(LONGHORN_NAMESPACE).items
        for dp in dp_list:
            if dp.status.updated_replicas != dp.spec.replicas:
                time.sleep(RETRY_INTERVAL_LONG)
                continue

        im_pod_list = core_api.list_namespaced_pod(
            LONGHORN_NAMESPACE, label_selector="app=instance-manager").items
        if len(im_pod_list) != 2 * count:
            time.sleep(RETRY_INTERVAL_LONG)
            continue
        for p in im_pod_list:
            if p.status.phase != "Running":
                time.sleep(RETRY_INTERVAL_LONG)
            continue

        updated = True
        pod_list = core_api.list_namespaced_pod(LONGHORN_NAMESPACE).items
        for p in pod_list:
            if p.status.phase != "Running" or \
                    not check_tolerations_set(p.spec.tolerations,
                                              set_tolerations):
                updated = False
                break
        if not updated:
            time.sleep(RETRY_INTERVAL_LONG)
            continue

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
