import time
import os
import stat
import random
import string
import subprocess
import json
import hashlib

import pytest

import cattle

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.stream import stream

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

RETRY_COUNTS = 300
RETRY_ITERVAL = 0.5

LONGHORN_NAMESPACE = "longhorn-system"

COMPATIBILTY_TEST_IMAGE_PREFIX = "rancher/longhorn-test:version-test"
UPGRADE_TEST_IMAGE_PREFIX = "rancher/longhorn-test:upgrade-test"

ISCSI_DEV_PATH = "/dev/disk/by-path"

VOLUME_FIELD_STATE = "state"
VOLUME_STATE_ATTACHED = "attached"
VOLUME_STATE_DETACHED = "detached"

VOLUME_FIELD_ROBUSTNESS = "robustness"
VOLUME_ROBUSTNESS_HEALTHY = "healthy"
VOLUME_ROBUSTNESS_FAULTED = "faulted"

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
DEFAULT_DISK_PATH = "/var/lib/rancher/longhorn"
DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE = "500"
DEFAULT_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = "10"

NODE_CONDITION_MOUNTPROPAGATION = "MountPropagation"
DISK_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_READY = "Ready"


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
    api.delete_namespaced_pod(
        name=pod_name,
        namespace='default',
        body=k8sclient.V1DeleteOptions())
    wait_delete_pod(api, pod_name)


def delete_and_wait_statefulset(api, client, statefulset):
    pod_data = get_statefulset_pod_info(api, statefulset)

    apps_api = get_apps_api_client()
    apps_api.delete_namespaced_stateful_set(
        name=statefulset['metadata']['name'],
        namespace='default', body=k8sclient.V1DeleteOptions())

    for i in range(DEFAULT_POD_TIMEOUT):
        ret = apps_api.list_namespaced_stateful_set(namespace='default')
        found = False
        for item in ret.items:
            if item.metadata.name == \
              statefulset['metadata']['name']:
                found = True
                break
        if not found:
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert not found
    # We need to generate the names for the PVCs on our own so we can
    # delete them.
    client = get_longhorn_api_client()
    for pod in pod_data:
        # Wait on Pods too, we apparently had timeout issues with them.
        wait_delete_pod(api, pod['pod_name'])
        api.delete_namespaced_persistent_volume_claim(
            name=pod['pvc_name'], namespace='default',
            body=k8sclient.V1DeleteOptions())
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
                    if item.status.phase == 'Failed':
                        api.delete_persistent_volume(
                            name=pod['pv_name'],
                            body=k8sclient.V1DeleteOptions())

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
    v = wait_for_volume_detached(client, name)
    client.delete(v)
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
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=read_command, stderr=True, stdin=False, stdout=True,
        tty=False)


def write_volume_data(api, pod_name, test_data):
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
        'echo -ne ' + test_data + ' > /data/test; sync'
    ]
    stream(
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
            except Exception:
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
        api.delete_persistent_volume(name=pv_manifest['metadata']['name'],
                                     body=k8sclient.V1DeleteOptions())

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
        claim = api.read_namespaced_persistent_volume_claim(
            name=pvc_manifest['metadata']['name'], namespace='default')
        volume_name = claim.spec.volume_name

        api = get_core_api_client()
        api.delete_namespaced_persistent_volume_claim(
            name=pvc_manifest['metadata']['name'], namespace='default',
            body=k8sclient.V1DeleteOptions())

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
        api.delete_storage_class(name=sc_manifest['metadata']['name'],
                                 body=k8sclient.V1DeleteOptions())

    request.addfinalizer(finalizer)

    return sc_manifest


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
    c = cattle.from_env(url=url)
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


def wait_for_device_login(dest_path, name):
    dev = ""
    for i in range(RETRY_COUNTS):
        files = os.listdir(dest_path)
        if name in files:
            dev = name
            break
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
    assert not found


def wait_for_volume_current_image(client, name, image):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume["currentImage"] == image:
            break
        time.sleep(RETRY_ITERVAL)
    assert volume["currentImage"] == image
    return volume


def wait_for_volume_replica_count(client, name, count):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if len(volume["replicas"]) == count:
            break
        time.sleep(RETRY_ITERVAL)
    assert len(volume["replicas"]) == count
    return volume


def wait_for_snapshot_purge(volume, *snaps):
    for i in range(RETRY_COUNTS):
        snapshots = volume.snapshotList(volume=volume["name"])
        snapMap = {}
        for snap in snapshots:
            snapMap[snap["name"]] = snap
        found = False
        for snap in snaps:
            if snap in snapMap:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_ITERVAL)
    assert not found


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
        time.sleep(RETRY_ITERVAL)
    assert image["state"] == state
    return image


def wait_for_engine_image_ref_count(client, image_name, count):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image["refCount"] == count:
            break
        time.sleep(RETRY_ITERVAL)
    assert image["refCount"] == count
    if count == 0:
        assert image["noRefSince"] != ""
    return image


def k8s_delete_replica_pods_for_volume(volname):
    k8sclient.CoreV1Api().delete_collection_namespaced_pod(
        label_selector="longhorn-volume-replica="+volname,
        namespace=LONGHORN_NAMESPACE,
        watch=False)


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


def check_volume_data(volume, data):
    dev = get_volume_endpoint(volume)
    check_device_data(dev, data)


def write_volume_random_data(volume, position={}):
    dev = get_volume_endpoint(volume)
    return write_device_random_data(dev, position={})


def check_device_data(dev, data):
    r_data = dev_read(dev, data['pos'], data['len'])
    assert r_data == data['content']
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
    exec_cmd = "nsenter --mount=/host/proc/1/ns/mnt \
               --net=/host/proc/1/ns/net bash -c \"" + cmd + "\""
    fp = os.popen(exec_cmd)
    ret = fp.read()
    fp.close()
    return ret


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
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
    return node


def wait_for_disk_conditions(client, name, fsid, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        disks = node["disks"]
        disk = disks[fsid]
        conditions = disk["conditions"]
        if conditions[key]["status"] == value:
            break
        time.sleep(RETRY_ITERVAL)
    assert conditions[key]["status"] == value
    return node


def wait_for_node_update(client, name, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        if str(node[key]) == str(value):
            break
        time.sleep(RETRY_ITERVAL)
    assert str(node[key]) == str(value)
    return node


def wait_for_disk_update(client, name, disk_num):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        if len(node["disks"]) == disk_num:
            break
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
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
        time.sleep(RETRY_ITERVAL)
    return node
