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
from common import create_and_wait_pod
from common import delete_and_wait_pod, wait_delete_pod
from common import delete_and_wait_pvc
from common import delete_and_wait_pv, wait_delete_pv
from common import create_pv_for_volume, create_pvc_for_volume
from common import wait_for_volume_detached
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import SIZE

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

Gi = (1 * 1024 * 1024 * 1024)

DEFAULT_STORAGECLASS_NAME = "longhorn-statefulset"
DEFAULT_VOLUME_SIZE = 3  # In Gi


def delete_and_wait_statefulset_only(api, ss):
    pod_data = get_statefulset_pod_info(api, ss)

    apps_api = get_apps_api_client()
    try:
        apps_api.delete_namespaced_stateful_set(
            name=ss['metadata']['name'],
            namespace='default', body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

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

    extra_pod_name = 'extra-pod-using-' + volume_info[1]
    pod['metadata']['name'] = extra_pod_name
    p2 = core_api.read_namespaced_pod(name=pod_info[1]['pod_name'],
                                      namespace='default')
    pod['spec']['nodeName'] = p2.spec.node_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': pod_info[1]['pvc_name'],
        },
    }]
    create_and_wait_pod(core_api, pod)

    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']
        if i == 0:
            assert len(workloads) == 1
            assert workloads[0]['podName'] == p['pod_name']
            assert workloads[0]['workloadName'] == statefulset_name
            assert workloads[0]['workloadType'] == 'StatefulSet'
            for _ in range(RETRY_COUNTS):
                if workloads[0]['podStatus'] == 'Running':
                    break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
            workloads = k_status['workloadsStatus']
            assert workloads[0]['podStatus'] == 'Running'
        if i == 1:
            assert len(k_status['workloadsStatus']) == 2
            if workloads[0]['podName'] == pod_info[i]['pod_name']:
                assert workloads[1]['podName'] == extra_pod_name
                assert workloads[0]['workloadName'] == statefulset_name
                assert workloads[0]['workloadType'] == 'StatefulSet'
                assert not workloads[1]['workloadName']
                assert not workloads[1]['workloadType']
            else:
                assert workloads[1]['podName'] == pod_info[i]['pod_name']
                assert workloads[0]['podName'] == extra_pod_name
                assert not workloads[0]['workloadName']
                assert not workloads[0]['workloadType']
                assert workloads[1]['workloadName'] == statefulset_name
                assert workloads[1]['workloadType'] == 'StatefulSet'
            for _ in range(RETRY_COUNTS):
                if workloads[0]['podStatus'] == 'Running' and \
                        workloads[1]['podStatus'] == 'Running':
                    break
                time.sleep(RETRY_INTERVAL)
                volume = client.by_id_volume(volume_name)
                k_status = volume["kubernetesStatus"]
                workloads = k_status['workloadsStatus']
                assert len(workloads) == 2
            assert workloads[0]['podStatus'] == 'Running'
            assert workloads[1]['podStatus'] == 'Running'

    # the extra pod is still using the 2nd volume
    delete_and_wait_statefulset_only(core_api, statefulset)
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert not k_status['lastPVCRefAt']
        assert len(workloads) == 1
        if i == 0:
            assert workloads[0]['podName'] == p['pod_name']
            assert workloads[0]['workloadName'] == statefulset_name
            assert workloads[0]['workloadType'] == 'StatefulSet'
            assert k_status['lastPodRefAt']
        if i == 1:
            assert workloads[0]['podName'] == extra_pod_name
            assert not workloads[0]['workloadName']
            assert not workloads[0]['workloadType']
            assert not k_status['lastPodRefAt']

    # deleted extra_pod, all volumes have no workload
    delete_and_wait_pod(core_api, pod['metadata']['name'])
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Bound'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert not k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']
        assert len(workloads) == 1
        if i == 0:
            assert workloads[0]['podName'] == p['pod_name']
            assert workloads[0]['workloadName'] == statefulset_name
            assert workloads[0]['workloadType'] == 'StatefulSet'
        if i == 1:
            assert workloads[0]['podName'] == extra_pod_name
            assert not workloads[0]['workloadName']
            assert not workloads[0]['workloadType']

    # deleted pvc only.
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        delete_and_wait_pvc(core_api, p['pvc_name'])
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        for _ in range(RETRY_COUNTS):
            if k_status['pvStatus'] == 'Released':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
            workloads = k_status['workloadsStatus']
        assert k_status['pvName'] == p['pv_name']
        assert k_status['pvStatus'] == 'Released'
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']
        assert len(workloads) == 1
        if i == 0:
            assert workloads[0]['podName'] == p['pod_name']
            assert workloads[0]['workloadName'] == statefulset_name
            assert workloads[0]['workloadType'] == 'StatefulSet'
        if i == 1:
            assert workloads[0]['podName'] == extra_pod_name
            assert not workloads[0]['workloadName']
            assert not workloads[0]['workloadType']

    # deleted pv only.
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        delete_and_wait_pv(core_api, p['pv_name'])
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert k_status['pvName'] == ''
        assert k_status['pvStatus'] == ''
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert k_status['lastPVCRefAt']
        assert k_status['lastPodRefAt']
        assert len(workloads) == 1
        if i == 0:
            assert workloads[0]['podName'] == p['pod_name']
            assert workloads[0]['workloadName'] == statefulset_name
            assert workloads[0]['workloadType'] == 'StatefulSet'
        if i == 1:
            assert workloads[0]['podName'] == extra_pod_name
            assert not workloads[0]['workloadName']
            assert not workloads[0]['workloadType']

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
        workloads = k_status['workloadsStatus']
        assert len(workloads) == 1
        assert k_status['pvName'] == p['pv_name']
        for _ in range(RETRY_COUNTS):
            if k_status['pvStatus'] == 'Bound':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
            workloads = k_status['workloadsStatus']
            assert len(workloads) == 1
        assert k_status['pvStatus'] == 'Bound'
        for _ in range(RETRY_COUNTS):
            if workloads[0]['podStatus'] == 'Running':
                break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume["kubernetesStatus"]
            workloads = k_status['workloadsStatus']
            assert len(workloads) == 1
        assert workloads[0]['podStatus'] == 'Running'
        assert workloads[0]['podName'] == p['pod_name']
        assert not workloads[0]['workloadName']
        assert not workloads[0]['workloadType']
        assert k_status['namespace'] == 'default'
        assert k_status['pvcName'] == p['pvc_name']
        assert not k_status['lastPVCRefAt']
        assert not k_status['lastPodRefAt']

        delete_and_wait_pod(core_api, p['pod_name'])
        # Since persistentVolumeReclaimPolicy of csi_pv is `Delete`,
        # we don't need to delete bounded pv manually
        delete_and_wait_pvc(core_api, p['pvc_name'])
        wait_delete_pv(core_api, p['pv_name'])


