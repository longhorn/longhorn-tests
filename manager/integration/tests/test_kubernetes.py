#!/usr/sbin/python
import pytest
import time

from common import client, core_api, statefulset, storage_class  # NOQA
from common import csi_pv, pvc, pod  # NOQA
from common import get_apps_api_client
from common import create_and_wait_statefulset
from common import update_statefulset_manifests
from common import create_storage_class
from common import get_statefulset_pod_info
from common import check_pod_existence, create_and_wait_pod
from common import delete_and_wait_pod, wait_delete_pod
from common import delete_and_wait_pvc
from common import delete_and_wait_pv, wait_delete_pv
from common import check_pv_existence, check_pvc_existence
from common import wait_for_volume_detached
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import SIZE

from kubernetes import client as k8sclient

Gi = (1 * 1024 * 1024 * 1024)

DEFAULT_STORAGECLASS_NAME = "longhorn-statefulset"
DEFAULT_VOLUME_SIZE = 3  # In Gi


def delete_and_wait_statefulset_only(api, ss):
    pod_data = get_statefulset_pod_info(api, ss)

    apps_api = get_apps_api_client()
    apps_api.delete_namespaced_stateful_set(
        name=ss['metadata']['name'],
        namespace='default', body=k8sclient.V1DeleteOptions())

    for i in range(RETRY_COUNTS):
        ret = apps_api.list_namespaced_stateful_set(namespace='default')
        found = False
        for item in ret.items:
            if item.metadata.name == ss['metadata']['name']:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found

    for p in pod_data:
        wait_delete_pod(api, p['pod_name'])


@pytest.mark.csi  # NOQA
def test_kubernetes_status(client, core_api, storage_class,  # NOQA
                           statefulset, csi_pv, pvc, pod):  # NOQA
    statefulset_name = 'kubernetes-status-test'
    update_statefulset_manifests(statefulset, storage_class, statefulset_name)

    storage_class['reclaimPolicy'] = 'Retain'
    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volume_info = [p['pv_name'] for p in pod_info]

    for p, volume_name in zip(pod_info, volume_info):
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        for i in range(RETRY_COUNTS):
            if k_status['podStatus'] == 'Running':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['podStatus'] == 'Running'
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']

    delete_and_wait_statefulset_only(core_api, statefulset)
    for p, volume_name in zip(pod_info, volume_info):
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'
        assert not k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']

    for p, volume_name in zip(pod_info, volume_info):
        delete_and_wait_pvc(core_api, p['pvc_name'])
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        for i in range(RETRY_COUNTS):
            if k_status['pvStatus'] == 'Released':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['pvStatus'] == 'Released'
        assert k_status['pvName'] == p['pv_name']
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'
        assert k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']

    for p, volume_name in zip(pod_info, volume_info):
        delete_and_wait_pv(core_api, p['pv_name'])
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        assert k_status['pvName'] == ''
        assert k_status['pvStatus'] == ''
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'
        assert k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']

    # reuse that volume
    for p, volume_name in zip(pod_info, volume_info):
        p['pod_name'] = p['pod_name'].replace('kubernetes-status-test',
                                              'kubernetes-status-test-reuse')
        p['pvc_name'] = p['pvc_name'].replace('kubernetes-status-test',
                                              'kubernetes-status-test-reuse')
        p['pv_name'] = p['pvc_name']

        csi_pv['metadata']['name'] = p['pv_name']
        csi_pv['spec']['csi']['volumeHandle'] = volume_name
        core_api.create_persistent_volume(csi_pv)

        pvc['metadata']['name'] = p['pvc_name']
        pvc['spec']['volumeName'] = p['pv_name']
        core_api.create_namespaced_persistent_volume_claim(
            body=pvc, namespace='default')

        pod['metadata']['name'] = p['pod_name']
        pod['spec']['volumes'] = [{
            'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
            'persistentVolumeClaim': {
                'claimName': p['pvc_name'],
            },
        }]
        create_and_wait_pod(core_api, pod)

        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        assert k_status['pvName'] == p['pv_name']
        for i in range(RETRY_COUNTS):
            if k_status['pvStatus'] == 'Bound':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['pvStatus'] == 'Bound'
        for i in range(RETRY_COUNTS):
            if k_status['podStatus'] == 'Running':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['podStatus'] == 'Running'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert not k_status['workloadName']
        assert not k_status['workloadType']
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']

        delete_and_wait_pod(core_api, p['pod_name'])
        # Since persistentVolumeReclaimPolicy of csi_pv is `Delete`,
        # we don't need to delete bounded pv manually
        delete_and_wait_pvc(core_api, p['pvc_name'])
        wait_delete_pv(core_api, p['pv_name'])


