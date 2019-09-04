import time
import os
import stat
import random
import string
import subprocess
import json
import hashlib
import signal

import pytest

import longhorn

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.stream import stream

from kubernetes.client.rest import ApiException


Mi = (1024 * 1024)
Gi = (1024 * Mi)

SIZE = str(16 * Mi)
VOLUME_NAME = "longhorn-testvol"
DEV_PATH = "/dev/longhorn/"
VOLUME_RWTEST_SIZE = 512
VOLUME_INVALID_POS = -1

BASE_IMAGE_EXT4 = "rancher/longhorn-test:baseimage-ext4"
BASE_IMAGE_EXT4_SIZE = 32 * Mi

PORT = ":9500"

RETRY_COMMAND_COUNT = 3
RETRY_COUNTS = 300
RETRY_INTERVAL = 0.5
RETRY_INTERVAL_LONG = 1

LONGHORN_NAMESPACE = "longhorn-system"

COMPATIBILTY_TEST_IMAGE_PREFIX = "longhornio/longhorn-test:version-test"
UPGRADE_TEST_IMAGE_PREFIX = "longhornio/longhorn-test:upgrade-test"

ISCSI_DEV_PATH = "/dev/disk/by-path"

VOLUME_FIELD_STATE = "state"
VOLUME_STATE_ATTACHED = "attached"
VOLUME_STATE_DETACHED = "detached"

VOLUME_FIELD_ROBUSTNESS = "robustness"
VOLUME_ROBUSTNESS_HEALTHY = "healthy"
VOLUME_ROBUSTNESS_DEGRADED = "degraded"
VOLUME_ROBUSTNESS_FAULTED = "faulted"

VOLUME_FIELD_INITIALRESTORATIONREQUIRED = "initialRestorationRequired"

DEFAULT_STORAGECLASS_NAME = 'longhorn-test'

DEFAULT_LONGHORN_PARAMS = {
    'numberOfReplicas': '3',
    'staleReplicaTimeout': '30'
}

DEFAULT_BACKUP_TIMEOUT = 100

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180

DEFAULT_STATEFULSET_INTERVAL = 5
DEFAULT_STATEFULSET_TIMEOUT = 180

DEFAULT_VOLUME_SIZE = 3  # In Gi

DIRECTORY_PATH = '/tmp/longhorn-test/'

VOLUME_CONDITION_SCHEDULED = "scheduled"
VOLUME_CONDITION_STATUS = "status"

CONDITION_STATUS_TRUE = "True"
CONDITION_STATUS_FALSE = "False"
CONDITION_STATUS_UNKNOWN = "Unknown"

SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE = \
    "storage-over-provisioning-percentage"
SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = \
    "storage-minimal-available-percentage"
DEFAULT_DISK_PATH = "/var/lib/rancher/longhorn/"
DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE = "500"
DEFAULT_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = "10"

NODE_CONDITION_MOUNTPROPAGATION = "MountPropagation"
DISK_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_READY = "Ready"

STREAM_EXEC_TIMEOUT = 60

SETTING_BACKUP_TARGET = "backup-target"
SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
SETTING_DEFAULT_REPLICA_COUNT = "default-replica-count"
SETTING_DEFAULT_LONGHORN_STATIC_SC = "default-longhorn-static-storage-class"
SETTING_TAINT_TOLERATION = "taint-toleration"

CSI_UNKNOWN = 0
CSI_TRUE = 1
CSI_FALSE = 2

BASE_IMAGE_LABEL = "ranchervm-base-image"
KUBERNETES_STATUS_LABEL = "KubernetesStatus"

# Default Tag test case set up to fulfill as many test inputs as
# possible.
DEFAULT_TAGS = [
    {
        "disk": ["nvme", "ssd"],
        "node": ["main", "storage"]
    },
    {
        "disk": ["nvme", "ssd"],
        "node": ["fallback", "storage"]
    },
    {
        "disk": ["m2", "nvme"],
        "node": ["main", "storage"]
    }
]


def load_k8s_config():
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()


def get_apps_api_client():
    load_k8s_config()
    return k8sclient.AppsV1Api()


def get_core_api_client():
    load_k8s_config()
    return k8sclient.CoreV1Api()


def get_storage_api_client():
    load_k8s_config()
    return k8sclient.StorageV1Api()


def get_longhorn_api_client():
    k8sconfig.load_incluster_config()
    ips = get_mgr_ips()
    client = get_client(ips[0] + PORT)
    return client


def cleanup_volume(client, volume):
    """
    Clean up the volume after the test.
    :param client: The Longhorn client to use in the request.
    :param volume: The volume to clean up.
    """
    volume.detach()
    volume = wait_for_volume_detached(client, volume["name"])
    client.delete(volume)
    wait_for_volume_delete(client, volume["name"])
    volumes = client.list_volume()
    assert len(volumes) == 0


def create_backup(client, volname, data={}, labels={}):
    volume = client.by_id_volume(volname)
    volume.snapshotCreate()
    if not data:
        data = write_volume_random_data(volume)
    else:
        data = write_volume_data(volume, data)
    snap = volume.snapshotCreate()
    volume.snapshotCreate()
    volume.snapshotBackup(name=snap["name"], labels=labels)

    bv, b = find_backup(client, volname, snap["name"])

    new_b = bv.backupGet(name=b["name"])
    assert new_b["name"] == b["name"]
    assert new_b["url"] == b["url"]
    assert new_b["snapshotName"] == b["snapshotName"]
    assert new_b["snapshotCreated"] == b["snapshotCreated"]
    assert new_b["created"] == b["created"]
    assert new_b["volumeName"] == b["volumeName"]
    assert new_b["volumeSize"] == b["volumeSize"]
    assert new_b["volumeCreated"] == b["volumeCreated"]
    # Don't directly compare the Label dictionaries, since the server could
    # have added extra Labels (for things like BaseImage).
    for key, val in labels.iteritems():
        assert new_b["labels"].get(key) == val

    volume = wait_for_backup_completion(client, volname, snap["name"])
    volume = wait_for_volume_status(client, volname,
                                    "lastBackup",
                                    b["name"])
    assert volume["lastBackupAt"] != ""

    return bv, b, snap, data


def delete_backup(backup_volume, backup_name):
    backup_volume.backupDelete(name=backup_name)

    found = False
    for i in range(RETRY_COMMAND_COUNT):
        found = False
        try:
            backups = backup_volume.backupList().data
        except longhorn.ApiError:
            continue

        for b in backups:
            if b["name"] == backup_name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)

    assert not found


def create_and_check_volume(client, volume_name, num_of_replicas=3, size=SIZE,
                            base_image="", frontend="blockdev"):
    """
    Create a new volume with the specified parameters. Assert that the new
    volume is detached and that all of the requested parameters match.

    :param client: The Longhorn client to use in the request.
    :param volume_name: The name of the volume.
    :param num_of_replicas: The number of replicas the volume should have.
    :param size: The size of the volume, as a string representing the number
    of bytes.
    :param base_image: The base image to use for the volume.
    :param frontend: The frontend to use for the volume.
    :return: The volume instance created.
    """
    client.create_volume(name=volume_name, size=size,
                         numberOfReplicas=num_of_replicas,
                         baseImage=base_image, frontend=frontend)
    volume = wait_for_volume_detached(client, volume_name)
    assert volume["name"] == volume_name
    assert volume["size"] == size
    assert volume["numberOfReplicas"] == num_of_replicas
    assert volume["state"] == "detached"
    assert volume["baseImage"] == base_image
    assert volume["frontend"] == frontend
    assert volume["created"] != ""
    return volume