@pytest.mark.csi  # NOQA
def test_pv_creation(client, core_api):  # NOQA
    volume_name = "test-pv-creation"
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pv_name = "pv-" + volume_name
    create_pv_for_volume(client, core_api, volume, pv_name)

    # try to create one more pv for the volume
    pv_name_2 = "pv2-" + volume_name
    with pytest.raises(Exception) as e:
        volume.pvCreate(pvName=pv_name_2)
        assert "already exist" in str(e.value)

    volume = client.by_id_volume(volume_name)
    k_status = volume["kubernetesStatus"]
    workloads = k_status['workloadsStatus']
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Available'
    assert not k_status['namespace']
    assert not k_status['pvcName']
    assert not workloads
    assert not k_status['lastPVCRefAt']
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

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

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
    workloads = k_status['workloadsStatus']
    assert k_status['pvName'] == pv_name
    assert k_status['pvStatus'] == 'Bound'
    assert len(workloads) == 1
    for i in range(RETRY_COUNTS):
        if workloads[0]['podStatus'] == 'Running':
            break
        time.sleep(RETRY_INTERVAL)
        volume = client.by_id_volume(volume_name)
        k_status = volume["kubernetesStatus"]
        workloads = k_status['workloadsStatus']
        assert len(workloads) == 1
    assert workloads[0]['podName'] == pod_name
    assert workloads[0]['podStatus'] == 'Running'
    assert not workloads[0]['workloadName']
    assert not workloads[0]['workloadType']
    assert k_status['namespace'] == 'default'
    assert k_status['pvcName'] == pvc_name
    assert not k_status['lastPVCRefAt']
    assert not k_status['lastPodRefAt']

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    wait_delete_pv(core_api, pv_name)
