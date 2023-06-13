import pytest
import time

from common import client, core_api, statefulset, storage_class  # NOQA
from common import csi_pv, pvc, pod  # NOQA
from common import generate_volume_name, get_apps_api_client
from common import create_and_wait_statefulset
from common import update_statefulset_manifests
from common import create_storage_class, delete_storage_class
from common import wait_for_backup_completion, find_backup
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
from common import delete_backup
from common import create_and_check_volume, create_pvc, \
    wait_and_get_pv_for_pvc, wait_delete_pvc
from common import volume_name # NOQA
from common import update_setting
from common import SETTING_DEGRADED_AVAILABILITY

from backupstore import backupstore_cleanup

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

from backupstore import set_random_backupstore  # NOQA

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
        wait_delete_pod(api, p['pod_uid'])


def provision_and_wait_pv(client, core_api, storage_class, pvc): # NOQA
    """
    Provision a new Longhorn Volume via Storage Class and wait for the Volume
    and its associated resources to be created.

    This method also waits for the Kubernetes Status to be properly set on the
    Volume.

    :param client: An instance of the Longhorn client.
    :param core_api: An instance of the Kubernetes CoreV1API client.
    :param storage_class: A dict representing a Storage Class spec.
    :param pvc: A dict representing a Persistent Volume Claim spec.
    :return: The Persistent Volume that was provisioned.
    """
    create_storage_class(storage_class)
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    pvc_name = pvc['metadata']['name']
    create_pvc(pvc)

    pv = wait_and_get_pv_for_pvc(core_api, pvc_name)
    volume_name = pv.spec.csi.volume_handle  # NOQA

    ks = {
        'pvName': pv.metadata.name,
        'pvStatus': 'Bound',
        'namespace': 'default',
        'pvcName': pvc_name,
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    return pv


@pytest.mark.csi  # NOQA
def test_kubernetes_status(client, core_api, storage_class,  # NOQA
                           statefulset, csi_pv, pvc, pod):  # NOQA
    """
    Test Volume feature: Kubernetes Status

    1. Create StorageClass with `reclaimPolicy = Retain`
    2. Create a statefulset `kubernetes-status-test` with the StorageClass
        1. The statefulset has scale of 2.
    3. Get the volume name from the SECOND pod of the StateufulSet pod and
    create an `extra_pod` with the same volume on the same node
    4. Check the volumes that used by the StatefulSet
        1. The volume used by the FIRST StatefulSet pod will have one workload
        2. The volume used by the SECOND StatefulSet pod will have two
        workloads
        3. Validate related status, e.g. pv/pod name/state, workload
        name/type
    5. Check the volumes again
        1. PV/PVC should still be bound
        2. The volume used by the FIRST pod should have history data
        3. The volume used by the SECOND and extra pod should have current data
        point to the extra pod
    6. Delete the extra pod
        1. Now all the volume's should only have history data(`lastPodRefAt`
        set)
    7. Delete the PVC
        1. PVC should be updated with status `Released` and become history data
    8. Delete PV
        1. All the Kubernetes status information should be cleaned up.
    9. Reuse the two Longhorn volumes to create new pods
        1. Since the `reclaimPolicy == Retain`, volume won't be deleted by
        Longhorn
        2. Check the Kubernetes status now updated, with pod info but empty
        workload
        3. Default Longhorn Static StorageClass will remove the PV with PVC,
        but leave Longhorn volume
    """
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
        p, volume_name = pod_info[i], volume_info[i] # NOQA
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
        if i == 1:
            ks_list[i]['lastPodRefAt'] = ''
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
    """
    Test creating PV using Longhorn API

    1. Create volume
    2. Create PV for the volume
    3. Try to create another PV for the same volume. It should fail.
    4. Check Kubernetes Status for the volume since PV is created.
    """
    volume_name = "test-pv-creation" # NOQA
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
    """
    Test creating PVC with default StorageClass set

    The target is to make sure the newly create PV/PVC won't use default
    StorageClass, and if there is no default StorageClass, PV/PVC can still be
    created.

    1. Create a StorageClass and set it to be the default StorageClass
    2. Update static StorageClass to `longhorn-static-test`
    3. Create volume then PV/PVC.
    4. Make sure the newly created PV/PVC using StorageClass
    `longhorn-static-test`
    5. Create pod with PVC.
    6. Verify volume's Kubernetes Status
    7. Remove PVC and Pod.
    8. Verify volume's Kubernetes Status only contains current PV and history
    9. Wait for volume to detach (since pod is deleted)
    10. Reuse the volume on a new pod. Wait for the pod to start
    11. Verify volume's Kubernetes Status reflect the new pod.
    12. Delete PV/PVC/Pod.
    13. Verify volume's Kubernetes Status only contains history
    14. Delete the default StorageClass.
    15. Create PV/PVC for the volume.
    16. Make sure the PV's StorageClass is static StorageClass
    """
    # set default storage class
    storage_class['metadata']['annotations'] = \
        {"storageclass.kubernetes.io/is-default-class": "true"}
    create_storage_class(storage_class)

    static_sc_name = "longhorn-static-test"
    setting = client.by_id_setting(SETTING_DEFAULT_LONGHORN_STATIC_SC)
    setting = client.update(setting, value=static_sc_name)
    assert setting.value == static_sc_name

    volume_name = "test-pvc-creation-with-sc" # NOQA
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

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Released',
        'namespace': 'default',
        'pvcName': pvc_name,
        'lastPVCRefAt': 'not empty',
        'lastPodRefAt': 'not empty',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    # try to reuse the pv
    volume = wait_for_volume_detached(client, volume_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name_extra)
    pod['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = \
        pvc_name_extra
    create_and_wait_pod(core_api, pod)

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Bound',
        'namespace': 'default',
        'pvcName': pvc_name_extra,
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
    delete_and_wait_pvc(core_api, pvc_name_extra)
    delete_and_wait_pv(core_api, pv_name)

    ks = {
        'pvName': '',
        'pvStatus': '',
        'namespace': 'default',
        'pvcName': pvc_name_extra,
        'lastPVCRefAt': 'not empty',
        'lastPodRefAt': 'not empty',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

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


@pytest.mark.csi  # NOQA
def test_backup_kubernetes_status(set_random_backupstore, client, core_api, pod):  # NOQA
    """
    Test that Backups have KubernetesStatus stored properly when there is an
    associated PersistentVolumeClaim and Pod.

    1. Setup a random backupstore
    2. Set settings Longhorn Static StorageClass to `longhorn-static-test`
    3. Create a volume and PV/PVC. Verify the StorageClass of PVC
    4. Create a Pod using the PVC.
    5. Check volume's Kubernetes status to reflect PV/PVC/Pod correctly.
    6. Create a backup for the volume.
    7. Verify the labels of created backup reflect PV/PVC/Pod status.
    8. Restore the backup to a volume. Wait for restoration to complete.
    9. Check the volume's Kubernetes Status
        1. Make sure the `lastPodRefAt` and `lastPVCRefAt` is snapshot created
    time
    10. Delete the backup and restored volume.
    11. Delete PV/PVC/Pod.
    12. Verify volume's Kubernetes Status updated to reflect history data.
    13. Attach the volume and create another backup. Verify the labels
    14. Verify the volume's Kubernetes status.
    15. Restore the previous backup to a new volume. Wait for restoration.
    16. Verify the restored volume's Kubernetes status.
        1. Make sure `lastPodRefAt` and `lastPVCRefAt` matched volume on step
        12
    """
    update_setting(client, SETTING_DEGRADED_AVAILABILITY, "false")

    host_id = get_self_host_id()
    static_sc_name = "longhorn-static-test"
    setting = client.by_id_setting(SETTING_DEFAULT_LONGHORN_STATIC_SC)
    setting = client.update(setting, value=static_sc_name)
    assert setting.value == static_sc_name

    volume_name = "test-backup-kubernetes-status-pod" # NOQA
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
    wait_for_backup_completion(client, volume_name, snap.name)
    _, b = find_backup(client, volume_name, snap.name)
    # Check backup label
    status = loads(b.labels.get(KUBERNETES_STATUS_LABEL))
    assert status == ks
    # Check backup volume label
    for _ in range(RETRY_COUNTS):
        bv = client.by_id_backupVolume(volume_name)
        if bv is not None and bv.labels is not None:
            break
        time.sleep(RETRY_INTERVAL)
    assert bv is not None and bv.labels is not None
    status = loads(bv.labels.get(KUBERNETES_STATUS_LABEL))
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

    delete_backup(client, bv.name, b.name)
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
        'pvStatus': ''
    }
    wait_volume_kubernetes_status(client, volume_name, ks)
    volume = wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    volume = wait_for_backup_completion(client, volume_name, snap.name)
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
        'pvStatus': ''
    }
    wait_volume_kubernetes_status(client, restore_name, ks)
    restore = client.by_id_volume(restore_name)
    assert restore.kubernetesStatus.lastPodRefAt == ks["lastPodRefAt"]
    assert restore.kubernetesStatus.lastPVCRefAt == ks["lastPVCRefAt"]

    # cleanup
    backupstore_cleanup(client)
    client.delete(restore)
    cleanup_volume(client, volume)


@pytest.mark.csi  # NOQA
def test_delete_with_static_pv(client, core_api, volume_name): # NOQA
    """
    Test that deleting a Volume with related static Persistent Volume and
    Persistent Volume Claim resources successfully deletes the Volume and
    cleans up those resources.

    1. Create a Volume in Longhorn.
    2. Create a static Persistent Volume and Persistent Volume Claim for the
    Volume through Longhorn.
    3. Wait for the Kubernetes Status to indicate the existence of these
    resources.
    4. Attempt deletion of the Volume.
    5. Verify that the Volume and its associated resources have been deleted.
    """
    volume = create_and_check_volume(client, volume_name)
    pv_name = 'pv-' + volume_name
    pvc_name = 'pvc-' + volume_name
    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Bound',
        'namespace': 'default',
        'pvcName': pvc_name,
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume_name, ks)

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)
    wait_delete_pv(core_api, pv_name)
    wait_delete_pvc(core_api, pvc_name)