def create_and_wait_pod(api, pod_manifest):
    """
    Creates a new Pod attached to a PersistentVolumeClaim for testing.

    The function will block until the Pod is online or until it times out,
    whichever occurs first. The volume created by the manifest passed in will
    be mounted to '/data'.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        volume: The volume manifest.
    """
    api.create_namespaced_pod(
        body=pod_manifest,
        namespace='default')
    for i in range(DEFAULT_POD_TIMEOUT):
        pod = api.read_namespaced_pod(
            name=pod_manifest['metadata']['name'],
            namespace='default')
        if pod.status.phase != 'Pending':
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert pod.status.phase == 'Running'


def create_pvc_spec(name):
    # type: (str) -> dict
    """
    Generate a volume manifest using the given name for the PVC.

    This spec is used to test dynamically provisioned PersistentVolumes (those
    created using a storage class).
    """
    return {
        'name': 'pod-data',
        'persistentVolumeClaim': {
            'claimName': name,
            'readOnly': False
        }
    }


def delete_and_wait_pod(api, pod_name):
    """
    Delete a specified Pod from the "default" namespace.

    This function does not check if the Pod does exist and will throw an error
    if a nonexistent Pod is specified.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
    """
    try:
        api.delete_namespaced_pod(
            name=pod_name, namespace='default',
            body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

    wait_delete_pod(api, pod_name)


def delete_and_wait_statefulset(api, client, statefulset):
    apps_api = get_apps_api_client()
    if not check_statefulset_existence(apps_api,
                                       statefulset['metadata']['name']):
        return

    # We need to generate the names for the PVCs on our own so we can
    # delete them.
    pod_data = get_statefulset_pod_info(api, statefulset)

    try:
        apps_api.delete_namespaced_stateful_set(
            name=statefulset['metadata']['name'],
            namespace='default', body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

    for i in range(DEFAULT_POD_TIMEOUT):
        ret = apps_api.list_namespaced_stateful_set(namespace='default')
        found = False
        for item in ret.items:
            if item.metadata.name == statefulset['metadata']['name']:
                found = True
                break
        if not found:
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert not found
    client = get_longhorn_api_client()
    for pod in pod_data:
        # Wait on Pods too, we apparently had timeout issues with them.
        wait_delete_pod(api, pod['pod_name'])
        delete_and_wait_pvc(api, pod['pvc_name'])
        # The StatefulSet tests involve both StorageClass provisioned volumes
        # and our manually created PVs. This checks the status of our PV once
        # the PVC is deleted. If it is Failed, we know it is a PV and we must
        # delete it manually. If it is removed from the system, we can just
        # wait for deletion.
        for i in range(DEFAULT_POD_TIMEOUT):
            ret = api.list_persistent_volume()
            found = False
            for item in ret.items:
                if item.metadata.name == pod['pv_name']:
                    if item.status.phase in ('Failed', 'Released'):
                        delete_and_wait_pv(api, pod['pv_name'])
                        delete_and_wait_longhorn(client, pod['pv_name'])
                    else:
                        found = True
                        break
            if not found:
                break
            time.sleep(DEFAULT_POD_INTERVAL)
        assert not found
        wait_for_volume_delete(client, pod['pv_name'])


def get_volume_name(api, pvc_name):
    # type: (dict) -> str
    """
    Given a PersistentVolumeClaim, return the name of the associated PV.
    """
    claim = api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return claim.spec.volume_name


def get_statefulset_pod_info(api, s_set):
    pod_info = []
    for i in range(s_set['spec']['replicas']):
        pod_name = s_set['metadata']['name'] + '-' + str(i)
        pod = api.read_namespaced_pod(name=pod_name, namespace='default')
        pvc_name = pod.spec.volumes[0].persistent_volume_claim.claim_name
        pv_name = get_volume_name(api, pvc_name)
        pod_info.append({
            'pod_name': pod_name,
            'pv_name': pv_name,
            'pvc_name': pvc_name,
        })
    return pod_info


def delete_and_wait_longhorn(client, name):
    """
    Delete a volume from Longhorn.
    """
    try:
        v = client.by_id_volume(name)
        client.delete(v)
    except ApiException as ex:
        assert ex.status == 404
    except longhorn.ApiError as err:
        # for deleting a non-existing volume,
        # the status_code is 500 Server Error.
        assert err.error.code == 500

    wait_for_volume_delete(client, name)


def read_volume_data(api, pod_name):
    """
    Retrieve data from a Pod's volume.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.

    Returns:
        The data contained within the volume.
    """
    read_command = [
        '/bin/sh',
        '-c',
        'cat /data/test'
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=read_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def write_pod_volume_data(api, pod_name, test_data):
    """
    Write data into a Pod's volume.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        test_data: The data to be written.
    """
    write_command = [
        '/bin/sh',
        '-c',
        'echo -ne ' + test_data + ' > /data/test'
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream write'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=write_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def size_to_string(volume_size):
    # type: (int) -> str
    """
    Convert a volume size to string format to pass into Kubernetes.
    Args:
        volume_size: The size of the volume in bytes.
    Returns:
        The size of the volume in gigabytes as a passable string to Kubernetes.
    """
    if volume_size >= Gi:
        return str(volume_size >> 30) + 'Gi'
    elif volume_size >= Mi:
        return str(volume_size >> 20) + 'Mi'
    else:
        return str(volume_size >> 10) + 'Ki'


def wait_delete_pod(api, pod_name):
    for i in range(DEFAULT_POD_TIMEOUT):
        ret = api.list_namespaced_pod(namespace='default')
        found = False
        for item in ret.items:
            if item.metadata.name == pod_name:
                found = True
                break
        if not found:
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert not found


def check_volume_replicas(volume, spec, tag_mapping):
    """
    Check the replicas on the volume to ensure that they were scheduled
    properly.
    :param volume: The Volume to check.
    :param spec: The spec to validate the Tag against.
    :param tag_mapping: The mapping of Nodes to the Tags they have.
    :raise AssertionError: If the Volume doesn't match all the conditions.
    """
    found_hosts = {}
    # Make sure that all the Tags the Volume requested were fulfilled.
    for replica in volume["replicas"]:
        found_hosts[replica["hostId"]] = {}
        assert not len(set(spec["disk"]) -
                       set(tag_mapping[replica["hostId"]]["disk"]))
        assert not len(set(spec["node"]) -
                       set(tag_mapping[replica["hostId"]]["node"]))

    # The Volume should have replicas on as many nodes as matched
    # the requirements (specified by "expected" in the spec variable).
    assert len(found_hosts) == spec["expected"]


# Default argument is mutable on this function, but it's fine since we're only
# using it as an empty tag list to pass to the server and will never actually
# modify it.
def set_node_tags(client, node, tags=[]):  # NOQA
    """
    Set the tags on a node without modifying its scheduling status.
    :param client: The Longhorn client to use in the request.
    :param node: The Node to update.
    :param tags: The tags to set on the node.
    :return: The updated Node.
    """
    return client.update(node, allowScheduling=node["allowScheduling"],
                         tags=tags)


@pytest.fixture
def flexvolume(request):
    flexvolume_manifest = {
        'name': generate_volume_name(),
        'flexVolume': {
            'driver': 'rancher.io/longhorn',
            'fsType': 'ext4',
            'options': {
                'size': size_to_string(DEFAULT_VOLUME_SIZE * Gi),
                'numberOfReplicas':
                    DEFAULT_LONGHORN_PARAMS['numberOfReplicas'],
                'staleReplicaTimeout':
                    DEFAULT_LONGHORN_PARAMS['staleReplicaTimeout'],
                'fromBackup': ''
            }
        }
    }

    def finalizer():
        client = get_longhorn_api_client()
        delete_and_wait_longhorn(client, flexvolume_manifest['name'])

    request.addfinalizer(finalizer)

    return flexvolume_manifest


@pytest.fixture
def flexvolume_baseimage(request):
    flexvolume_manifest = flexvolume(request)
    flexvolume_manifest['flexVolume']['options']['size'] = \
        size_to_string(BASE_IMAGE_EXT4_SIZE)
    flexvolume_manifest['flexVolume']['fsType'] = ''
    flexvolume_manifest['flexVolume']['options']['baseImage'] = BASE_IMAGE_EXT4
    return flexvolume_manifest


@pytest.fixture
def pod_make(request):
    def make_pod(name='test-pod'):
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': name
            },
            'spec': {
                'containers': [{
                    'image': 'busybox',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'sleep',
                    "args": [
                        "/bin/sh",
                        "-c",
                        "while true; do date; sleep 5; done"
                    ],
                    "volumeMounts": [{
                        'name': 'pod-data',
                        'mountPath': '/data'
                    }],
                }],
                'volumes': []
            }
        }

        def finalizer():
            api = get_core_api_client()
            try:
                delete_and_wait_pod(api, pod_manifest['metadata']['name'])
            except Exception as e:
                print "Exception when waiting for pod deletion", e
                return

        request.addfinalizer(finalizer)
        return pod_manifest

    return make_pod


@pytest.fixture
def pod(request):
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': 'test-pod'
        },
        'spec': {
            'containers': [{
                'image': 'busybox',
                'imagePullPolicy': 'IfNotPresent',
                'name': 'sleep',
                "args": [
                    "/bin/sh",
                    "-c",
                    "while true;do date;sleep 5; done"
                ],
                "volumeMounts": [{
                    'name': 'pod-data',
                    'mountPath': '/data'
                }],
            }],
            'volumes': []
        }
    }

    def finalizer():
        api = get_core_api_client()
        delete_and_wait_pod(api, pod_manifest['metadata']['name'])

    request.addfinalizer(finalizer)

    return pod_manifest