@pytest.mark.csi  # NOQA
def test_kubernetes_status_pod_deletion(client, core_api, storage_class,  # NOQA
                                        statefulset, csi_pv, pvc, pod):  # NOQA
    statefulset_name = 'kubernetes-status-pod-deletion-test'
    update_statefulset_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volume_info = [p['pv_name'] for p in pod_info]

    for p, volume_name in zip(pod_info, volume_info):
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        for i in range(RETRY_COUNTS):
            if k_status['podStatus'] == 'Running':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['podStatus'] == 'Running'
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['podName'] == p['pod_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']

    for p in pod_info:
        core_api.delete_namespaced_pod(name=p['pod_name'], namespace='default',
                                       body=k8sclient.V1DeleteOptions())
        # wait for pod recreation
        for i in range(RETRY_COUNTS):
            found = False
            if check_pod_existence(core_api, p['pod_name']):
                found = True
                break
            time.sleep(RETRY_INTERVAL)
        assert found

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volume_info = [p['pv_name'] for p in pod_info]

    for p, volume_name in zip(pod_info, volume_info):
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        for i in range(RETRY_COUNTS):
            if k_status['podStatus'] == 'Pending':
                assert not k_status['lastPVCRefAt']
                assert not k_status['lastPodRefAt']
            if k_status['podStatus'] == 'Running':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
        assert k_status['podStatus'] == 'Running'
        assert k_status['podName'] == p['pod_name']
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['workloadName'] == statefulset_name
        assert k_status['workloadType'] == 'StatefulSet'


@pytest.mark.csi  # NOQA
def test_pv_creation(client, core_api):  # NOQA
    volume_name = "test-pv-creation"
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pv_name = "pv-" + volume_name

    volume.pvCreate(pvName=pv_name)
    for i in range(RETRY_COUNTS):
        if check_pv_existence(core_api, pv_name):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pv_existence(core_api, pv_name)

    volume = client.by_id_volume(volume_name)
    k_status = volume["kubernetesStatus"]
    for i in range(RETRY_COUNTS):
        if k_status['pvName'] and k_status['pvStatus'] == 'Available':
            break
        time.sleep(RETRY_INTERVAL)
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Available'
    assert not k_status['namespace']
    assert not k_status['pvcName']
    assert not k_status['lastPVCRefAt']
    assert not k_status['podName']
    assert not k_status['podStatus']
    assert not k_status['workloadName']
    assert not k_status['workloadType']
    assert not k_status['lastPodRefAt']

    # try to create one more pv for the volume
    pv_name_2 = "pv2-" + volume_name
    with pytest.raises(Exception) as e:
        volume.pvCreate(pvName=pv_name_2)
        assert "already exist" in str(e.value)

    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Available'
    assert not k_status['namespace']
    assert not k_status['pvcName']
    assert not k_status['lastPVCRefAt']
    assert not k_status['podName']
    assert not k_status['podStatus']
    assert not k_status['workloadName']
    assert not k_status['workloadType']
    assert not k_status['lastPodRefAt']

    delete_and_wait_pv(core_api, pv_name)


@pytest.mark.csi  # NOQA
def test_pvc_creation(client, core_api, pod):  # NOQA
    volume_name = "test-pvc-creation"
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pv_name = "pv-" + volume_name
    pvc_name = "pvc-" + volume_name
    pod_name = "pod-" + volume_name

    # try to create pvc without pv for the volume
    with pytest.raises(Exception) as e:
        volume.pvcCreate(namespace="default", pvcName=pvc_name)
        assert "connot find existing PV for volume" in str(e.value)

    volume.pvCreate(pvName=pv_name)
    for i in range(RETRY_COUNTS):
        if check_pv_existence(core_api, pv_name):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pv_existence(core_api, pv_name)

    volume = client.by_id_volume(volume_name)
    k_status = volume["kubernetesStatus"]
    for i in range(RETRY_COUNTS):
        if k_status['pvName'] and k_status['pvStatus'] == 'Available':
            break
        time.sleep(RETRY_INTERVAL)
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Available'
    assert not k_status['namespace']
    assert not k_status['pvcName']
    assert not k_status['lastPVCRefAt']
    assert not k_status['podName']
    assert not k_status['podStatus']
    assert not k_status['workloadName']
    assert not k_status['workloadType']
    assert not k_status['lastPodRefAt']

    volume.pvcCreate(namespace="default", pvcName=pvc_name)
    for i in range(RETRY_COUNTS):
        if check_pvc_existence(core_api, pvc_name):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pvc_existence(core_api, pvc_name)

    volume = client.by_id_volume(volume_name)
    k_status = volume["kubernetesStatus"]
    for i in range(RETRY_COUNTS):
        if k_status['pvcName'] and k_status['namespace']:
            break
        time.sleep(RETRY_INTERVAL)
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Bound'
    assert k_status['namespace'] == "default"
    assert k_status['pvcName'] == pvc_name
    assert not k_status['lastPVCRefAt']
    assert not k_status['podName']
    assert not k_status['podStatus']
    assert not k_status['workloadName']
    assert not k_status['workloadType']
    assert not k_status['lastPodRefAt']

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    volume = client.by_id_volume(volume_name)
    k_status = volume["kubernetesStatus"]
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Bound'
    for i in range(RETRY_COUNTS):
        if k_status['podStatus'] == 'Running':
            break
        time.sleep(RETRY_INTERVAL)
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
    assert k_status['podName'] == pod_name
    assert k_status['podStatus'] == 'Running'
    assert k_status['namespace'] == 'default'
    assert k_status['pvcName'] == pvc_name
    assert not k_status['workloadName']
    assert not k_status['workloadType']
    assert not k_status['lastPVCRefAt']
    assert not k_status['lastPodRefAt']

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    wait_delete_pv(core_api, pv_name)