@pytest.mark.csi  # NOQA
def test_delete_with_provisioned_pv(client, core_api, storage_class, pvc): # NOQA
    """
    Test that deleting a Volume with dynamically provisioned Persistent Volume
    and Persistent Volume Claim resources successfully deletes the Volume and
    cleans up those resources.

    1. Create a Storage Class to test with.
    2. Create a Persistent Volume Claim that requests a Volume from that
    Storage Class.
    3. Wait for the Volume to be provisioned and for the Kubernetes Status to
    be updated correctly.
    4. Attempt to delete the Volume.
    5. Verify that the Volume and its associated resources have been deleted.
    """
    pv = provision_and_wait_pv(client, core_api, storage_class, pvc)
    pv_name = pv.metadata.name
    volume_name = pv.spec.csi.volume_handle  # NOQA

    volume = client.by_id_volume(volume_name)
    client.delete(volume)
    wait_for_volume_delete(client, volume_name)
    wait_delete_pv(core_api, pv_name)
    wait_delete_pvc(core_api, pvc['metadata']['name'])


@pytest.mark.csi  # NOQA
def test_delete_provisioned_pvc(client, core_api,  storage_class, pvc): # NOQA
    """
    Test that deleting the Persistent Volume Claim for a dynamically
    provisioned Volume properly deletes the Volume and the associated
    Kubernetes resources.

    1. Create a Storage Class to test with.
    2. Create a Persistent Volume Claim that requests a Volume from that
    Storage Class.
    3. Wait for the Volume to be provisioned and for the Kubernetes Status to
    be updated correctly.
    4. Attempt to delete the Persistent Volume Claim.
    5. Verify that the associated Volume and its resources have been deleted.
    """
    pv = provision_and_wait_pv(client, core_api, storage_class, pvc)
    pv_name = pv.metadata.name
    volume_name = pv.spec.csi.volume_handle  # NOQA

    delete_and_wait_pvc(core_api, pvc['metadata']['name'])
    wait_delete_pv(core_api, pv_name)
    wait_for_volume_delete(client, volume_name)
