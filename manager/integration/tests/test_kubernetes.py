import pytest
import time

from common import client, core_api, statefulset, storage_class  # NOQA
from common import csi_pv, pvc, pod  # NOQA
from common import generate_volume_name, get_apps_api_client
from common import create_and_wait_statefulset
from common import update_statefulset_manifests
from common import create_storage_class, delete_storage_class, \
    find_backup
from common import get_self_host_id, get_statefulset_pod_info
from common import create_and_wait_pod
from common import delete_and_wait_pod, wait_delete_pod
from common import delete_and_wait_pvc
from common import delete_and_wait_pv, wait_delete_pv
from common import cleanup_volume, create_pv_for_volume, create_pvc_for_volume
from common import wait_for_volume_delete, wait_for_volume_detached, \
    wait_for_volume_healthy
from common import wait_volume_kubernetes_status, \
    wait_for_volume_restoration_completed
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import SIZE
from common import KUBERNETES_STATUS_LABEL, SETTING_DEFAULT_LONGHORN_STATIC_SC
from common import DEFAULT_LONGHORN_STATIC_STORAGECLASS_NAME
from common import create_snapshot
from common import set_random_backupstore

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

from json import loads

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
        k_status = volume.kubernetesStatus
        workloads = k_status.workloadsStatus
        assert k_status.pvName == p['pv_name']
        assert k_status.pvStatus == 'Bound'
        assert k_status.namespace == 'default'
        assert k_status.pvcName == p['pvc_name']
        assert not k_status.lastPVCRefAt
        assert not k_status.lastPodRefAt
        if i == 0:
            assert len(workloads) == 1
            assert workloads[0].podName == p['pod_name']
            assert workloads[0].workloadName == statefulset_name
            assert workloads[0].workloadType == 'StatefulSet'
            for _ in range(RETRY_COUNTS):
                if workloads[0].podStatus == 'Running':
                    break
            time.sleep(RETRY_INTERVAL)
            volume = client.by_id_volume(volume_name)
            k_status = volume.kubernetesStatus
            workloads = k_status.workloadsStatus
            assert workloads[0].podStatus == 'Running'
        if i == 1:
            assert len(k_status.workloadsStatus) == 2
            if workloads[0].podName == pod_info[i]['pod_name']:
                assert workloads[1].podName == extra_pod_name
                assert workloads[0].workloadName == statefulset_name
                assert workloads[0].workloadType == 'StatefulSet'
                assert not workloads[1].workloadName
                assert not workloads[1].workloadType
            else:
                assert workloads[1].podName == pod_info[i]['pod_name']
                assert workloads[0].podName == extra_pod_name
                assert not workloads[0].workloadName
                assert not workloads[0].workloadType
                assert workloads[1].workloadName == statefulset_name
                assert workloads[1].workloadType == 'StatefulSet'
            for _ in range(RETRY_COUNTS):
                if workloads[0].podStatus == 'Running' and \
                        workloads[1].podStatus == 'Running':
                    break
                time.sleep(RETRY_INTERVAL)
                volume = client.by_id_volume(volume_name)
                k_status = volume.kubernetesStatus
                workloads = k_status.workloadsStatus
                assert len(workloads) == 2
            assert workloads[0].podStatus == 'Running'
            assert workloads[1].podStatus == 'Running'

    ks_list = [{}, {}]
    delete_and_wait_statefulset_only(core_api, statefulset)
    # the extra pod is still using the 2nd volume
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        ks_list[i]['pvName'] = p['pv_name']
        ks_list[i]['pvStatus'] = 'Bound'
        ks_list[i]['namespace'] = 'default'
        ks_list[i]['pvcName'] = p['pvc_name']
        ks_list[i]['lastPVCRefAt'] = ''
        if i == 0:
            ks_list[i]['lastPodRefAt'] = 'not empty'
            ks_list[i]['workloadsStatus'] = [
                {
                    'podName': p['pod_name'],
                    'podStatus': 'Running',
                    'workloadName': statefulset_name,
                    'workloadType': 'StatefulSet',
                },
            ]
        if i == 1:
            ks_list[i]['lastPodRefAt'] = ''
            ks_list[i]['workloadsStatus'] = [
                {
                    'podName': extra_pod_name,
                    'podStatus': 'Running',
                    'workloadName': '',
                    'workloadType': '',
                }
            ]
        wait_volume_kubernetes_status(client, volume_name, ks_list[i])

    # deleted extra_pod, all volumes have no workload
    delete_and_wait_pod(core_api, pod['metadata']['name'])
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        ks_list[i]['lastPodRefAt'] = 'not empty'
        wait_volume_kubernetes_status(client, volume_name, ks_list[i])

    # deleted pvc only.
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        delete_and_wait_pvc(core_api, p['pvc_name'])
        ks_list[i]['pvStatus'] = 'Released'
        ks_list[i]['lastPVCRefAt'] = 'not empty'
        wait_volume_kubernetes_status(client, volume_name, ks_list[i])

    # deleted pv only.
    for i in range(len(volume_info)):
        p, volume_name = pod_info[i], volume_info[i]
        delete_and_wait_pv(core_api, p['pv_name'])
        ks_list[i]['pvName'] = ''
        ks_list[i]['pvStatus'] = ''
        wait_volume_kubernetes_status(client, volume_name, ks_list[i])

    # reuse that volume
    for p, volume_name in zip(pod_info, volume_info):
        p['pod_name'] = p['pod_name'].replace('kubernetes-status-test',
                                              'kubernetes-status-test-reuse')
        p['pvc_name'] = p['pvc_name'].replace('kubernetes-status-test',
                                              'kubernetes-status-test-reuse')
        p['pv_name'] = p['pvc_name']

        csi_pv['metadata']['name'] = p['pv_name']
        csi_pv['spec']['csi']['volumeHandle'] = volume_name
        csi_pv['spec']['storageClassName'] = \
            DEFAULT_LONGHORN_STATIC_STORAGECLASS_NAME
        core_api.create_persistent_volume(csi_pv)

        pvc['metadata']['name'] = p['pvc_name']
        pvc['spec']['volumeName'] = p['pv_name']
        pvc['spec']['storageClassName'] = \
            DEFAULT_LONGHORN_STATIC_STORAGECLASS_NAME
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

        ks = {
            'pvName': p['pv_name'],
            'pvStatus': 'Bound',
            'namespace': 'default',
            'pvcName': p['pvc_name'],
            'lastPVCRefAt': '',
            'lastPodRefAt': '',
            'workloadsStatus': [{
                'podName': p['pod_name'],
                'podStatus': 'Running',
                'workloadName': '',
                'workloadType': '',
            }, ],
        }
        wait_volume_kubernetes_status(client, volume_name, ks)

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

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Available',
        'namespace': '',
        'pvcName': '',
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    delete_and_wait_pv(core_api, pv_name)


