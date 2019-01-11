#!/usr/sbin/python
import pytest
import time

from random import randrange

from common import client, core_api, statefulset, storage_class  # NOQA
from common import DEFAULT_BACKUP_TIMEOUT, DEFAULT_POD_INTERVAL
from common import DEFAULT_STATEFULSET_TIMEOUT, DEFAULT_STATEFULSET_INTERVAL
from common import DEFAULT_POD_TIMEOUT, VOLUME_RWTEST_SIZE
from common import delete_and_wait_statefulset, generate_random_data
from common import get_apps_api_client, get_statefulset_pod_info
from common import get_storage_api_client, read_volume_data, size_to_string
from common import wait_for_volume_detached, write_volume_data

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

Gi = (1 * 1024 * 1024 * 1024)

DEFAULT_STORAGECLASS_NAME = "longhorn-statefulset"
DEFAULT_VOLUME_SIZE = 3  # In Gi


def create_and_wait_statefulset(statefulset_manifest):
    """
    Create a new StatefulSet for testing.

    This function will block until all replicas in the StatefulSet are online
    or it times out, whichever occurs first.
    """
    api = get_apps_api_client()
    api.create_namespaced_stateful_set(
        body=statefulset_manifest,
        namespace='default')
    wait_statefulset(statefulset_manifest)