@pytest.fixture
def core_api(request):
    """
    Create a new CoreV1API instance.
    Returns:
        A new CoreV1API Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    core_api = k8sclient.CoreV1Api()

    return core_api


@pytest.fixture
def csi_pv(request):
    volume_name = generate_volume_name()
    pv_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {
            'name': volume_name
        },
        'spec': {
            'capacity': {
                'storage': size_to_string(DEFAULT_VOLUME_SIZE * Gi)
            },
            'volumeMode': 'Filesystem',
            'accessModes': ['ReadWriteOnce'],
            'persistentVolumeReclaimPolicy': 'Delete',
            'csi': {
                'driver': 'io.rancher.longhorn',
                'fsType': 'ext4',
                'volumeAttributes': {
                    'numberOfReplicas':
                        DEFAULT_LONGHORN_PARAMS['numberOfReplicas'],
                    'staleReplicaTimeout':
                        DEFAULT_LONGHORN_PARAMS['staleReplicaTimeout']
                },
                'volumeHandle': volume_name
            }
        }
    }

    def finalizer():
        api = get_core_api_client()
        delete_and_wait_pv(api, pv_manifest['metadata']['name'])

        client = get_longhorn_api_client()
        delete_and_wait_longhorn(client, pv_manifest['metadata']['name'])

    request.addfinalizer(finalizer)

    return pv_manifest


@pytest.fixture
def csi_pv_baseimage(request):
    pv_manifest = csi_pv(request)
    pv_manifest['spec']['capacity']['storage'] = \
        size_to_string(BASE_IMAGE_EXT4_SIZE)
    pv_manifest['spec']['csi']['volumeAttributes']['baseImage'] = \
        BASE_IMAGE_EXT4
    return pv_manifest


@pytest.fixture
def pvc(request):
    pvc_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': generate_volume_name()
        },
        'spec': {
            'accessModes': [
                'ReadWriteOnce'
            ],
            'resources': {
                'requests': {
                    'storage': size_to_string(DEFAULT_VOLUME_SIZE * Gi)
                }
            }
        }
    }

    def finalizer():
        api = k8sclient.CoreV1Api()

        if not check_pvc_existence(api, pvc_manifest['metadata']['name']):
            return

        claim = api.read_namespaced_persistent_volume_claim(
            name=pvc_manifest['metadata']['name'], namespace='default')
        volume_name = claim.spec.volume_name

        api = get_core_api_client()
        delete_and_wait_pvc(api, pvc_manifest['metadata']['name'])

        # Working around line break issue.
        key = 'volume.beta.kubernetes.io/storage-provisioner'
        # If not using StorageClass (such as in CSI test), the Longhorn volume
        # will not be automatically deleted, causing this to throw an error.
        if (key in claim.metadata.annotations):
            client = get_longhorn_api_client()
            wait_for_volume_delete(client, volume_name)

    request.addfinalizer(finalizer)

    return pvc_manifest


@pytest.fixture
def pvc_baseimage(request):
    pvc_manifest = pvc(request)
    pvc_manifest['spec']['resources']['requests']['storage'] = \
        size_to_string(BASE_IMAGE_EXT4_SIZE)
    return pvc_manifest


@pytest.fixture
def statefulset(request):
    statefulset_manifest = {
        'apiVersion': 'apps/v1',
        'kind': 'StatefulSet',
        'metadata': {
            'name': 'test-statefulset'
        },
        'spec': {
            'selector': {
                'matchLabels': {
                    'app': 'test-statefulset'
                }
            },
            'serviceName': 'test-statefulset',
            'replicas': 2,
            'template': {
                'metadata': {
                    'labels': {
                        'app': 'test-statefulset'
                    }
                },
                'spec': {
                    'terminationGracePeriodSeconds': 10,
                    'containers': [{
                        'image': 'busybox',
                        'imagePullPolicy': 'IfNotPresent',
                        'name': 'sleep',
                        'args': [
                            '/bin/sh',
                            '-c',
                            'while true;do date;sleep 5; done'
                        ],
                        'volumeMounts': [{
                            'name': 'pod-data',
                            'mountPath': '/data'
                        }]
                    }]
                }
            },
            'volumeClaimTemplates': [{
                'metadata': {
                    'name': 'pod-data'
                },
                'spec': {
                    'accessModes': [
                        'ReadWriteOnce'
                    ],
                    'storageClassName': DEFAULT_STORAGECLASS_NAME,
                    'resources': {
                        'requests': {
                            'storage': size_to_string(
                                           DEFAULT_VOLUME_SIZE * Gi)
                        }
                    }
                }
            }]
        }
    }

    def finalizer():
        api = get_core_api_client()
        client = get_longhorn_api_client()
        delete_and_wait_statefulset(api, client, statefulset_manifest)

    request.addfinalizer(finalizer)

    return statefulset_manifest


@pytest.fixture
def storage_class(request):
    sc_manifest = {
        'apiVersion': 'storage.k8s.io/v1',
        'kind': 'StorageClass',
        'metadata': {
            'name': DEFAULT_STORAGECLASS_NAME
        },
        'provisioner': 'rancher.io/longhorn',
        'parameters': {
            'numberOfReplicas': DEFAULT_LONGHORN_PARAMS['numberOfReplicas'],
            'staleReplicaTimeout':
                DEFAULT_LONGHORN_PARAMS['staleReplicaTimeout']
        },
        'reclaimPolicy': 'Delete'
    }

    def finalizer():
        api = get_storage_api_client()
        try:
            api.delete_storage_class(name=sc_manifest['metadata']['name'],
                                     body=k8sclient.V1DeleteOptions())
        except ApiException as e:
            assert e.status == 404

    request.addfinalizer(finalizer)

    return sc_manifest


@pytest.yield_fixture
def node_default_tags():
    """
    Assign the Tags under DEFAULT_TAGS to the Longhorn client's Nodes to
    provide a base set of Tags to work with in the tests.
    :return: A dictionary mapping a Node's ID to the Tags it has.
    """
    client = get_longhorn_api_client()  # NOQA
    nodes = client.list_node()
    assert len(nodes) == 3

    tag_mappings = {}
    for tags, node in zip(DEFAULT_TAGS, nodes):
        assert len(node["disks"]) == 1

        update_disks = get_update_disks(node["disks"])
        update_disks[0]["tags"] = tags["disk"]
        new_node = node.diskUpdate(disks=update_disks)
        disks = get_update_disks(new_node["disks"])
        assert disks[0]["tags"] == tags["disk"]

        new_node = set_node_tags(client, node, tags["node"])
        assert new_node["tags"] == tags["node"]

        tag_mappings[node["id"]] = tags
    yield tag_mappings

    client = get_longhorn_api_client()  # NOQA
    nodes = client.list_node()
    for node in nodes:
        update_disks = get_update_disks(node["disks"])
        update_disks[0]["tags"] = []
        new_node = node.diskUpdate(disks=update_disks)
        disks = get_update_disks(new_node["disks"])
        assert disks[0]["tags"] is None

        new_node = set_node_tags(client, node)
        assert new_node["tags"] is None


@pytest.fixture
def random_labels():
    labels = {}
    i = 0
    while i < 3:
        key = "label/" + "".join(random.choice(string.ascii_lowercase +
                                               string.digits)
                                 for _ in range(6))
        if not labels.get(key):
            labels[key] = generate_random_data(VOLUME_RWTEST_SIZE)
            i += 1
    return labels


@pytest.fixture
def client(request):
    """
    Return an individual Longhorn API client for testing.
    """
    k8sconfig.load_incluster_config()
    # Make sure nodes and managers are all online.
    ips = get_mgr_ips()
    client = get_client(ips[0] + PORT)
    hosts = client.list_node()
    assert len(hosts) == len(ips)

    request.addfinalizer(lambda: cleanup_client(client))

    cleanup_client(client)

    return client


@pytest.fixture
def clients(request):
    k8sconfig.load_incluster_config()
    ips = get_mgr_ips()
    client = get_client(ips[0] + PORT)
    hosts = client.list_node()
    assert len(hosts) == len(ips)
    clis = get_clients(hosts)

    def finalizer():
        client = clis.itervalues().next()
        cleanup_client(client)

    request.addfinalizer(finalizer)

    client = clis.itervalues().next()
    cleanup_client(client)

    return clis


def cleanup_client(client):
    # cleanup test disks
    cleanup_test_disks(client)

    volumes = client.list_volume()
    for v in volumes:
        # ignore the error when clean up
        try:
            client.delete(v)
        except Exception as e:
            print "Exception when cleanup volume ", v, e
            pass
    images = client.list_engine_image()
    for img in images:
        if not img["default"]:
            # ignore the error when clean up
            try:
                client.delete(img)
            except Exception as e:
                print "Exception when cleanup image", img, e
                pass

    # enable nodes scheduling
    reset_node(client)
    reset_disks_for_all_nodes(client)
    reset_settings(client)


def get_client(address):
    url = 'http://' + address + '/v1/schemas'
    c = longhorn.from_env(url=url)
    return c


def get_mgr_ips():
    ret = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
            label_selector="app=longhorn-manager",
            watch=False)
    mgr_ips = []
    for i in ret.items:
        mgr_ips.append(i.status.pod_ip)
    return mgr_ips


def get_self_host_id():
    envs = os.environ
    return envs["NODE_NAME"]


def get_backupstore_url():
    backupstore = os.environ['LONGHORN_BACKUPSTORES']
    backupstore = backupstore.replace(" ", "")
    backupstores = backupstore.split(",")

    assert len(backupstores) != 0
    return backupstores


def get_clients(hosts):
    clients = {}
    for host in hosts:
        assert host["name"] is not None
        assert host["address"] is not None
        clients[host["name"]] = get_client(host["address"] + PORT)
    return clients


def wait_scheduling_failure(client, volume_name):
    """
    Wait and make sure no new replicas are running on the specified
    volume. Trigger a failed assertion of one is detected.
    :param client: The Longhorn client to use in the request.
    :param volume_name: The name of the volume.
    """
    scheduling_failure = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        if v["conditions"]["scheduled"]["status"] == "False" and \
                v["conditions"]["scheduled"]["reason"] == \
                "ReplicaSchedulingFailure":
            scheduling_failure = True
        if scheduling_failure:
            break
        time.sleep(RETRY_INTERVAL)
    assert scheduling_failure


def wait_for_device_login(dest_path, name):
    dev = ""
    for i in range(RETRY_COUNTS):
        for j in range(RETRY_COMMAND_COUNT):
            files = []
            try:
                files = os.listdir(dest_path)
                break
            except Exception:
                time.sleep(1)
        assert files
        if name in files:
            dev = name
            break
        time.sleep(RETRY_INTERVAL)
    assert dev == name
    return dev


def wait_for_volume_creation(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        found = False
        for volume in volumes:
            if volume["name"] == name:
                found = True
                break
        if found:
            break
    assert found


def wait_for_volume_detached(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_STATE,
                                  VOLUME_STATE_DETACHED)


def wait_for_volume_healthy(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_HEALTHY)


def wait_for_volume_restoration_completed(client, name):
    wait_for_volume_creation(client, name)
    monitor_restore_progress(client, name)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_INITIALRESTORATIONREQUIRED,
                                  False)


def wait_for_volume_degraded(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_DEGRADED)


def wait_for_volume_faulted(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_DETACHED)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_FAULTED)


def wait_for_volume_status(client, name, key, value):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume[key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume[key] == value
    return volume


def wait_for_volume_delete(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        found = False
        for volume in volumes:
            if volume["name"] == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_for_backup_volume_delete(client, name):
    for i in range(RETRY_COUNTS):
        bvs = client.list_backupVolume()
        found = False
        for bv in bvs:
            if bv["name"] == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_for_volume_current_image(client, name, image):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume["currentImage"] == image:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume["currentImage"] == image
    return volume


def wait_for_volume_replica_count(client, name, count):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if len(volume["replicas"]) == count:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(volume["replicas"]) == count
    return volume


def wait_for_snapshot_purge(client, volume_name, *snaps):
    completed = 0
    last_purge_progress = {}
    purge_status = {}
    for i in range(RETRY_COUNTS):
        completed = 0
        v = client.by_id_volume(volume_name)
        purge_status = v["purgeStatus"]
        for status in purge_status:
            assert status["error"] == ""

            progress = status["progress"]
            replica = status["replica"]
            last = last_purge_progress.get(status["replica"])
            assert last is None or last <= status["progress"]
            last_purge_progress[replica] = progress

            if status["state"] == "complete":
                assert progress == 100
                completed += 1
        if completed == len(purge_status):
            break
        time.sleep(RETRY_INTERVAL)
    assert completed == len(purge_status)

    # Now that the purge has been reported to be completed, the Snapshots
    # should be gone.
    found = False
    snapshots = v.snapshotList(volume=volume_name)
    snap_list = []
    for snap in snapshots:
        snap_list.append(snap["name"])
    for snap in snaps:
        if snap in snap_list:
            found = True
            break
    assert not found
    return v


def wait_for_engine_image_creation(client, image_name):
    for i in range(RETRY_COUNTS):
        images = client.list_engine_image()
        found = False
        for img in images:
            if img["name"] == image_name:
                found = True
                break
        if found:
            break
    assert found


def wait_for_engine_image_state(client, image_name, state):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image["state"] == state:
            break
        time.sleep(RETRY_INTERVAL)
    assert image["state"] == state
    return image


def wait_for_engine_image_ref_count(client, image_name, count):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image["refCount"] == count:
            break
        time.sleep(RETRY_INTERVAL)
    assert image["refCount"] == count
    if count == 0:
        assert image["noRefSince"] != ""
    return image


def json_string_go_to_python(str):
    return str.replace("u\'", "\"").replace("\'", "\""). \
        replace("True", "true").replace("False", "false")


def delete_replica_processes(client, api, volname):
    replica_managers = []

    volume = client.by_id_volume(volname)
    for r in volume["replicas"]:
        replica_managers.append(r["instanceManagerName"])

    list_command = [
        '/bin/sh', '-c',
        'longhorn-instance-manager process ls'
    ]
    for rm_name in replica_managers:
        with timeout(seconds=STREAM_EXEC_TIMEOUT,
                     error_message='Timeout on executing stream read'):
            ps_str = stream(
                api.connect_get_namespaced_pod_exec, rm_name,
                LONGHORN_NAMESPACE, command=list_command,
                stderr=True, stdin=False, stdout=True, tty=False)
            ps = json.loads(json_string_go_to_python(ps_str))
            deleted = False
            for name in ps:
                if volname in name:
                    delete_command = [
                        '/bin/sh', '-c',
                        'longhorn-instance-manager process delete ' +
                        '--name ' + name
                    ]
                    stream(api.connect_get_namespaced_pod_exec, rm_name,
                           LONGHORN_NAMESPACE, command=delete_command,
                           stderr=True, stdin=False, stdout=True,
                           tty=False)
                    deleted = True
                    break
            assert deleted


@pytest.fixture
def volume_name(request):
    return generate_volume_name()


@pytest.fixture
def pvc_name(request):
    return generate_volume_name()


@pytest.fixture
def csi_pvc_name(request):
    return generate_volume_name()


def generate_volume_name():
    return VOLUME_NAME + "-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def get_default_engine_image(client):
    images = client.list_engine_image()
    for img in images:
        if img["default"]:
            return img
    assert False


def get_compatibility_test_image(cli_v, cli_minv,
                                 ctl_v, ctl_minv,
                                 data_v, data_minv):
    return "%s.%d-%d.%d-%d.%d-%d" % (COMPATIBILTY_TEST_IMAGE_PREFIX,
                                     cli_v, cli_minv,
                                     ctl_v, ctl_minv,
                                     data_v, data_minv)


def generate_random_data(count):
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(count))


def check_volume_data(volume, data, check_checksum=True):
    dev = get_volume_endpoint(volume)
    check_device_data(dev, data, check_checksum)


def write_volume_random_data(volume, position={}):
    dev = get_volume_endpoint(volume)
    return write_device_random_data(dev, position={})


def check_device_data(dev, data, check_checksum=True):
    r_data = dev_read(dev, data['pos'], data['len'])
    assert r_data == data['content']
    if check_checksum:
        r_checksum = get_device_checksum(dev)
        assert r_checksum == data['checksum']


def write_device_random_data(dev, position={}):
    data = generate_random_data(VOLUME_RWTEST_SIZE)
    data_pos = generate_random_pos(VOLUME_RWTEST_SIZE, position)
    data_len = dev_write(dev, data_pos, data)
    checksum = get_device_checksum(dev)

    return {
        'content': data,
        'pos': data_pos,
        'len': data_len,
        'checksum': checksum
    }


def write_volume_data(volume, data):
    dev = get_volume_endpoint(volume)
    data_len = dev_write(dev, data['pos'], data['content'])
    checksum = get_device_checksum(dev)

    return {
        'content': data['content'],
        'pos': data['pos'],
        'len': data_len,
        'checksum': checksum
    }


def get_device_checksum(dev):
    hash = hashlib.sha512()

    with open(dev, 'rb') as fdev:
        if fdev is not None:
            for chunk in iter(lambda: fdev.read(4096), b""):
                hash.update(chunk)

    return hash.hexdigest()


def volume_read(v, start, count):
    dev = get_volume_endpoint(v)
    return dev_read(dev, start, count)


def dev_read(dev, start, count):
    r_data = ""
    fdev = open(dev, 'rb')
    if fdev is not None:
        fdev.seek(start)
        r_data = fdev.read(count)
        fdev.close()
    return r_data


def volume_write(v, start, data):
    dev = get_volume_endpoint(v)
    return dev_write(dev, start, data)


def dev_write(dev, start, data):
    w_length = 0
    fdev = open(dev, 'rb+')
    if fdev is not None:
        fdev.seek(start)
        fdev.write(data)
        fdev.close()
        w_length = len(data)
    return w_length


def volume_valid(dev):
    return stat.S_ISBLK(os.stat(dev).st_mode)


def parse_iscsi_endpoint(iscsi):
    iscsi_endpoint = iscsi[8:]
    return iscsi_endpoint.split('/')


def get_iscsi_ip(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    ip = iscsi_endpoint[0].split(':')
    return ip[0]


def get_iscsi_port(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    ip = iscsi_endpoint[0].split(':')
    return ip[1]


def get_iscsi_target(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    return iscsi_endpoint[1]


def get_iscsi_lun(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    return iscsi_endpoint[2]


def exec_nsenter(cmd):
    dockerd_pid = find_dockerd_pid() or "1"
    exec_cmd = ["nsenter", "--mount=/host/proc/{}/ns/mnt".format(dockerd_pid),
                "--net=/host/proc/{}/ns/net".format(dockerd_pid),
                "bash", "-c", cmd]
    return subprocess.check_output(exec_cmd)


def iscsi_login(iscsi_ep):
    ip = get_iscsi_ip(iscsi_ep)
    port = get_iscsi_port(iscsi_ep)
    target = get_iscsi_target(iscsi_ep)
    lun = get_iscsi_lun(iscsi_ep)
    # discovery
    cmd_discovery = "iscsiadm -m discovery -t st -p " + ip
    exec_nsenter(cmd_discovery)
    # login
    cmd_login = "iscsiadm -m node -T " + target + " -p " + ip + " --login"
    exec_nsenter(cmd_login)
    blk_name = "ip-%s:%s-iscsi-%s-lun-%s" % (ip, port, target, lun)
    wait_for_device_login(ISCSI_DEV_PATH, blk_name)
    dev = os.path.realpath(ISCSI_DEV_PATH + "/" + blk_name)
    return dev


def iscsi_logout(iscsi_ep):
    ip = get_iscsi_ip(iscsi_ep)
    target = get_iscsi_target(iscsi_ep)
    cmd_logout = "iscsiadm -m node -T " + target + " -p " + ip + " --logout"
    exec_nsenter(cmd_logout)
    cmd_rm_discovery = "iscsiadm -m discovery -p " + ip + " -o delete"
    exec_nsenter(cmd_rm_discovery)


def get_process_info(p_path):
    info = {}
    with open(p_path) as file:
        for line in file.readlines():
            if 'Name:\t' == line[0:len('Name:\t')]:
                info["Name"] = line[len("Name:"):].strip()
            if 'Pid:\t' == line[0:len('Pid:\t')]:
                info["Pid"] = line[len("Pid:"):].strip()
            if 'PPid:\t' == line[0:len('PPid:\t')]:
                info["PPid"] = line[len("PPid:"):].strip()
    if "Name" not in info or "Pid" not in info or "PPid" not in info:
        return
    return info


def find_self():
    return get_process_info("/host/proc/self/status")


def find_ancestor_process_by_name(ancestor_name):
    p = find_self()
    while True:
        if not p or p["Pid"] == "1":
            break
        if p["Name"] == ancestor_name:
            return p["Pid"]
        p = get_process_info("/host/proc/{}/status".format(p["PPid"]))
    return


def find_dockerd_pid():
    return find_ancestor_process_by_name("dockerd")


def generate_random_pos(size, used={}):
    for i in range(RETRY_COUNTS):
        pos = 0
        if int(SIZE) != size:
            pos = random.randrange(0, int(SIZE)-size, 1)
        collided = False
        # it's [start, end) vs [pos, pos + size)
        for start, end in used.items():
            if pos + size <= start or pos >= end:
                continue
            collided = True
            break
        if not collided:
            break
    assert not collided
    used[pos] = pos + size
    return pos


def get_upgrade_test_image(cli_v, cli_minv,
                           ctl_v, ctl_minv,
                           data_v, data_minv):
    return "%s.%d-%d.%d-%d.%d-%d" % (UPGRADE_TEST_IMAGE_PREFIX,
                                     cli_v, cli_minv,
                                     ctl_v, ctl_minv,
                                     data_v, data_minv)


def prepare_host_disk(dev, vol_name):
    cmd = ['mkfs.ext4', dev]
    subprocess.check_call(cmd)

    mount_path = os.path.join(DIRECTORY_PATH, vol_name)
    # create directory before mount
    cmd = ['mkdir', '-p', mount_path]
    subprocess.check_call(cmd)

    mount_disk(dev, mount_path)
    return mount_path


def mount_disk(dev, mount_path):
    cmd = ['mount', dev, mount_path]
    subprocess.check_call(cmd)


def umount_disk(mount_path):
    cmd = ['umount', mount_path]
    subprocess.check_call(cmd)


def lazy_umount_disk(mount_path):
    cmd = ['umount', '-l', mount_path]
    subprocess.check_call(cmd)


def cleanup_host_disk(vol_name):
    mount_path = os.path.join(DIRECTORY_PATH, vol_name)
    umount_disk(mount_path)

    cmd = ['rm', '-r', mount_path]
    subprocess.check_call(cmd)


def wait_for_volume_condition_scheduled(client, name, key, value):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        conditions = volume["conditions"]
        if conditions is not None and \
                conditions != {} and \
                conditions[VOLUME_CONDITION_SCHEDULED] and \
                conditions[VOLUME_CONDITION_SCHEDULED][key] and \
                conditions[VOLUME_CONDITION_SCHEDULED][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    conditions = volume["conditions"]
    assert conditions[VOLUME_CONDITION_SCHEDULED][key] == value
    return volume


def get_host_disk_size(disk):
    cmd = ['stat', '-fc',
           '{"path":"%n","fsid":"%i","type":"%T","freeBlock":%f,'
           '"totalBlock":%b,"blockSize":%S}',
           disk]
    output = subprocess.check_output(cmd)
    disk_info = json.loads(output)
    block_size = disk_info["blockSize"]
    free_blk = disk_info["freeBlock"]
    total_blk = disk_info["totalBlock"]
    free = (free_blk * block_size)
    total = (total_blk * block_size)
    return free, total


def wait_for_disk_status(client, name, fsid, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        disks = node["disks"]
        disk = disks[fsid]
        if str(disk[key]) == str(value):
            break
        time.sleep(RETRY_INTERVAL)
    return node


def wait_for_disk_conditions(client, name, fsid, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        disks = node["disks"]
        disk = disks[fsid]
        conditions = disk["conditions"]
        if conditions[key]["status"] == value:
            break
        time.sleep(RETRY_INTERVAL)
    assert conditions[key]["status"] == value
    return node


def wait_for_node_update(client, name, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        if str(node[key]) == str(value):
            break
        time.sleep(RETRY_INTERVAL)
    assert str(node[key]) == str(value)
    return node


def wait_for_disk_update(client, name, disk_num):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        if len(node["disks"]) == disk_num:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(node["disks"]) == disk_num
    return node


def get_volume_engine(v):
    engines = v["controllers"]
    assert len(engines) != 0
    return engines[0]


def get_volume_endpoint(v):
    engine = get_volume_engine(v)
    endpoint = engine["endpoint"]
    assert endpoint != ""
    return endpoint


def get_volume_attached_nodes(v):
    nodes = []
    engines = v["controllers"]
    for e in engines:
        node = e["hostId"]
        if node != "":
            nodes.append(node)
    return nodes


def wait_for_backup_completion(client, volume_name, snapshot_name):
    completed = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        for b in v["backupStatus"]:
            assert b["error"] == ""
            if b["snapshot"] == snapshot_name and b["state"] == "complete":
                assert b["progress"] == 100
                completed = True
                break
        if completed:
            break
        time.sleep(RETRY_INTERVAL)
    assert completed is True
    return v


def monitor_restore_progress(client, volume_name):
    completed = 0
    rs = {}
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        rs = v["restoreStatus"]
        for r in rs:
            assert r["error"] == ""
            if r["state"] == "complete":
                assert r["progress"] == 100
                completed += 1
        if completed == len(rs):
            break
        time.sleep(RETRY_INTERVAL)
    assert completed == len(rs)
    return v


def wait_for_volume_migration_ready(client, volume_name):
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        engines = v["controllers"]
        ready = True
        if len(engines) == 2:
            for e in v["controllers"]:
                if e["endpoint"] == "":
                    ready = False
                    break
        else:
            ready = False
        if ready:
            break
        time.sleep(RETRY_INTERVAL)
    assert ready
    return v


def wait_for_volume_migration_node(client, volume_name, node_id):
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        engines = v["controllers"]
        replicas = v["replicas"]
        if len(engines) == 1 and len(replicas) == v["numberOfReplicas"]:
            e = engines[0]
            if e["endpoint"] != "":
                break
        time.sleep(RETRY_INTERVAL)
    assert e["hostId"] == node_id
    assert e["endpoint"] != ""
    return v


def get_random_client(clients):
    for _, client in clients.iteritems():
        break
    return client


def get_update_disks(disks):
    update_disk = []
    for key, disk in disks.iteritems():
        update_disk.append(disk)
    return update_disk


def reset_node(client):
    nodes = client.list_node()
    for node in nodes:
        try:
            node = client.update(node, allowScheduling=True)
            wait_for_node_update(client, node["id"],
                                 "allowScheduling", True)
        except Exception as e:
            print "Exception when reset node schedulding", node, e
            pass


def cleanup_test_disks(client):
    del_dirs = os.listdir(DIRECTORY_PATH)
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    disks = node["disks"]
    for fsid, disk in disks.iteritems():
        for del_dir in del_dirs:
            dir_path = os.path.join(DIRECTORY_PATH, del_dir)
            if dir_path == disk["path"]:
                disk["allowScheduling"] = False
    update_disks = get_update_disks(disks)
    try:
        node = node.diskUpdate(disks=update_disks)
        disks = node["disks"]
        for fsid, disk in disks.iteritems():
            for del_dir in del_dirs:
                dir_path = os.path.join(DIRECTORY_PATH, del_dir)
                if dir_path == disk["path"]:
                    wait_for_disk_status(client, host_id, fsid,
                                         "allowScheduling", False)
    except Exception as e:
        print "Exception when update node disks", node, e
        pass

    # delete test disks
    disks = node["disks"]
    update_disks = []
    for fsid, disk in disks.iteritems():
        if disk["allowScheduling"]:
            update_disks.append(disk)
    try:
        node.diskUpdate(disks=update_disks)
        wait_for_disk_update(client, host_id, len(update_disks))
    except Exception as e:
        print "Exception when delete node test disks", node, e
        pass
    # cleanup host disks
    for del_dir in del_dirs:
        try:
            cleanup_host_disk(del_dir)
        except Exception as e:
            print "Exception when cleanup host disk", del_dir, e
            pass


def reset_disks_for_all_nodes(client):  # NOQA
    nodes = client.list_node()
    for node in nodes:
        if len(node["disks"]) == 0:
            default_disk = {"path": DEFAULT_DISK_PATH, "allowScheduling": True}
            node = node.diskUpdate(disks=[default_disk])
            node = wait_for_disk_update(client, node["name"], 1)
            assert(len(node["disks"])) == 1
        # wait for node controller to update disk status
        disks = node["disks"]
        update_disks = []
        for fsid, disk in disks.iteritems():
            update_disk = disk
            update_disk["allowScheduling"] = True
            update_disk["storageReserved"] = \
                update_disk["storageMaximum"] * 30 / 100
            update_disks.append(update_disk)
        node = node.diskUpdate(disks=update_disks)
        for fsid, disk in node["disks"].iteritems():
            # wait for node controller update disk status
            wait_for_disk_status(client, node["name"], fsid,
                                 "allowScheduling", True)
            wait_for_disk_status(client, node["name"], fsid,
                                 "storageScheduled", 0)
            wait_for_disk_status(client, node["name"], fsid,
                                 "storageReserved",
                                 update_disk["storageMaximum"] * 30 / 100)


def reset_settings(client):
    minimal_setting = client.by_id_setting(
        SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    try:
        client.update(minimal_setting,
                      value=DEFAULT_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE)
    except Exception as e:
        print "Exception when update " \
              "storage minimal available percentage settings", \
            minimal_setting, e
        pass

    over_provisioning_setting = client.by_id_setting(
        SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    try:
        client.update(over_provisioning_setting,
                      value=DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE)
    except Exception as e:
        print "Exception when update " \
              "storage over provisioning percentage settings", \
            over_provisioning_setting, e


def wait_for_node_mountpropagation_condition(client, name):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        conditions = {}
        if "conditions" in node.keys():
            conditions = node["conditions"]
        if NODE_CONDITION_MOUNTPROPAGATION in \
                conditions.keys() and \
                "status" in \
                conditions[NODE_CONDITION_MOUNTPROPAGATION].keys() \
                and conditions[NODE_CONDITION_MOUNTPROPAGATION]["status"] != \
                CONDITION_STATUS_UNKNOWN:
            break
        time.sleep(RETRY_INTERVAL)
    return node


class timeout:

    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise Exception(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def is_backupTarget_s3(s):
    return s.startswith("s3://")


def is_backupTarget_nfs(s):
    return s.startswith("nfs://")


def find_backup(client, vol_name, snap_name):
    found = False
    for i in range(100):
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv["name"] == vol_name:
                found = True
                break
        if found:
            break
        time.sleep(1)
    assert found

    found = False
    for i in range(20):
        backups = bv.backupList().data
        for b in backups:
            if b["snapshotName"] == snap_name:
                found = True
                break
        if found:
            break
        time.sleep(1)
    assert found

    return bv, b


def check_longhorn(core_api):
    ready = False

    has_engine_image = False
    has_driver_deployer = False
    has_manager = False
    has_ui = False

    try:
        longhorn_pod_list = core_api.list_namespaced_pod(
            'longhorn-system', include_uninitialized=False)
        for item in longhorn_pod_list.items:
            labels = item.metadata.labels
            if not labels:
                pass
            elif labels.get('longhorn', '') == 'engine-image':
                has_engine_image = True
            elif labels.get('app', '') == 'longhorn-driver-deployer':
                has_driver_deployer = True
            elif labels.get('app', '') == 'longhorn-manager':
                has_manager = True
            elif labels.get('app', '') == 'longhorn-ui':
                has_ui = True

        if has_engine_image and has_driver_deployer and has_manager and has_ui:
            ready = True

    except ApiException as e:
        if (e.status == 404):
            ready = False

    assert ready


def check_csi(core_api):
    using_csi = CSI_UNKNOWN

    has_attacher = False
    has_provisioner = False
    has_csi_plugin = False

    try:
        longhorn_pod_list = core_api.list_namespaced_pod(
            'longhorn-system', include_uninitialized=False)
        for item in longhorn_pod_list.items:
            labels = item.metadata.labels
            if not labels:
                pass
            elif labels.get('app', '') == 'csi-attacher':
                has_attacher = True
            elif labels.get('app', '') == 'csi-provisioner':
                has_provisioner = True
            elif labels.get('app', '') == 'longhorn-csi-plugin':
                has_csi_plugin = True

        if has_attacher and has_provisioner and has_csi_plugin:
            using_csi = CSI_TRUE
        elif not has_attacher and not has_provisioner and not has_csi_plugin:
            using_csi = CSI_FALSE

    except ApiException as e:
        if (e.status == 404):
            using_csi = CSI_FALSE

    assert using_csi != CSI_UNKNOWN

    return True if using_csi == CSI_TRUE else False


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


def delete_storage_class(sc_name):
    api = get_storage_api_client()
    try:
        api.delete_storage_class(sc_name, body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404


def update_statefulset_manifests(ss_manifest, sc_manifest, name):
    """
    Write in a new StatefulSet name and the proper StorageClass name for tests.
    """
    ss_manifest['metadata']['name'] = \
        ss_manifest['spec']['selector']['matchLabels']['app'] = \
        ss_manifest['spec']['serviceName'] = \
        ss_manifest['spec']['template']['metadata']['labels']['app'] = \
        name
    ss_manifest['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = DEFAULT_STORAGECLASS_NAME
    sc_manifest['metadata']['name'] = DEFAULT_STORAGECLASS_NAME


def check_volume_existence(client, volume_name):
    volumes = client.list_volume()
    for volume in volumes:
        if volume["name"] == volume_name:
            return True
    return False


def check_pod_existence(api, pod_name, namespace="default"):
    pods = api.list_namespaced_pod(namespace)
    for pod in pods.items:
        if pod.metadata.name == pod_name and \
                not pod.metadata.deletion_timestamp:
            return True
    return False


def check_pvc_existence(api, pvc_name, namespace="default"):
    pvcs = api.list_namespaced_persistent_volume_claim(namespace)
    for pvc in pvcs.items:
        if pvc.metadata.name == pvc_name and not \
                pvc.metadata.deletion_timestamp:
            return True
    return False


def check_pv_existence(api, pv_name):
    pvs = api.list_persistent_volume()
    for pv in pvs.items:
        if pv.metadata.name == pv_name and not pv.metadata.deletion_timestamp:
            return True
    return False


def check_statefulset_existence(api, ss_name, namespace="default"):
    ss_list = api.list_namespaced_stateful_set(namespace)
    for ss in ss_list.items:
        if ss.metadata.name == ss_name and not ss.metadata.deletion_timestamp:
            return True
    return False


def delete_and_wait_pvc(api, pvc_name):
    try:
        api.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace='default',
            body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

    wait_delete_pvc(api, pvc_name)


def wait_delete_pvc(api, pvc_name):
    for i in range(RETRY_COUNTS):
        found = False
        ret = api.list_namespaced_persistent_volume_claim(namespace='default')
        for item in ret.items:
            if item.metadata.name == pvc_name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def delete_and_wait_pv(api, pv_name):
    try:
        api.delete_persistent_volume(
            name=pv_name, body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

    wait_delete_pv(api, pv_name)


def wait_delete_pv(api, pv_name):
    for i in range(RETRY_COUNTS):
        found = False
        pvs = api.list_persistent_volume()
        for item in pvs.items:
            if item.metadata.name == pv_name:
                if item.status.phase == 'Failed':
                    try:
                        api.delete_persistent_volume(
                            name=pv_name, body=k8sclient.V1DeleteOptions())
                    except ApiException as e:
                        assert e.status == 404
                else:
                    found = True
                    break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_volume_kubernetes_status(client, volume_name, expect_ks):
    for i in range(RETRY_COUNTS):
        expected = True
        volume = client.by_id_volume(volume_name)
        ks = volume["kubernetesStatus"]
        for k, v in expect_ks.items():
            if k in ('lastPVCRefAt', 'lastPodRefAt'):
                if (v != '' and ks[k] == '') or (v == '' and ks[k] != ''):
                    expected = False
                    break
            else:
                if ks[k] != v:
                    expected = False
                    break
        if expected:
            break
        time.sleep(RETRY_INTERVAL)
    assert expected


def create_pv_for_volume(client, core_api, volume, pv_name):
    volume.pvCreate(pvName=pv_name)
    for i in range(RETRY_COUNTS):
        if check_pv_existence(core_api, pv_name):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pv_existence(core_api, pv_name)

    ks = {
        'pvName': pv_name,
        'pvStatus': 'Available',
        'namespace': '',
        'lastPVCRefAt': '',
        'lastPodRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume['name'], ks)


def create_pvc_for_volume(client, core_api, volume, pvc_name):
    volume.pvcCreate(namespace="default", pvcName=pvc_name)
    for i in range(RETRY_COUNTS):
        if check_pvc_existence(core_api, pvc_name):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pvc_existence(core_api, pvc_name)

    ks = {
        'pvStatus': 'Bound',
        'namespace': 'default',
        'lastPVCRefAt': '',
    }
    wait_volume_kubernetes_status(client, volume['name'], ks)


def activate_standby_volume(client, volume_name, frontend="blockdev"):
    volume = client.by_id_volume(volume_name)
    assert volume['standby'] is True
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        engines = volume["controllers"]
        if len(engines) != 1 or \
                engines[0]["lastRestoredBackup"] != volume['lastBackup']:
            time.sleep(RETRY_INTERVAL)
            continue
        try:
            volume.activate(frontend=frontend)
            break
        except Exception as e:
            assert "hasn't finished incremental restored" \
                   in str(e.error.message)
            time.sleep(RETRY_INTERVAL)
    volume = client.by_id_volume(volume_name)
    assert volume['standby'] is False
    assert volume['frontend'] == "blockdev"

    wait_for_volume_detached(client, volume_name)

    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert engine["lastRestoredBackup"] == ""
    assert engine["requestedBackupRestore"] == ""


def check_volume_last_backup(client, volume_name, last_backup):
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        if volume['lastBackup'] == last_backup:
            break
        time.sleep(RETRY_INTERVAL)
    volume = client.by_id_volume(volume_name)
    assert volume['lastBackup'] == last_backup