@pytest.mark.csi  # NOQA
def test_pvc_creation_with_default_sc_set(
        client, core_api, storage_class, pod):  # NOQA
    # set default storage class
    storage_class['metadata']['annotations'] = \
        {"storageclass.kubernetes.io/is-default-class": "true"}
    create_storage_class(storage_class)

    static_sc_name = "longhorn-static-test"
    setting = client.by_id_setting(SETTING_DEFAULT_LONGHORN_STATIC_SC)
    setting = client.update(setting, value=static_sc_name)
    assert setting.value == static_sc_name

    volume_name = "test-pvc-creation-with-sc"
    pod_name = "pod-" + volume_name
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pv_name = "pv-" + volume_name
    pvc_name = "pvc-" + volume_name
    pvc_name_extra = "pvc-" + volume_name + "-extra"

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    ret = core_api.list_namespaced_persistent_volume_claim(
        namespace='default')
    for item in ret.items:
        if item.metadata.name == pvc_name:
            pvc_found = item
            break
    assert pvc_found
    assert pvc_found.spec.storage_class_name == static_sc_name

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Bound',
        'namespace': 'default',
        'pvcName': pvc_name,
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
        'workloadsStatus': [{
            'podName': pod_name,
            'podStatus': 'Running',
            'workloadName': '',
            'workloadType': '',
        }, ],
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)

    # try to reuse the pv
    volume = wait_for_volume_detached(client, volume_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name_extra)
    pod['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = \
        pvc_name_extra
    create_and_wait_pod(core_api, pod)

    ks['pvcName'] = pvc_name_extra
    wait_volume_kubernetes_status(client, volume_name, ks)

    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name_extra)
    delete_and_wait_pv(core_api, pv_name)

    # without default storage class
    delete_storage_class(storage_class['metadata']['name'])

    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    ret = core_api.list_namespaced_persistent_volume_claim(
        namespace='default')
    for item in ret.items:
        if item.metadata.name == pvc_name:
            pvc2 = item
            break
    assert pvc2
    assert pvc2.spec.storage_class_name == static_sc_name

    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)