def create_and_test_backups(api, cli, pod_info):
    """
    Create backups for all Pods in a StatefulSet and tests that all the backups
    have the correct attributes.

    Args:
        api: An instance of CoreV1Api.
        cli: A Longhorn client instance.
        pod_info: A List of Pods with names and volume information. This List
            can be generated using the get_statefulset_pod_info function
            located in common.py.
    """
    for pod in pod_info:
        pod['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        pod['backup_snapshot'] = ''

        # Create backup.
        volume = cli.by_id_volume(pod['pv_name'])
        volume.snapshotCreate()
        write_volume_data(api, pod['pod_name'], pod['data'])
        pod['backup_snapshot'] = volume.snapshotCreate()
        volume.snapshotCreate()
        volume.snapshotBackup(name=pod['backup_snapshot']['name'])

        # Wait for backup to appear.
        found = False
        for i in range(DEFAULT_BACKUP_TIMEOUT):
            backup_volumes = cli.list_backupVolume()
            for bv in backup_volumes:
                if bv['name'] == pod['pv_name']:
                    found = True
                    break
            if found:
                break
            time.sleep(DEFAULT_POD_INTERVAL)
        assert found

        found = False
        for i in range(DEFAULT_BACKUP_TIMEOUT):
            backups = bv.backupList()
            for b in backups:
                if b['snapshotName'] == pod['backup_snapshot']['name']:
                    found = True
                    break
            if found:
                break
            time.sleep(DEFAULT_POD_INTERVAL)
        assert found

        # Make sure backup has the correct attributes.
        new_b = bv.backupGet(name=b["name"])
        assert new_b["name"] == b["name"]
        assert new_b["url"] == b["url"]
        assert new_b["snapshotName"] == b["snapshotName"]
        assert new_b["snapshotCreated"] == b["snapshotCreated"]
        assert new_b["created"] == b["created"]
        assert new_b["volumeName"] == b["volumeName"]
        assert new_b["volumeSize"] == b["volumeSize"]
        assert new_b["volumeCreated"] == b["volumeCreated"]

        # This backup has the url attribute we need to restore from backup.
        pod['backup_snapshot'] = b


def wait_statefulset(statefulset_manifest):
    api = get_apps_api_client()
    replicas = statefulset_manifest['spec']['replicas']
    for i in range(DEFAULT_STATEFULSET_TIMEOUT):
        s_set = api.read_namespaced_stateful_set(
            name=statefulset_manifest['metadata']['name'],
            namespace='default')
        if s_set.status.ready_replicas == replicas:
            break
        time.sleep(DEFAULT_STATEFULSET_INTERVAL)
    assert s_set.status.ready_replicas == replicas


def create_storage_class(sc_manifest):
    api = get_storage_api_client()
    api.create_storage_class(
        body=sc_manifest)


def update_test_manifests(statefulset_manifest, sc_manifest, name):
    """
    Write in a new StatefulSet name and the proper StorageClass name for tests.
    """
    statefulset_manifest['metadata']['name'] = \
        statefulset_manifest['spec']['selector']['matchLabels']['app'] = \
        statefulset_manifest['spec']['serviceName'] = \
        (statefulset_manifest['spec']['template']['metadata']['labels']
            ['app']) = name
    (statefulset_manifest['spec']['volumeClaimTemplates'][0]['spec']
        ['storageClassName']) = DEFAULT_STORAGECLASS_NAME
    sc_manifest['metadata']['name'] = DEFAULT_STORAGECLASS_NAME


def test_statefulset_mount(client, core_api, storage_class, statefulset):  # NOQA
    """
    Tests that volumes provisioned for a StatefulSet can be properly created,
    mounted, unmounted, and deleted on the Kubernetes cluster.
    """

    statefulset_name = 'statefulset-mount-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)

    volumes = client.list_volume()
    assert len(volumes) == statefulset['spec']['replicas']
    for v in volumes:
        # Workaround for checking volume name since they differ per pod.
        found = False
        for pod in pod_info:
            if v['name'] == pod['pv_name']:
                found = True
                break
        assert found
        pod_info.remove(pod)

        assert v['size'] == str(DEFAULT_VOLUME_SIZE * Gi)
        assert v['numberOfReplicas'] == \
            int(storage_class['parameters']['numberOfReplicas'])
        assert v['state'] == 'attached'
    # Confirm that we've iterated through all the volumes.
    assert len(pod_info) == 0


@pytest.mark.coretest   # NOQA
def test_statefulset_scaling(client, core_api, storage_class, statefulset):  # NOQA
    """
    Test that scaling up a StatefulSet successfully provisions new volumes.
    """

    statefulset_name = 'statefulset-scaling-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)

    volumes = client.list_volume()
    assert len(volumes) == statefulset['spec']['replicas']
    for v in volumes:
        found = False
        for pod in pod_info:
            if v['name'] == pod['pv_name']:
                found = True
                break
        assert found
        pod_info.remove(pod)

        assert v['size'] == str(DEFAULT_VOLUME_SIZE * Gi)
        assert v['numberOfReplicas'] == \
            int(storage_class['parameters']['numberOfReplicas'])
        assert v['state'] == 'attached'
    assert len(pod_info) == 0

    statefulset['spec']['replicas'] = replicas = 3
    apps_api = get_apps_api_client()
    apps_api.patch_namespaced_stateful_set(
        name=statefulset_name,
        namespace='default',
        body={
            'spec': {
                'replicas': replicas
            }
        })
    for i in range(DEFAULT_POD_TIMEOUT):
        s_set = apps_api.read_namespaced_stateful_set(
            name=statefulset_name,
            namespace='default')
        if s_set.status.ready_replicas == replicas:
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert s_set.status.ready_replicas == replicas

    pod_info = get_statefulset_pod_info(core_api, statefulset)

    volumes = client.list_volume()
    assert len(volumes) == replicas
    for v in volumes:
        found = False
        for pod in pod_info:
            if v['name'] == pod['pv_name']:
                found = True
                break
        assert found
        pod_info.remove(pod)

        assert v['size'] == str(DEFAULT_VOLUME_SIZE * Gi)
        assert v['numberOfReplicas'] == \
            int(storage_class['parameters']['numberOfReplicas'])
        assert v['state'] == 'attached'
    assert len(pod_info) == 0


@pytest.mark.csi  # NOQA
def test_statefulset_pod_deletion(core_api, storage_class, statefulset):  # NOQA
    """
    Test that a StatefulSet can spin up a new Pod with the same data after a
    previous Pod has been deleted.

    This test will only work in a CSI environment. It will automatically be
    disabled in FlexVolume environments.
    """

    statefulset_name = 'statefulset-pod-deletion-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)
    test_pod_name = statefulset_name + '-' + \
        str(randrange(statefulset['spec']['replicas']))
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    write_volume_data(core_api, test_pod_name, test_data)
    # Not using delete_and_wait_pod here because there is the small chance the
    # StatefulSet recreates the Pod quickly enough where the function won't
    # detect that the Pod was deleted, which will time out and throw an error.
    core_api.delete_namespaced_pod(name=test_pod_name, namespace='default',
                                   body=k8sclient.V1DeleteOptions())
    wait_statefulset(statefulset)
    resp = read_volume_data(core_api, test_pod_name)

    assert resp == test_data


def test_statefulset_backup(client, core_api, storage_class, statefulset):  # NOQA
    """
    Test that backups on StatefulSet volumes work properly.
    """

    statefulset_name = 'statefulset-backup-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    create_and_test_backups(core_api, client, pod_info)


@pytest.mark.recurring_job  # NOQA
def test_statefulset_recurring_backup(client, core_api, storage_class,  # NOQA
                                      statefulset):  # NOQA
    """
    Test that recurring backups on StatefulSets work properly.
    """

    statefulset_name = 'statefulset-backup-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    # backup every minute
    job_backup = {"name": "backup", "cron": "* * * * *",
                  "task": "backup", "retain": 2}
    pod_data = get_statefulset_pod_info(core_api, statefulset)
    for pod in pod_data:
        pod['data'] = generate_random_data(VOLUME_RWTEST_SIZE)
        pod['backup_snapshot'] = ''

    for pod in pod_data:
        volume = client.by_id_volume(pod['pv_name'])
        write_volume_data(core_api, pod['pod_name'], pod['data'])
        volume.recurringUpdate(jobs=[job_backup])

    time.sleep(300)

    for pod in pod_data:
        volume = client.by_id_volume(pod['pv_name'])
        snapshots = volume.snapshotList()
        count = 0
        for snapshot in snapshots:
            if snapshot['removed'] is False:
                count += 1

        # two backups + volume-head
        assert count == 3


def test_statefulset_restore(client, core_api, storage_class,  # NOQA
                             statefulset):  # NOQA
    """
    Test that data can be restored into volumes usable by a StatefulSet.
    """
    statefulset_name = 'statefulset-restore-test'
    update_test_manifests(statefulset, storage_class, statefulset_name)

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    create_and_test_backups(core_api, client, pod_info)

    delete_and_wait_statefulset(core_api, client, statefulset)

    csi = True
    try:
        core_api.read_namespaced_pod(
            name='csi-provisioner-0', namespace='longhorn-system')
    except ApiException as e:
        if (e.status == 404):
            csi = False

    # StatefulSet fixture already cleans these up, use the manifests instead of
    # the fixtures to avoid issues during teardown.
    pv = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {
            'name': ''
        },
        'spec': {
            'capacity': {
                'storage': size_to_string(DEFAULT_VOLUME_SIZE * Gi)
            },
            'volumeMode': 'Filesystem',
            'accessModes': ['ReadWriteOnce'],
            'persistentVolumeReclaimPolicy': 'Delete',
            'storageClassName': DEFAULT_STORAGECLASS_NAME
        }
    }

    pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': ''
        },
        'spec': {
            'accessModes': [
                'ReadWriteOnce'
            ],
            'resources': {
                'requests': {
                    'storage': size_to_string(DEFAULT_VOLUME_SIZE * Gi)
                }
            },
            'storageClassName': DEFAULT_STORAGECLASS_NAME
        }
    }

    if csi:
        pv['spec']['csi'] = {
            'driver': 'io.rancher.longhorn',
            'fsType': 'ext4',
            'volumeAttributes': {
                'numberOfReplicas':
                    storage_class['parameters']['numberOfReplicas'],
                'staleReplicaTimeout':
                    storage_class['parameters']['staleReplicaTimeout']
            },
            'volumeHandle': ''
        }
    else:
        pv['spec']['flexVolume'] = {
            'driver': 'rancher.io/longhorn',
            'fsType': 'ext4',
            'options': {
                'numberOfReplicas':
                    storage_class['parameters']['numberOfReplicas'],
                'staleReplicaTimeout':
                    storage_class['parameters']['staleReplicaTimeout'],
                'fromBackup': '',
                'size': size_to_string(DEFAULT_VOLUME_SIZE * Gi)
            }
        }

    # Make sure that volumes still work even if the Pod and StatefulSet names
    # are different.
    for pod in pod_info:
        pod['pod_name'] = pod['pod_name'].replace('statefulset-restore-test',
                                                  'statefulset-restore-test-2')
        pod['pvc_name'] = pod['pvc_name'].replace('statefulset-restore-test',
                                                  'statefulset-restore-test-2')

        pv['metadata']['name'] = pod['pvc_name']
        if csi:
            client.create_volume(
                name=pod['pvc_name'],
                size=size_to_string(DEFAULT_VOLUME_SIZE * Gi),
                numberOfReplicas=int(
                    storage_class['parameters']['numberOfReplicas']),
                fromBackup=pod['backup_snapshot']['url'])
            wait_for_volume_detached(client, pod['pvc_name'])

            pv['spec']['csi']['volumeHandle'] = pod['pvc_name']
        else:
            pv['spec']['flexVolume']['options']['fromBackup'] = \
                pod['backup_snapshot']['url']

        core_api.create_persistent_volume(pv)

        pvc['metadata']['name'] = pod['pvc_name']
        pvc['spec']['volumeName'] = pod['pvc_name']
        core_api.create_namespaced_persistent_volume_claim(
            body=pvc,
            namespace='default')

    statefulset_name = 'statefulset-restore-test-2'
    update_test_manifests(statefulset, storage_class, statefulset_name)
    create_and_wait_statefulset(statefulset)

    for pod in pod_info:
        resp = read_volume_data(core_api, pod['pod_name'])
        assert resp == pod['data']