@pytest.mark.csi
def test_backup_kubernetes_status(client, core_api, pod):  # NOQA
    """
    Test that Backups have KubernetesStatus stored properly when there is an
    associated PersistentVolumeClaim and Pod.
    """
    set_random_backupstore(client)

    host_id = get_self_host_id()
    static_sc_name = "longhorn-static-test"
    setting = client.by_id_setting(SETTING_DEFAULT_LONGHORN_STATIC_SC)
    setting = client.update(setting, value=static_sc_name)
    assert setting.value == static_sc_name

    volume_name = "test-backup-kubernetes-status-pod"
    client.create_volume(name=volume_name, size=SIZE,
                         numberOfReplicas=2)
    volume = wait_for_volume_detached(client, volume_name)

    pod_name = "pod-" + volume_name
    pv_name = "pv-" + volume_name
    pvc_name = "pvc-" + volume_name
    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    ret = core_api.list_namespaced_persistent_volume_claim(
        namespace='default')
    pvc_found = False
    for item in ret.items:
        if item.metadata.name == pvc_name:
            pvc_found = item
            break
    assert pvc_found
    assert pvc_found.spec.storage_class_name == static_sc_name

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    ks = {
        'lastPodRefAt': '',
        'lastPVCRefAt': '',
        'namespace': 'default',
        'pvcName': pvc_name,
        'pvName': pv_name,
        'pvStatus': 'Bound',
        'workloadsStatus': [{
            'podName': pod_name,
            'podStatus': 'Running',
            'workloadName': '',
            'workloadType': ''
        }]
    }
    wait_volume_kubernetes_status(client, volume_name, ks)
    volume = wait_for_volume_healthy(client, volume_name)

    # Create Backup manually instead of calling create_backup since Kubernetes
    # is not guaranteed to mount our Volume to the test host.
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    bv, b = find_backup(client, volume_name, snap.name)
    new_b = bv.backupGet(name=b.name)
    status = loads(new_b.labels.get(KUBERNETES_STATUS_LABEL))
    assert status == ks

    restore_name = generate_volume_name()
    client.create_volume(name=restore_name, size=SIZE,
                         numberOfReplicas=2,
                         fromBackup=b.url)
    wait_for_volume_restoration_completed(client, restore_name)
    wait_for_volume_detached(client, restore_name)

    snapshot_created = b.snapshotCreated
    ks = {
        'lastPodRefAt': b.snapshotCreated,
        'lastPVCRefAt': b.snapshotCreated,
        'namespace': 'default',
        'pvcName': pvc_name,
        # Restoration should not apply PersistentVolume data.
        'pvName': '',
        'pvStatus': '',
        'workloadsStatus': [{
            'podName': pod_name,
            'podStatus': 'Running',
            'workloadName': '',
            'workloadType': ''
        }]
    }
    wait_volume_kubernetes_status(client, restore_name, ks)
    restore = client.by_id_volume(restore_name)
    # We need to compare LastPodRefAt and LastPVCRefAt manually since
    # wait_volume_kubernetes_status only checks for empty or non-empty state.
    assert restore.kubernetesStatus.lastPodRefAt == ks["lastPodRefAt"]
    assert restore.kubernetesStatus.lastPVCRefAt == ks["lastPVCRefAt"]

    bv.backupDelete(name=b.name)
    client.delete(restore)
    wait_for_volume_delete(client, restore_name)
    delete_and_wait_pod(core_api, pod_name)
    delete_and_wait_pvc(core_api, pvc_name)
    delete_and_wait_pv(core_api, pv_name)

    # With the Pod, PVC, and PV deleted, the Volume should have both Ref
    # fields set. Check that a new Backup and Restore will use this instead of
    # manually populating the Ref fields.
    ks = {
        'lastPodRefAt': 'NOT NULL',
        'lastPVCRefAt': 'NOT NULL',
        'namespace': 'default',
        'pvcName': pvc_name,
        'pvName': '',
        'pvStatus': '',
        'workloadsStatus': [{
            'podName': pod_name,
            'podStatus': 'Running',
            'workloadName': '',
            'workloadType': ''
        }]
    }
    wait_volume_kubernetes_status(client, volume_name, ks)
    volume = wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    bv, b = find_backup(client, volume_name, snap.name)
    new_b = bv.backupGet(name=b.name)
    status = loads(new_b.labels.get(KUBERNETES_STATUS_LABEL))
    # Check each field manually, we have no idea what the LastPodRefAt or the
    # LastPVCRefAt will be. We just know it shouldn't be SnapshotCreated.
    assert status['lastPodRefAt'] != snapshot_created
    assert status['lastPVCRefAt'] != snapshot_created
    assert status['namespace'] == "default"
    assert status['pvcName'] == pvc_name
    assert status['pvName'] == ""
    assert status['pvStatus'] == ""
    assert status['workloadsStatus'] == [{
        'podName': pod_name,
        'podStatus': 'Running',
        'workloadName': '',
        'workloadType': ''
    }]

    restore_name = generate_volume_name()
    client.create_volume(name=restore_name, size=SIZE,
                         numberOfReplicas=2,
                         fromBackup=b.url)
    wait_for_volume_restoration_completed(client, restore_name)
    wait_for_volume_detached(client, restore_name)

    ks = {
        'lastPodRefAt': status['lastPodRefAt'],
        'lastPVCRefAt': status['lastPVCRefAt'],
        'namespace': 'default',
        'pvcName': pvc_name,
        'pvName': '',
        'pvStatus': '',
        'workloadsStatus': [{
            'podName': pod_name,
            'podStatus': 'Running',
            'workloadName': '',
            'workloadType': ''
        }]
    }
    wait_volume_kubernetes_status(client, restore_name, ks)
    restore = client.by_id_volume(restore_name)
    assert restore.kubernetesStatus.lastPodRefAt == ks["lastPodRefAt"]
    assert restore.kubernetesStatus.lastPVCRefAt == ks["lastPVCRefAt"]

    bv.backupDelete(name=b.name)
    client.delete(restore)
    cleanup_volume(client, volume)
