import fcntl
import struct
import time
import os
import stat
import random
import string
import subprocess
import json
import hashlib
import signal

import socket
import pytest

import longhorn
import requests
import warnings

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.stream import stream

from kubernetes.client.rest import ApiException
from datetime import datetime

Ki = 1024
Mi = (1024 * 1024)
Gi = (1024 * Mi)

SIZE = str(16 * Mi)
EXPAND_SIZE = str(32 * Mi)
VOLUME_NAME = "longhorn-testvol"
STATEFULSET_NAME = "longhorn-teststs"
DEV_PATH = "/dev/longhorn/"
VOLUME_RWTEST_SIZE = 512
VOLUME_INVALID_POS = -1

BACKING_IMAGE_NAME = "bi-test"
BACKING_IMAGE_QCOW2_URL = \
    "https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2"
BACKING_IMAGE_QCOW2_CHECKSUM = \
    "bd79ab9e6d45abf4f3f0adf552a868074dd235c4698ce7258d521160e0ad79ffe555b94" \
    "e7d4007add6e1a25f4526885eb25c53ce38f7d344dd4925b9f2cb5d3b"
BACKING_IMAGE_RAW_URL = \
    "https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw"
BACKING_IMAGE_RAW_CHECKSUM = \
    "304f3ed30ca6878e9056ee6f1b02b328239f0d0c2c1272840998212f9734b196371560b" \
    "3b939037e4f4c2884ce457c2cbc9f0621f4f5d1ca983983c8cdf8cd9a"
BACKING_IMAGE_EXT4_SIZE = 32 * Mi

PORT = ":9500"

RETRY_COMMAND_COUNT = 3
RETRY_COUNTS = 300
RETRY_INTERVAL = 0.5
RETRY_INTERVAL_LONG = 2
RETRY_BACKUP_COUNTS = 300
RETRY_BACKUP_INTERVAL = 1
RETRY_SNAPSHOT_INTERVAL = 1
RETRY_EXEC_COUNTS = 30
RETRY_EXEC_INTERVAL = 5

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
VOLUME_ROBUSTNESS_UNKNOWN = "unknown"

VOLUME_FIELD_RESTOREREQUIRED = "restoreRequired"
VOLUME_FIELD_READY = "ready"

VOLUME_FIELD_CLONE_STATUS = "cloneStatus"
VOLUME_FIELD_CLONE_COMPLETED = "completed"

VOLUME_REPLICA_WO_LIMIT = 1

DEFAULT_STORAGECLASS_NAME = 'longhorn-test'

DEFAULT_LONGHORN_PARAMS = {
    'numberOfReplicas': '3',
    'staleReplicaTimeout': '30'
}

DEFAULT_BACKUP_TIMEOUT = 100

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180

DEFAULT_STATEFULSET_INTERVAL = 1
DEFAULT_STATEFULSET_TIMEOUT = 180

DEFAULT_DEPLOYMENT_INTERVAL = 1
DEFAULT_DEPLOYMENT_TIMEOUT = 120


DEFAULT_VOLUME_SIZE = 3  # In Gi
EXPANDED_VOLUME_SIZE = 4  # In Gi

DIRECTORY_PATH = '/tmp/longhorn-test/'

VOLUME_CONDITION_SCHEDULED = "scheduled"
VOLUME_CONDITION_RESTORE = "restore"
VOLUME_CONDITION_STATUS = "status"
VOLUME_CONDITION_TOOMANYSNAPSHOTS = "toomanysnapshots"

CONDITION_STATUS_TRUE = "True"
CONDITION_STATUS_FALSE = "False"
CONDITION_STATUS_UNKNOWN = "Unknown"

CONDITION_REASON_SCHEDULING_FAILURE = "ReplicaSchedulingFailure"

VOLUME_FRONTEND_BLOCKDEV = "blockdev"
VOLUME_FRONTEND_ISCSI = "iscsi"

DEFAULT_DISK_PATH = "/var/lib/longhorn/"
DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE = "200"
DEFAULT_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = "10"
DEFAULT_LONGHORN_STATIC_STORAGECLASS_NAME = "longhorn-static"

DEFAULT_REPLICA_DIRECTORY = os.path.join(DEFAULT_DISK_PATH, "replicas/")

NODE_CONDITION_MOUNTPROPAGATION = "MountPropagation"
NODE_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_READY = "Ready"

STREAM_EXEC_TIMEOUT = 60

SETTING_AUTO_SALVAGE = "auto-salvage"
SETTING_BACKUP_TARGET = "backup-target"
SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
SETTING_BACKUPSTORE_POLL_INTERVAL = "backupstore-poll-interval"
SETTING_CREATE_DEFAULT_DISK_LABELED_NODES = "create-default-disk-labeled-nodes"
SETTING_DEFAULT_DATA_LOCALITY = "default-data-locality"
SETTING_DEFAULT_DATA_PATH = "default-data-path"
SETTING_DEFAULT_LONGHORN_STATIC_SC = "default-longhorn-static-storage-class"
SETTING_DEFAULT_REPLICA_COUNT = "default-replica-count"
SETTING_DEGRADED_AVAILABILITY = \
    "allow-volume-creation-with-degraded-availability"
SETTING_DISABLE_SCHEDULING_ON_CORDONED_NODE = \
    "disable-scheduling-on-cordoned-node"
SETTING_GUARANTEED_ENGINE_CPU = "guaranteed-engine-cpu"
SETTING_GUARANTEED_ENGINE_MANAGER_CPU = "guaranteed-engine-manager-cpu"
SETTING_GUARANTEED_REPLICA_MANAGER_CPU = "guaranteed-replica-manager-cpu"
SETTING_MKFS_EXT4_PARAMS = "mkfs-ext4-parameters"
SETTING_PRIORITY_CLASS = "priority-class"
SETTING_RECURRING_JOB_WHILE_VOLUME_DETACHED = \
    "allow-recurring-job-while-volume-detached"
SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY = "replica-soft-anti-affinity"
SETTING_REPLICA_AUTO_BALANCE = "replica-auto-balance"
SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL = \
    "replica-replenishment-wait-interval"
SETTING_REPLICA_ZONE_SOFT_ANTI_AFFINITY = "replica-zone-soft-anti-affinity"
SETTING_STORAGE_OVER_PROVISIONING_PERCENTAGE = \
    "storage-over-provisioning-percentage"
SETTING_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = \
    "storage-minimal-available-percentage"
SETTING_TAINT_TOLERATION = "taint-toleration"
SETTING_BACKING_IMAGE_CLEANUP_WAIT_INTERVAL = \
    "backing-image-cleanup-wait-interval"
SETTING_DISABLE_REVISION_COUNTER = "disable-revision-counter"

CSI_UNKNOWN = 0
CSI_TRUE = 1
CSI_FALSE = 2

KUBERNETES_STATUS_LABEL = "KubernetesStatus"

# https://github.com/kubernetes/kubernetes/blob/a9f0db16614ae62563ead2018f1692407bd93d8f/pkg/apis/scheduling/types.go#L29  # NOQA
PRIORITY_CLASS_MAX = 1000000000
PRIORITY_CLASS_MIN = 1
PRIORITY_CLASS_NAME = "priority-class"

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

INSTANCE_MANAGER_HOST_PATH_PREFIX = "/host"
EXPANSION_SNAP_TMP_META_NAME_PATTERN = "volume-snap-expand-%s.img.meta.tmp"

DATA_SIZE_IN_MB_1 = 100
DATA_SIZE_IN_MB_2 = 300
DATA_SIZE_IN_MB_3 = 500
DATA_SIZE_IN_MB_4 = 800

MESSAGE_TYPE_ERROR = "error"

BACKUP_BLOCK_SIZE = 2 * Mi

# label deprecated for k8s >= v1.17
DEPRECATED_K8S_ZONE_LABEL = "failure-domain.beta.kubernetes.io/zone"

K8S_ZONE_LABEL = "topology.kubernetes.io/zone"

BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD = "download"
BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME = "export-from-volume"

JOB_LABEL = "recurring-job.longhorn.io"

MAX_SUPPORT_BINDLE_NUMBER = 20


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


def get_scheduling_api_client():
    load_k8s_config()
    return k8sclient.SchedulingV1Api()


def get_storage_api_client():
    load_k8s_config()
    return k8sclient.StorageV1Api()


def get_version_api_client():
    load_k8s_config()
    return k8sclient.VersionApi()


def get_custom_object_api_client():
    load_k8s_config()
    return k8sclient.CustomObjectsApi()


def get_longhorn_api_client():
    for i in range(RETRY_COUNTS):
        try:
            k8sconfig.load_incluster_config()
            ips = get_mgr_ips()

            # check if longhorn manager port is open before calling get_client
            for ip in ips:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                mgr_port_open = sock.connect_ex((ip, 9500))

                if mgr_port_open == 0:
                    client = get_client(ip + PORT)
                    break
            return client
        except Exception:
            time.sleep(RETRY_INTERVAL)


def cleanup_volume(client, volume):
    """
    Clean up the volume after the test.
    :param client: The Longhorn client to use in the request.
    :param volume: The volume to clean up.
    """
    volume.detach(hostId="")
    volume = wait_for_volume_detached(client, volume.name)
    client.delete(volume)
    wait_for_volume_delete(client, volume.name)
    volumes = client.list_volume()
    assert len(volumes) == 0


def cleanup_all_volumes(client):
    """
    Clean up all volumes
    :param client: The Longhorn client to use in the request.
    """

    volumes = client.list_volume()
    for v in volumes:
        # ignore the error when clean up
        try:
            client.delete(v)
        except Exception as e:
            print("\nException when cleanup volume ", v)
            print(e)
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        if len(volumes) == 0:
            break
        time.sleep(RETRY_INTERVAL)

    volumes = client.list_volume()
    assert len(volumes) == 0


def create_backup(client, volname, data={}, labels={}):
    volume = client.by_id_volume(volname)
    create_snapshot(client, volname)
    if not data:
        data = write_volume_random_data(volume)
    else:
        data = write_volume_data(volume, data)
    snap = create_snapshot(client, volname)
    create_snapshot(client, volname)

    # after backup request we need to wait for completion of the backup
    # since the backup.cfg will only be available once the backup operation
    # has been completed
    volume.snapshotBackup(name=snap.name, labels=labels)
    wait_for_backup_completion(client, volname, snap.name)

    verified = False
    for i in range(RETRY_COMMAND_COUNT):
        bv, b = find_backup(client, volname, snap.name)
        new_b = bv.backupGet(name=b.name)
        if new_b.name == b.name and \
           new_b.url == b.url and \
           new_b.snapshotName == b.snapshotName and \
           new_b.snapshotCreated == b.snapshotCreated and \
           new_b.created == b.created and \
           new_b.volumeName == b.volumeName and \
           new_b.volumeSize == b.volumeSize and \
           new_b.volumeCreated == b.volumeCreated:
            verified = True
            break
        time.sleep(RETRY_INTERVAL)
    assert verified

    # Don't directly compare the Label dictionaries, since the server could
    # have added extra Labels.
    for key, val in iter(labels.items()):
        assert new_b.labels.get(key) == val

    volume = wait_for_volume_status(client, volname,
                                    "lastBackup",
                                    b.name)
    assert volume.lastBackupAt != ""

    return bv, b, snap, data


def wait_for_backup_count(backup_volume, number, retry_counts=120):
    ok = False
    for _ in range(retry_counts):

        complete_backup_cnt = 0
        for single_backup in backup_volume.backupList():
            if single_backup.state == "Completed" and \
                                        int(single_backup.volumeSize) > 0:
                complete_backup_cnt = complete_backup_cnt + 1

        if complete_backup_cnt == number:
            ok = True
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert ok


def delete_backup(client, volume_name, backup_name):
    backup_volume = client.by_id_backupVolume(volume_name)
    backup_volume.backupDelete(name=backup_name)
    wait_for_backup_delete(client, volume_name, backup_name)


def delete_backup_volume(client, volume_name):
    bv = client.by_id_backupVolume(volume_name)
    client.delete(bv)
    wait_for_backup_volume_delete(client, volume_name)


def create_and_check_volume(client, volume_name,
                            num_of_replicas=3, size=SIZE, backing_image="",
                            frontend=VOLUME_FRONTEND_BLOCKDEV):
    """
    Create a new volume with the specified parameters. Assert that the new
    volume is detached and that all of the requested parameters match.

    :param client: The Longhorn client to use in the request.
    :param volume_name: The name of the volume.
    :param num_of_replicas: The number of replicas the volume should have.
    :param size: The size of the volume, as a string representing the number
    of bytes.
    :param backing_image: The backing image to use for the volume.
    :param frontend: The frontend to use for the volume.
    :return: The volume instance created.
    """
    if not backing_image_feature_supported(client):
        backing_image = None
    client.create_volume(name=volume_name, size=size,
                         numberOfReplicas=num_of_replicas,
                         backingImage=backing_image, frontend=frontend)
    volume = wait_for_volume_detached(client, volume_name)
    assert volume.name == volume_name
    assert volume.size == size
    assert volume.numberOfReplicas == num_of_replicas
    assert volume.state == "detached"
    if backing_image_feature_supported(client):
        assert volume.backingImage == backing_image
    assert volume.frontend == frontend
    assert volume.created != ""
    return volume


def wait_pod(pod_name):
    api = get_core_api_client()

    pod = None
    for i in range(DEFAULT_POD_TIMEOUT):
        pod = api.read_namespaced_pod(
            name=pod_name,
            namespace='default')
        if pod is not None and pod.status.phase != 'Pending':
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert pod is not None and pod.status.phase == 'Running'


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

    pod_name = pod_manifest['metadata']['name']

    wait_pod(pod_name)


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


def delete_and_wait_pod(api, pod_name, namespace='default', wait=True):
    """
    Delete a specified Pod.

    This function does not check if the Pod does exist and will throw an error
    if a nonexistent Pod is specified.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
    """
    target_pod = None
    try:
        target_pod = api.read_namespaced_pod(name=pod_name,
                                             namespace=namespace)
    except ApiException as e:
        assert e.status == 404
        return

    try:
        api.delete_namespaced_pod(
            name=pod_name, namespace=namespace,
            body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404
        return

    if wait:
        wait_delete_pod(api, target_pod.metadata.uid, namespace=namespace)


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
        wait_delete_pod(api, pod['pod_uid'])
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
            'pod_uid': pod.metadata.uid,
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


def read_volume_data(api, pod_name, filename='test'):
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
        'cat /data/' + filename
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=read_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def write_pod_volume_data(api, pod_name, test_data, filename='test'):
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
        'echo -ne ' + test_data + ' > /data/' + filename
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream write'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=write_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def write_pod_block_volume_data(api, pod_name, test_data, offset, device_path):
    tmp_file = '/var/test_data'
    pre_write_cmd = [
        '/bin/sh',
        '-c',
        'echo -ne ' + test_data + ' > ' + tmp_file
    ]
    write_cmd = [
        '/bin/sh',
        '-c',
        'dd if=' + tmp_file + ' of=' + device_path +
        ' bs=' + str(len(test_data)) + ' count=1 seek=' + str(offset)
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream write'):
        stream(api.connect_get_namespaced_pod_exec, pod_name, 'default',
               command=pre_write_cmd, stderr=True, stdin=False, stdout=True,
               tty=False)
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=write_cmd, stderr=True, stdin=False, stdout=True,
            tty=False)


def read_pod_block_volume_data(api, pod_name, data_size, offset, device_path):
    read_command = [
        '/bin/sh',
        '-c',
        'dd if=' + device_path +
        ' status=none bs=' + str(data_size) + ' count=1 skip=' + str(offset)
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=read_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def exec_command_in_pod(api, command, pod_name, namespace):
    """
    Execute command in the pod.
    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        command: The command to execute in the pod.
        namespace: The namespace where the pod exists.
    Returns:
        The output of the command.
    """
    exec_command = [
        '/bin/sh',
        '-c',
        command
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read/write'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, namespace,
            command=exec_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def get_pod_data_md5sum(api, pod_name, path):
    md5sum_command = [
        '/bin/sh', '-c', 'md5sum ' + path + " | awk '{print $1}'"
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT * 3,
                 error_message='Timeout on executing stream md5sum'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=md5sum_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def write_pod_volume_random_data(api, pod_name, path, size_in_mb):
    write_cmd = [
        '/bin/sh',
        '-c',
        'dd if=/dev/urandom of=' + path +
        ' bs=1M' + ' count=' + str(size_in_mb)
    ]
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_cmd, stderr=True, stdin=False, stdout=True,
        tty=False)


def copy_pod_volume_data(api, pod_name, src_path, dest_path):
    write_cmd = [
        '/bin/sh',
        '-c',
        'dd if=' + src_path + ' of=' + dest_path
    ]
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_cmd, stderr=True, stdin=False, stdout=True,
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


def wait_delete_pod(api, pod_uid, namespace='default'):
    for i in range(DEFAULT_POD_TIMEOUT):
        ret = api.list_namespaced_pod(namespace=namespace)
        found = False
        for item in ret.items:
            if item.metadata.uid == pod_uid:
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
    for replica in volume.replicas:
        found_hosts[replica.hostId] = {}
        assert not len(set(spec["disk"]) -
                       set(tag_mapping[replica.hostId]["disk"]))
        assert not len(set(spec["node"]) -
                       set(tag_mapping[replica.hostId]["node"]))

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
    return client.update(node, allowScheduling=node.allowScheduling,
                         tags=tags)


def set_node_scheduling(client, node, allowScheduling):
    if node.tags is None:
        node.tags = []
    return client.update(node, allowScheduling=allowScheduling,
                         tags=node.tags)


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
                pod_name = pod_manifest['metadata']['name']
                delete_and_wait_pod(api, pod_name)
            except Exception as e:
                print("\nException when waiting for pod deletion")
                print(e)
                return
            try:
                volume_details = pod_manifest['spec']['volumes'][0]
                pvc_name = volume_details['persistentVolumeClaim']['claimName']
                delete_and_wait_pvc(api, pvc_name)
            except Exception as e:
                print("\nException when waiting for PVC deletion")
                print(e)
            try:
                found = False
                pvs = api.list_persistent_volume()
                for item in pvs.items:
                    if item.spec.claim_ref.name == pvc_name:
                        pv = item
                        found = True
                        break
                if found:
                    pv_name = pv.metadata.name
                    delete_and_wait_pv(api, pv_name)
            except Exception as e:
                print("\nException when waiting for PV deletion")
                print(e)

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
def scheduling_api(request):
    """
    Create a new SchedulingV1API instance.
    Returns:
        A new CoreV1API Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    scheduling_api = k8sclient.SchedulingV1Api()

    return scheduling_api


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
def apps_api(request):
    """
    Create a new AppsV1API instance.
    Returns:
        A new AppsV1API Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    apps_api = k8sclient.AppsV1Api()

    return apps_api


@pytest.fixture
def batch_v1_beta_api(request):
    """
    Create a new BatchV1beta1Api instance.
    Returns:
        A new BatchV1beta1Api Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.BatchV1beta1Api()

    return api


def get_pv_manifest(request):
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
                'driver': 'driver.longhorn.io',
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
def csi_pv(request):
    return get_pv_manifest(request)


@pytest.fixture
def csi_pv_backingimage(request):
    pv_manifest = get_pv_manifest(request)
    pv_manifest['spec']['capacity']['storage'] = \
        size_to_string(BACKING_IMAGE_EXT4_SIZE)
    pv_manifest['spec']['csi']['volumeAttributes']['backingImage'] = \
        BACKING_IMAGE_NAME

    def finalizer():
        api = get_core_api_client()
        delete_and_wait_pv(api, pv_manifest['metadata']['name'])

        client = get_longhorn_api_client()
        delete_and_wait_longhorn(client, pv_manifest['metadata']['name'])

    request.addfinalizer(finalizer)

    return pv_manifest


def get_pvc_manifest(request):
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
def pvc(request):
    return get_pvc_manifest(request)


@pytest.fixture
def pvc_backingimage(request):
    pvc_manifest = get_pvc_manifest(request)
    pvc_manifest['spec']['resources']['requests']['storage'] = \
        size_to_string(BACKING_IMAGE_EXT4_SIZE)
    return pvc_manifest


@pytest.fixture
def statefulset(request):
    statefulset_manifest = {
        'apiVersion': 'apps/v1',
        'kind': 'StatefulSet',
        'metadata': {
            'name': 'test-statefulset',
            'namespace': 'default',
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
        'provisioner': 'driver.longhorn.io',
        'allowVolumeExpansion': True,
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


@pytest.fixture
def priority_class(request):
    priority_class = {
        'apiVersion': 'scheduling.k8s.io/v1',
        'kind': 'PriorityClass',
        'metadata': {
            'name': PRIORITY_CLASS_NAME + "-" + ''.join(
                random.choice(string.ascii_lowercase +
                              string.digits)
                for _ in range(6))
        },
        'value': random.randrange(PRIORITY_CLASS_MIN, PRIORITY_CLASS_MAX)
    }

    def finalizer():
        # ensure that the priority class gets unset for longhorn
        # before deleting the class
        client = get_longhorn_api_client()
        setting = client.by_id_setting(SETTING_PRIORITY_CLASS)
        setting = client.update(setting, value='')
        assert setting.value == ''

        api = get_scheduling_api_client()
        try:
            api.delete_priority_class(name=priority_class['metadata']['name'],
                                      body=k8sclient.V1DeleteOptions())
        except ApiException as e:
            assert e.status == 404

    request.addfinalizer(finalizer)

    return priority_class


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
        assert len(node.disks) == 1

        update_disks = get_update_disks(node.disks)
        update_disks[list(update_disks)[0]].tags = tags["disk"]
        new_node = node.diskUpdate(disks=update_disks)
        disks = get_update_disks(new_node.disks)
        assert disks[list(new_node.disks)[0]].tags == tags["disk"]

        new_node = set_node_tags(client, node, tags["node"])
        assert new_node.tags == tags["node"]

        tag_mappings[node.id] = tags
    yield tag_mappings

    client = get_longhorn_api_client()  # NOQA
    nodes = client.list_node()
    for node in nodes:
        update_disks = get_update_disks(node.disks)
        update_disks[list(update_disks)[0]].tags = []
        new_node = node.diskUpdate(disks=update_disks)
        disks = get_update_disks(new_node.disks)
        assert len(disks[list(new_node.disks)[0]].tags) == 0, \
            f" disk = {disks}"

        new_node = set_node_tags(client, node)
        assert len(new_node.tags) == 0, f" Node = {new_node}"


@pytest.fixture
def random_labels():
    labels = {}
    i = 0
    while i < 3:
        key = "label/" + "".join(random.choice(string.ascii_lowercase +
                                               string.digits)
                                 for _ in range(6))
        if not labels.get(key):
            labels["key"] = generate_random_data(VOLUME_RWTEST_SIZE)
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

    # check if longhorn manager port is open before calling get_client
    for ip in ips:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mgr_port_open = sock.connect_ex((ip, 9500))

        if mgr_port_open == 0:
            client = get_client(ip + PORT)
            break

    hosts = client.list_node()
    assert len(hosts) == len(ips)

    request.addfinalizer(lambda: cleanup_client())

    cleanup_client()

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
        cleanup_client()

    request.addfinalizer(finalizer)

    cleanup_client()

    return clis


def cleanup_client():
    client = get_longhorn_api_client()
    # cleanup test disks
    cleanup_test_disks(client)

    if recurring_job_feature_supported(client):
        cleanup_all_recurring_jobs(client)

    cleanup_all_volumes(client)

    if backing_image_feature_supported(client):
        cleanup_all_backing_images(client)

    cleanup_storage_class()

    # enable nodes scheduling
    reset_node(client)
    reset_settings(client)
    reset_disks_for_all_nodes(client)
    reset_engine_image(client)
    wait_for_all_instance_manager_running(client)

    # check replica subdirectory of default disk path
    if not os.path.exists(DEFAULT_REPLICA_DIRECTORY):
        subprocess.check_call(
            ["mkdir", "-p", DEFAULT_REPLICA_DIRECTORY])


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


def get_backupstore_poll_interval():
    poll_interval = os.environ['LONGHORN_BACKUPSTORE_POLL_INTERVAL']
    assert len(poll_interval) != 0
    return poll_interval


def get_backupstores():
    # The try is added to avoid the pdoc3 error while publishing this on
    # https://longhorn.github.io/longhorn-tests
    try:
        backupstore = os.environ['LONGHORN_BACKUPSTORES']
    except KeyError:
        return []

    try:
        backupstore = backupstore.replace(" ", "")
        backupstores = backupstore.split(",")
        for i in range(len(backupstores)):
            backupstores[i] = backupstores[i].split(":")[0]
    except ValueError:
        backupstores = backupstore.split(":")[0]
    return backupstores


def get_clients(hosts):
    clients = {}
    for host in hosts:
        assert host.name is not None
        assert host.address is not None
        clients[host.name] = get_client(host.address + PORT)
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
        if v.conditions.scheduled.status == "False" and \
                v.conditions.scheduled.reason == \
                "ReplicaSchedulingFailure":
            scheduling_failure = True
        if scheduling_failure:
            break
        time.sleep(RETRY_INTERVAL)
    assert scheduling_failure, f" Scheduled Status = " \
        f"{v.conditions.scheduled.status}, Scheduled reason = " \
        f"{v.conditions.scheduled.reason}, volume = {v}"


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


def wait_for_replica_directory():
    found = False
    for i in range(RETRY_COUNTS):
        if os.path.exists(DEFAULT_REPLICA_DIRECTORY):
            found = True
            break
        time.sleep(RETRY_INTERVAL)
    assert found


def wait_for_volume_creation(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        found = False
        for volume in volumes:
            if volume.name == name:
                found = True
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found


def wait_for_volume_endpoint(client, name):
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(name)
        engine = get_volume_engine(v)
        if engine.endpoint != "":
            break
        time.sleep(RETRY_INTERVAL)
    check_volume_endpoint(v)
    return v


def wait_for_volume_attached(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_STATE,
                                  VOLUME_STATE_ATTACHED)


def wait_for_volume_detached(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_STATE,
                                  VOLUME_STATE_DETACHED)


def wait_for_volume_detached_unknown(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_ROBUSTNESS,
                           VOLUME_ROBUSTNESS_UNKNOWN)
    return wait_for_volume_detached(client, name)


def wait_for_volume_healthy(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED)
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_ROBUSTNESS,
                           VOLUME_ROBUSTNESS_HEALTHY)
    return wait_for_volume_endpoint(client, name)


def wait_for_volume_healthy_no_frontend(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_HEALTHY)


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
    assert volume[key] == value, f" value={value}\n. \
            volume[key]={volume[key]}\n. volume={volume}"
    return volume


def wait_for_volume_delete(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        found = False
        for volume in volumes:
            if volume.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_for_backup_volume_delete(client, name):
    for _ in range(RETRY_BACKUP_COUNTS):
        bvs = client.list_backupVolume()
        found = False
        for bv in bvs:
            if bv.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert not found


def wait_for_volume_current_image(client, name, image):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume.currentImage == image:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume.currentImage == image
    return volume


def wait_for_volume_replica_count(client, name, count):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if len(volume.replicas) == count:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(volume.replicas) == count
    return volume


def wait_for_volume_replica_auto_balance_update(client, volume_name, value):
    wait_for_volume_creation(client, volume_name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        if volume.replicaAutoBalance == value:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume.replicaAutoBalance == value
    return volume


def wait_for_volume_replicas_mode(client, volname, mode,
                                  replica_names=None, replica_count=None):
    verified = False
    for _ in range(RETRY_COUNTS):
        replicas = []
        volume = client.by_id_volume(volname)
        if replica_names is None:
            replicas = volume.replicas
        else:
            for r_name in replica_names:
                found = False
                for r in volume.replicas:
                    if r.name == r_name:
                        replicas.append(r)
                        found = True
                assert found

        count = 0
        wo_count = 0
        for r in replicas:
            if r.mode == mode:
                count += 1
            if r.mode == 'WO':
                wo_count += 1
        assert wo_count <= VOLUME_REPLICA_WO_LIMIT

        r_count = len(replicas) if replica_count is None else replica_count
        if count == r_count:
            verified = True
            break
        time.sleep(RETRY_INTERVAL)

    assert verified
    return volume


def wait_for_volume_replicas_running_on_hosts(client, volume_name, host_ids,
                                              replica_balanced):
    hosts = list(host_ids)
    for i in range(RETRY_COUNTS):
        hosts = list(host_ids)
        num_running = 0
        volume = client.by_id_volume(volume_name)
        for replica in volume.replicas:
            if not replica.running:
                continue

            if replica.hostId not in hosts:
                continue

            if replica_balanced:
                hosts.remove(replica.hostId)

            num_running += 1
        if num_running == volume.numberOfReplicas:
            break

        time.sleep(RETRY_INTERVAL)
    assert num_running == volume.numberOfReplicas
    return volume


def wait_for_volume_frontend_disabled(client, volume_name, state=True):
    for _ in range(RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        try:
            assert vol.disableFrontend is state
            break
        except AssertionError:
            time.sleep(RETRY_INTERVAL)


def wait_for_snapshot_purge(client, volume_name, *snaps):
    completed = 0
    last_purge_progress = {}
    purge_status = {}
    for i in range(RETRY_COUNTS):
        completed = 0
        v = client.by_id_volume(volume_name)
        purge_status = v.purgeStatus
        for status in purge_status:
            assert status.error == ""

            progress = status.progress
            assert progress <= 100
            replica = status.replica
            last = last_purge_progress.get(replica)
            assert last is None or last <= status.progress
            last_purge_progress["replica"] = progress

            if status.state == "complete":
                assert progress == 100
                completed += 1
        if completed == len(purge_status):
            break
        time.sleep(RETRY_INTERVAL)
    assert completed == len(purge_status)

    # Now that the purge has been reported to be completed, the Snapshots
    # should should be removed or "marked as removed" in the case of
    # the latest snapshot.
    found = False
    snapshots = v.snapshotList(volume=volume_name)

    for snap in snaps:
        for vs in snapshots.data:
            if snap == vs["name"]:
                if vs["removed"] is False:
                    found = True
                    break

                if "volume-head" not in vs["children"]:
                    found = True
                    break
    assert not found
    return v


def wait_for_engine_image_creation(client, image_name):
    for i in range(RETRY_COUNTS):
        images = client.list_engine_image()
        found = False
        for img in images:
            if img.name == image_name:
                found = True
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found


def wait_for_engine_image_state(client, image_name, state):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image.state == state:
            break
        time.sleep(RETRY_INTERVAL)
    assert image.state == state
    return image


def wait_for_engine_image_condition(client, image_name, state):
    """
    state: "True", "False"
    """
    for i in range(RETRY_COUNTS):
        wait_for_engine_image_creation(client, image_name)
        image = client.by_id_engine_image(image_name)
        if image['conditions'][0]['status'] == state:
            break
        time.sleep(RETRY_INTERVAL_LONG)
    assert image['conditions'][0]['status'] == state
    return image


def wait_for_engine_image_ref_count(client, image_name, count):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image.refCount == count:
            break
        time.sleep(RETRY_INTERVAL)
    assert image.refCount == count
    if count == 0:
        assert image.noRefSince != ""
    return image


def json_string_go_to_python(str):
    return str.replace("u\'", "\"").replace("\'", "\""). \
        replace("True", "true").replace("False", "false")


def delete_replica_processes(client, api, volname):
    replica_map = {}
    volume = client.by_id_volume(volname)
    for r in volume.replicas:
        replica_map[r.instanceManagerName] = r.name

    for rm_name, r_name in replica_map.items():
        delete_command = 'longhorn-instance-manager process delete ' + \
                         '--name ' + r_name
        exec_instance_manager(api, rm_name, delete_command)


def crash_replica_processes(client, api, volname, replicas=None,
                            wait_to_fail=True):

    if replicas is None:
        volume = client.by_id_volume(volname)
        replicas = volume.replicas

    for r in replicas:
        assert r.instanceManagerName != ""
        kill_command = "kill `ps aux | grep '" + r['dataPath'] +\
                       "' | grep -v grep | awk '{print $2}'`"
        exec_instance_manager(api, r.instanceManagerName, kill_command)

    if wait_to_fail is True:
        for r in replicas:
            wait_for_replica_failed(client, volname, r['name'])


def exec_instance_manager(api, im_name, cmd):
    exec_cmd = ['/bin/sh', '-c', cmd]

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        stream(api.connect_get_namespaced_pod_exec,
               im_name,
               LONGHORN_NAMESPACE, command=exec_cmd,
               stderr=True, stdin=False, stdout=True, tty=False)


def wait_for_replica_failed(client, volname, replica_name):
    failed = True
    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)
        failed = True
        volume = client.by_id_volume(volname)
        for r in volume.replicas:
            if r['name'] != replica_name:
                continue
            if r['running'] or r['failedAt'] == "":
                failed = False
                break
            if r['instanceManagerName'] != "":
                im = client.by_id_instance_manager(
                    r['instanceManagerName'])
                if r['name'] in im['instances']:
                    failed = False
                    break
        if failed:
            break
    assert failed


def wait_for_replica_running(client, volname, replica_name):
    is_running = False
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volname)
        for r in volume.replicas:
            if r['name'] != replica_name:
                continue
            if r['running'] and r['instanceManagerName'] != "":
                im = client.by_id_instance_manager(
                    r['instanceManagerName'])
                if r['name'] in im['instances']:
                    is_running = True
                    break
        if is_running:
            break
        time.sleep(RETRY_INTERVAL)
    assert is_running


def wait_for_replica_scheduled(client, volume_name, to_nodes,
                               expect_success=2, expect_fail=0,
                               anti_affinity=False,
                               chk_vol_healthy=True,
                               chk_replica_running=True):
    for _ in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        if chk_vol_healthy:
            assert volume.robustness == VOLUME_ROBUSTNESS_HEALTHY

        scheduled = 0
        unexpect_fail = expect_fail
        expect_nodes = [n for n in to_nodes]
        for r in volume.replicas:
            try:
                assert r.hostId in expect_nodes

                if chk_replica_running:
                    assert r.running is True
                    assert r.mode == "RW"

                if not anti_affinity:
                    expect_nodes.remove(r.hostId)

                scheduled += 1
            except AssertionError:
                unexpect_fail -= 1

        if scheduled == expect_success and unexpect_fail == 0:
            break

        time.sleep(RETRY_INTERVAL)

    assert scheduled == expect_success, f" Volume = {volume}"
    assert unexpect_fail == 0, f" Volume = {volume}"
    assert len(volume.replicas) == expect_success + expect_fail, \
        f" Volume = {volume}"
    return volume


def get_host_replica_count(client, volume_name, host_id, chk_running=False):
    volume = client.by_id_volume(volume_name)

    replica_count = 0
    for replica in volume.replicas:
        if chk_running and not replica.running:
            continue
        if replica.hostId == host_id:
            replica_count += 1
    return replica_count


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


@pytest.fixture
def sts_name(request):
    return generate_sts_name()


def generate_sts_name():
    return STATEFULSET_NAME + "-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def generate_random_suffix():
    return "-" + ''.join(random.choice(string.ascii_lowercase + string.digits)
                         for _ in range(6))


def get_default_engine_image(client):
    images = client.list_engine_image()
    for img in images:
        if img.default:
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
    return write_device_random_data(dev, position=position)


def check_device_data(dev, data, check_checksum=True):
    r_data = dev_read(dev, data['pos'], data['len'])
    assert r_data == bytes(data['content'], encoding='utf8')
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
    data = bytes(data, encoding='utf-8')
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


def prepare_host_disk(dev, vol_name, mkfs_ext4_options=""):
    if mkfs_ext4_options == "":
        cmd = ['mkfs.ext4', dev]
    else:
        cmd = ['mkfs.ext4', mkfs_ext4_options, dev]
    subprocess.check_call(cmd)

    mount_path = os.path.join(DIRECTORY_PATH, vol_name)
    mount_disk(dev, mount_path)
    return mount_path


def mount_disk(dev, mount_path):
    # create directory before mount
    cmd = ['mkdir', '-p', mount_path]
    subprocess.check_call(cmd)
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
        conditions = volume.conditions
        if conditions is not None and \
                conditions != {} and \
                conditions[VOLUME_CONDITION_SCHEDULED] and \
                conditions[VOLUME_CONDITION_SCHEDULED][key] and \
                conditions[VOLUME_CONDITION_SCHEDULED][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    conditions = volume.conditions
    assert conditions[VOLUME_CONDITION_SCHEDULED][key] == value, \
        f" Expected value = {value}, " \
        f" Conditions[{VOLUME_CONDITION_SCHEDULED}][{key}] = " \
        f"{conditions[VOLUME_CONDITION_SCHEDULED][key]}, Volume = {volume}"
    return volume


def wait_for_volume_condition_restore(client, name, key, value):
    wait_for_volume_creation(client, name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        conditions = volume.conditions
        if conditions is not None and \
                conditions != {} and \
                VOLUME_CONDITION_RESTORE in conditions and \
                conditions[VOLUME_CONDITION_RESTORE][key] and \
                conditions[VOLUME_CONDITION_RESTORE][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    conditions = volume.conditions
    assert conditions[VOLUME_CONDITION_RESTORE][key] == value
    return volume


def wait_for_volume_condition_toomanysnapshots(client, name, key, value):
    wait_for_volume_creation(client, name)
    for _ in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        conditions = volume.conditions
        if conditions is not None and \
                conditions != {} and \
                VOLUME_CONDITION_TOOMANYSNAPSHOTS in conditions and \
                conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] and \
                conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    conditions = volume.conditions
    assert conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] == value
    return volume


def get_host_disk_size(disk):
    cmd = ['stat', '-fc',
           '{"path":"%n","fsid":"%i","type":"%T","freeBlock":%f,'
           '"totalBlock":%b,"blockSize":%S}',
           disk]
    # As the disk available storage is rounded off to 100Mb
    truncate_to = 100 * 1024 * 1024
    output = subprocess.check_output(cmd)
    disk_info = json.loads(output)
    block_size = disk_info["blockSize"]
    free_blk = disk_info["freeBlock"]
    total_blk = disk_info["totalBlock"]
    free = int((free_blk * block_size) / truncate_to) * truncate_to
    total = (total_blk * block_size)
    return free, total


def wait_for_disk_status(client, node_name, disk_name, key, value):
    # use wait_for_disk_storage_available to check storageAvailable
    assert key != "storageAvailable"
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(node_name)
        disks = node.disks
        if len(disks) > 0 and \
                disk_name in disks and \
                disks[disk_name][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(disks) != 0
    assert disk_name in disks
    assert disks[disk_name][key] == value
    return node


def wait_for_disk_storage_available(client, node_name, disk_name, disk_path):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(node_name)
        disks = node.disks
        if len(disks) > 0 and disk_name in disks:
            free, _ = get_host_disk_size(disk_path)
            if disks[disk_name]["storageAvailable"] == free:
                break
        time.sleep(RETRY_INTERVAL)
    assert len(disks) != 0
    assert disk_name in disks
    assert disks[disk_name]["storageAvailable"] == free
    return node


def wait_for_disk_uuid(client, node_name, uuid):
    found = False
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(node_name)
        disks = node.disks
        for name in disks:
            if disks[name]["diskUUID"] == uuid:
                found = True
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)
    assert found
    return node


def wait_for_disk_conditions(client, node_name, disk_name, key, value):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(node_name)
        disks = node.disks
        disk = disks[disk_name]
        conditions = disk.conditions
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
        if len(node.disks) == disk_num:
            allUpdated = True
            disks = node.disks
            for d in disks:
                if disks[d]["diskUUID"] == "":
                    allUpdated = False
                    break
            if allUpdated:
                break
        time.sleep(RETRY_INTERVAL)
    assert len(node.disks) == disk_num
    return node


def wait_for_node_tag_update(client, name, tags):
    updated = False
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        if not tags and not node.tags:
            updated = True
            break
        elif node.tags is not None and set(node.tags) == set(tags):
            updated = True
            break
        time.sleep(RETRY_INTERVAL)
    assert updated
    return node


def cleanup_node_disks(client, node_name):
    node = client.by_id_node(node_name)
    disks = node.disks
    for _, disk in iter(disks.items()):
        disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    node = client.by_id_node(node_name)
    node.diskUpdate(disks=update_disks)
    node.diskUpdate(disks={})
    return wait_for_disk_update(client, node_name, 0)


def get_volume_engine(v):
    engines = v.controllers
    assert len(engines) != 0
    return engines[0]


def get_volume_endpoint(v):
    endpoint = check_volume_endpoint(v)
    return endpoint


def check_volume_endpoint(v):
    engine = get_volume_engine(v)
    endpoint = engine.endpoint
    if v.disableFrontend:
        assert endpoint == ""
    else:
        if v.frontend == VOLUME_FRONTEND_BLOCKDEV:
            assert endpoint == os.path.join(DEV_PATH, v.name)
        elif v.frontend == VOLUME_FRONTEND_ISCSI:
            assert endpoint.startswith("iscsi://")
        else:
            raise Exception("Unexpected volume frontend:", v.frontend)
    return endpoint


def wait_for_backup_completion(client, volume_name, snapshot_name=None,
                               retry_count=RETRY_BACKUP_COUNTS):
    completed = False
    for _ in range(retry_count):
        v = client.by_id_volume(volume_name)
        for b in v.backupStatus:
            if snapshot_name is not None and b.snapshot != snapshot_name:
                continue
            if b.state == "Completed":
                assert b.progress == 100
                assert b.error == ""
                completed = True
                break
        if completed:
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert completed is True, f" Backup status = {b.state}," \
                              f" Backup Progress = {b.progress}, Volume = {v}"
    return v


def wait_pod_attach_after_first_backup_completion(
        client, core_api, volume_name, label_name):
    completed = False
    for _ in range(RETRY_BACKUP_COUNTS):
        vol = client.by_id_volume(volume_name)
        for b in vol.backupStatus:
            if b.state == 'Completed':
                assert b.progress == 100
                assert b.error == ''
                completed = True
                break
        if completed:
            wait_for_volume_frontend_disabled(client, vol.name, False)
            wait_for_volume_attached(client, vol.name)
            break

        label_selector = "name=" + label_name
        pods = core_api.list_namespaced_pod(namespace="default",
                                            label_selector=label_selector)
        for pod in pods.items:
            assert pod.status.phase != 'Running'
        assert vol.disableFrontend is True

        time.sleep(RETRY_BACKUP_INTERVAL)
    assert completed is True
    return vol


def wait_for_backup_to_start(client, volume_name, snapshot_name=None,
                             retry_count=RETRY_BACKUP_COUNTS,
                             chk_progress=0):
    in_progress = False
    for _ in range(retry_count):
        v = client.by_id_volume(volume_name)
        for b in v.backupStatus:
            if snapshot_name is not None and b.snapshot != snapshot_name:
                continue
            if b.state == "InProgress" and b.progress > chk_progress:
                assert b.error == ""
                in_progress = True
                break
        if in_progress:
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert in_progress is True
    return v


def wait_for_backup_state(client, volume_name, predicate,
                          retry_count=RETRY_BACKUP_COUNTS):
    completed = False
    for i in range(retry_count):
        v = client.by_id_volume(volume_name)
        for b in v.backupStatus:
            if predicate(b):
                completed = True
                break
        if completed:
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert completed is True
    return v


def monitor_restore_progress(client, volume_name):
    completed = 0
    rs = {}
    for i in range(RETRY_COUNTS):
        completed = 0
        v = client.by_id_volume(volume_name)
        rs = v.restoreStatus
        for r in rs:
            assert r.error == ""
            if r.state == "complete":
                assert r.progress == 100
                completed += 1
        if completed == len(rs):
            break
        time.sleep(RETRY_INTERVAL)
    assert completed == len(rs)
    return v


def wait_for_volume_migration_ready(client, volume_name):
    ready = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        engines = v.controllers
        ready = len(engines) == 2
        for e in engines:
            ready = ready and e.endpoint != ""
        if ready:
            break
        time.sleep(RETRY_INTERVAL)
    assert ready
    return v


def wait_for_volume_migration_node(client, volume_name, node_id):
    ready = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        engines = v.controllers
        replicas = v.replicas
        if len(engines) == 1 and len(replicas) == v.numberOfReplicas:
            e = engines[0]
            if e.endpoint != "":
                assert e.hostId == node_id
                ready = True
                break
        time.sleep(RETRY_INTERVAL)
    assert ready
    return v


def get_random_client(clients):
    for _, client in iter(clients.items()):
        break
    return client


def get_update_disks(disks):
    update_disk = {}
    for key, disk in iter(disks.items()):
        update_disk[key] = disk
    return update_disk


def reset_node(client):
    nodes = client.list_node()
    for node in nodes:
        try:
            node = client.update(node, tags=[])
            node = wait_for_node_tag_update(client, node.id, [])
            node = client.update(node, allowScheduling=True)
            wait_for_node_update(client, node.id,
                                 "allowScheduling", True)
        except Exception as e:
            print("\nException when reset node schedulding and tags", node)
            print(e)

    reset_longhorn_node_zone(client)


def reset_longhorn_node_zone(client):
    core_api = get_core_api_client()

    nodes = client.list_node()
    for n in nodes:
        set_k8s_node_zone_label(core_api, n.name, None)
    wait_longhorn_node_zone_reset(client)


def wait_longhorn_node_zone_reset(client):

    lh_nodes = client.list_node()
    node_names = map(lambda node: node.name, lh_nodes)

    for node_name in node_names:
        for j in range(RETRY_COUNTS):
            lh_node = client.by_id_node(node_name)
            if lh_node.zone == '':
                break
            time.sleep(RETRY_INTERVAL)

        assert lh_node.zone == ''


def set_k8s_node_zone_label(core_api, node_name, zone_name):
    k8s_zone_label = get_k8s_zone_label()

    payload = {
        "metadata": {
            "labels": {
                k8s_zone_label: zone_name}
        }
    }

    core_api.patch_node(node_name, body=payload)


def get_k8s_zone_label():
    ver_api = get_version_api_client()
    k8s_ver_data = ver_api.get_code()

    k8s_ver_major = k8s_ver_data.major
    assert k8s_ver_major == '1'

    k8s_ver_minor = k8s_ver_data.minor

    if int(k8s_ver_minor) >= 17:
        k8s_zone_label = K8S_ZONE_LABEL
    else:
        k8s_zone_label = DEPRECATED_K8S_ZONE_LABEL

    return k8s_zone_label


def cleanup_test_disks(client):
    del_dirs = os.listdir(DIRECTORY_PATH)
    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    disks = node.disks
    for name, disk in iter(disks.items()):
        for del_dir in del_dirs:
            dir_path = os.path.join(DIRECTORY_PATH, del_dir)
            if dir_path == disk.path:
                disk.allowScheduling = False
    update_disks = get_update_disks(disks)
    try:
        node = node.diskUpdate(disks=update_disks)
        disks = node.disks
        for name, disk in iter(disks.items()):
            for del_dir in del_dirs:
                dir_path = os.path.join(DIRECTORY_PATH, del_dir)
                if dir_path == disk.path:
                    wait_for_disk_status(client, host_id, name,
                                         "allowScheduling", False)
    except Exception as e:
        print("\nException when update node disks", node)
        print(e)
        pass

    # delete test disks
    disks = node.disks
    update_disks = {}
    for name, disk in iter(disks.items()):
        if disk.allowScheduling:
            update_disks[name] = disk
    try:
        node.diskUpdate(disks=update_disks)
        wait_for_disk_update(client, host_id, len(update_disks))
    except Exception as e:
        print("\nException when delete node test disks", node)
        print(e)
        pass
    # cleanup host disks
    for del_dir in del_dirs:
        try:
            cleanup_host_disk(del_dir)
        except Exception as e:
            print("\nException when cleanup host disk", del_dir)
            print(e)
            pass


def reset_disks_for_all_nodes(client):  # NOQA
    nodes = client.list_node()
    for node in nodes:
        # Reset default disk if there are more than 1 disk
        # on the node.
        cleanup_required = False
        if len(node.disks) > 1:
            cleanup_required = True
        if len(node.disks) == 1:
            for _, disk in iter(node.disks.items()):
                if disk.path != DEFAULT_DISK_PATH:
                    cleanup_required = True
        if cleanup_required:
            update_disks = get_update_disks(node.disks)
            for disk_name, disk in iter(update_disks.items()):
                disk.allowScheduling = False
                update_disks[disk_name] = disk
                node = node.diskUpdate(disks=update_disks)
            update_disks = {}
            node = node.diskUpdate(disks=update_disks)
            node = wait_for_disk_update(client, node.name, 0)
        if len(node.disks) == 0:
            default_disk = {"default-disk":
                            {"path": DEFAULT_DISK_PATH,
                             "allowScheduling": True}}
            node = node.diskUpdate(disks=default_disk)
            node = wait_for_disk_update(client, node.name, 1)
            assert len(node.disks) == 1
        # wait for node controller to update disk status
        disks = node.disks
        update_disks = {}
        for name, disk in iter(disks.items()):
            update_disk = disk
            update_disk.allowScheduling = True
            update_disk.storageReserved = \
                int(update_disk.storageMaximum * 30 / 100)
            update_disk.tags = []
            update_disks[name] = update_disk
        node = node.diskUpdate(disks=update_disks)
        for name, disk in iter(node.disks.items()):
            # wait for node controller update disk status
            wait_for_disk_status(client, node.name, name,
                                 "allowScheduling", True)
            wait_for_disk_status(client, node.name, name,
                                 "storageScheduled", 0)
            wait_for_disk_status(client, node.name, name,
                                 "storageReserved",
                                 int(update_disk.storageMaximum * 30 / 100))


def reset_settings(client):

    for setting in client.list_setting():
        setting_name = setting.name
        setting_default_value = setting.definition.default
        setting_readonly = setting.definition.readOnly

        s = client.by_id_setting(setting_name)
        if s.value != setting_default_value and not setting_readonly:
            try:
                client.update(s, value=setting_default_value)
            except Exception as e:
                print("\nException when resetting ",
                      setting_name,
                      " to value: ",
                      setting_default_value)
                print(s)
                print(e)


def reset_engine_image(client):
    core_api = get_core_api_client()
    ready = False

    for i in range(RETRY_COUNTS):
        ready = True
        ei_list = client.list_engine_image().data
        for ei in ei_list:
            if ei.default:
                if ei.state != get_engine_image_status_value(client, ei.name):
                    ready = False
            else:
                wait_for_engine_image_ref_count(client, ei.name, 0)
                client.delete(ei)
                wait_for_engine_image_deletion(client, core_api, ei.name)
        if ready:
            break
        time.sleep(RETRY_INTERVAL)

    assert ready


def wait_for_all_instance_manager_running(client):
    core_api = get_core_api_client()

    nodes = client.list_node()

    for i in range(RETRY_COUNTS):
        instance_managers = client.list_instance_manager()
        node_to_engine_manager_map, node_to_replica_manager_map = {}, {}
        try:
            for im in instance_managers:
                if im.managerType == "engine" and im.currentState == "running":
                    node_to_engine_manager_map[im.nodeID] = im
                elif im.managerType == "replica" and \
                        im.currentState == "running":
                    node_to_replica_manager_map[im.nodeID] = im
                else:
                    print("\nFound unknown instance manager:", im)
            if len(node_to_engine_manager_map) != len(nodes) or \
                    len(node_to_replica_manager_map) != len(nodes):
                time.sleep(RETRY_INTERVAL)
                continue

            for _, im in node_to_engine_manager_map.items():
                wait_for_instance_manager_desire_state(client, core_api,
                                                       im.name, "Running",
                                                       True)
            for _, im in node_to_replica_manager_map.items():
                wait_for_instance_manager_desire_state(client, core_api,
                                                       im.name, "Running",
                                                       True)
            break
        except Exception:
            continue


def wait_for_node_mountpropagation_condition(client, name):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        conditions = {}
        if "conditions" in node.keys():
            conditions = node.conditions

        if NODE_CONDITION_MOUNTPROPAGATION in \
                conditions.keys() and \
                "status" in \
                conditions[NODE_CONDITION_MOUNTPROPAGATION].keys() \
                and conditions[NODE_CONDITION_MOUNTPROPAGATION]["status"] != \
                CONDITION_STATUS_UNKNOWN:
            break
        time.sleep(RETRY_INTERVAL)
    return node


def wait_for_node_schedulable_condition(client, name):
    for i in range(RETRY_COUNTS):
        node = client.by_id_node(name)
        conditions = {}
        if "conditions" in node.keys():
            conditions = node.conditions

        if NODE_CONDITION_SCHEDULABLE in \
                conditions.keys() and \
                "status" in \
                conditions[NODE_CONDITION_SCHEDULABLE].keys() \
                and conditions[NODE_CONDITION_SCHEDULABLE]["status"] != \
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


def wait_for_backup_volume(client, vol_name, backing_image=""):
    for _ in range(RETRY_BACKUP_COUNTS):
        bv = client.by_id_backupVolume(vol_name)
        if bv is not None:
            if backing_image == "":
                break
            if bv.backingImageName == backing_image \
                    and bv.backingImageChecksum != "":
                break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert bv is not None, "failed to find backup volume " + vol_name


def wait_for_backup_target_available(client, available):
    def find_backup_target_default(client):
        bt = client.list_backup_target()
        assert bt is not None
        return bt.data[0]

    for _ in range(RETRY_COUNTS):
        bt = find_backup_target_default(client)
        if bt.available == available:
            break
        time.sleep(RETRY_INTERVAL)
    if bt.available != available:
        raise Exception(
            'BackupTarget status.available should be {}', available)


def find_backup(client, vol_name, snap_name):
    """
    find_backup will look for a backup on the backupstore
    it's important to note, that this can only be used for completed backups
    since the backup.cfg will only be written once a backup operation has
    been completed successfully
    """

    def find_backup_volume():
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv.name == vol_name:
                return bv
        return None

    bv = None
    for i in range(120):
        if bv is None:
            bv = find_backup_volume()
        if bv is not None:
            backups = bv.backupList().data
            for b in backups:
                if b.snapshotName == snap_name:
                    return bv, b
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert False, "failed to find backup for snapshot " + snap_name + \
                  " for volume " + vol_name


def find_replica_for_backup(client, volume_name, backup_id):
    replica_name = None
    for _ in range(RETRY_EXEC_COUNTS):
        volume = client.by_id_volume(volume_name)
        for status in volume.backupStatus:
            if status.id == backup_id:
                replica_name = status.replica
        if replica_name:
            return replica_name
        else:
            time.sleep(RETRY_BACKUP_INTERVAL)
    assert replica_name


def check_longhorn(core_api):
    ready = False
    has_engine_image = False
    has_driver_deployer = False
    has_manager = False
    has_ui = False
    has_instance_manager = False

    pod_running = True

    try:
        longhorn_pod_list = core_api.list_namespaced_pod('longhorn-system')
        for item in longhorn_pod_list.items:
            labels = item.metadata.labels

            if not labels:
                pass
            elif labels.get('longhorn.io/component', '') == 'engine-image' \
                    and item.status.phase == "Running":
                has_engine_image = True
            elif labels.get('app', '') == 'longhorn-driver-deployer' \
                    and item.status.phase == "Running":
                has_driver_deployer = True
            elif labels.get('app', '') == 'longhorn-manager' \
                    and item.status.phase == "Running":
                has_manager = True
            elif labels.get('app', '') == 'longhorn-ui' \
                    and item.status.phase == "Running":
                has_ui = True
            elif labels.get('longhorn.io/component', '') == \
                    'instance-manager' \
                    and item.status.phase == "Running":
                has_instance_manager = True

        if has_engine_image and has_driver_deployer and has_manager and \
                has_ui and has_instance_manager and pod_running:
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

    pod_running = True

    try:
        longhorn_pod_list = core_api.list_namespaced_pod('longhorn-system')
        for item in longhorn_pod_list.items:
            if item.status.phase != "Running":
                pod_running = False

            labels = item.metadata.labels
            if not labels:
                pass
            elif labels.get('app', '') == 'csi-attacher':
                has_attacher = True
            elif labels.get('app', '') == 'csi-provisioner':
                has_provisioner = True
            elif labels.get('app', '') == 'longhorn-csi-plugin':
                has_csi_plugin = True

        if has_attacher and has_provisioner and has_csi_plugin and pod_running:
            using_csi = CSI_TRUE
        elif not has_attacher and not has_provisioner \
                and not has_csi_plugin and not pod_running:
            using_csi = CSI_FALSE

    except ApiException as e:
        if (e.status == 404):
            using_csi = CSI_FALSE

    assert using_csi != CSI_UNKNOWN

    return True if using_csi == CSI_TRUE else False


def check_csi_expansion(core_api):
    csi_expansion_enabled = False
    has_csi_resizer = False
    pod_running = True

    try:
        longhorn_pod_list = core_api.list_namespaced_pod('longhorn-system')
        for item in longhorn_pod_list.items:
            if item.status.phase != "Running":
                pod_running = False

            labels = item.metadata.labels
            if not labels:
                pass
            elif labels.get('app', '') == 'csi-resizer':
                has_csi_resizer = True
        if has_csi_resizer and pod_running:
            csi_expansion_enabled = True

    except ApiException:
        pass

    return csi_expansion_enabled


def create_statefulset(statefulset_manifest):
    """
    Create a new StatefulSet for testing.
    """
    api = get_apps_api_client()
    api.create_namespaced_stateful_set(
        body=statefulset_manifest,
        namespace='default')


def create_and_wait_statefulset(statefulset_manifest):
    """
    Create a new StatefulSet for testing.

    This function will block until all replicas in the StatefulSet are online
    or it times out, whichever occurs first.
    """
    create_statefulset(statefulset_manifest)
    wait_statefulset(statefulset_manifest)


def wait_statefulset(statefulset_manifest):
    api = get_apps_api_client()
    replicas = statefulset_manifest['spec']['replicas']
    for i in range(DEFAULT_STATEFULSET_TIMEOUT):
        s_set = api.read_namespaced_stateful_set(
            name=statefulset_manifest['metadata']['name'],
            namespace='default')
        # s_set is none if statefulset is not yet created
        if s_set is not None and s_set.status.ready_replicas == replicas:
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


def cleanup_storage_class():
    skip_sc_deletes = ["longhorn", "local-path"]
    api = get_storage_api_client()
    ret = api.list_storage_class()
    for sc in ret.items:
        if sc.metadata.name in skip_sc_deletes:
            continue
        delete_storage_class(sc.metadata.name)

    ok = False
    for _ in range(RETRY_COUNTS):
        ok = True
        ret = api.list_storage_class()
        for sc in ret.items:
            if sc.metadata.name not in skip_sc_deletes:
                ok = False
                break
        if ok:
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def create_pvc(pvc_manifest):
    api = get_core_api_client()
    api.create_namespaced_persistent_volume_claim(
        'default', pvc_manifest)


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
        if volume.name == volume_name:
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


def delete_and_wait_pvc(api, pvc_name, retry_counts=RETRY_COUNTS):
    try:
        api.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace='default',
            body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404

    wait_delete_pvc(api, pvc_name, retry_counts=retry_counts)


def wait_delete_pvc(api, pvc_name, retry_counts=RETRY_COUNTS):
    for _ in range(retry_counts):
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
        ks = volume.kubernetesStatus
        ks = json.loads(json.dumps(ks, default=lambda o: o.__dict__))

        for k, v in expect_ks.items():
            if k in ('lastPVCRefAt', 'lastPodRefAt'):
                if (v != '' and ks[k] == '') or \
                   (v == '' and ks[k] != ''):
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


def create_pv_for_volume(client, core_api, volume, pv_name, fs_type="ext4"):
    volume.pvCreate(pvName=pv_name, fsType=fs_type)
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
    wait_volume_kubernetes_status(client, volume.name, ks)


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
    wait_volume_kubernetes_status(client, volume.name, ks)


def activate_standby_volume(client, volume_name,
                            frontend=VOLUME_FRONTEND_BLOCKDEV):
    volume = client.by_id_volume(volume_name)
    assert volume.standby is True
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        engines = volume.controllers
        if len(engines) != 1 or \
                (volume.lastBackup != "" and
                 engines[0].lastRestoredBackup != volume.lastBackup):
            time.sleep(RETRY_INTERVAL)
            continue
        activated = False
        try:
            volume.activate(frontend=frontend)
            activated = True
            break
        except Exception as e:
            assert "hasn't finished incremental restored" \
                   in str(e.error.message)
            time.sleep(RETRY_INTERVAL)
        if activated:
            break
    volume = client.by_id_volume(volume_name)
    assert volume.standby is False
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    wait_for_volume_detached(client, volume_name)

    volume = client.by_id_volume(volume_name)
    engine = get_volume_engine(volume)
    assert engine.lastRestoredBackup == ""
    assert engine.requestedBackupRestore == ""


def check_volume_last_backup(client, volume_name, last_backup):
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        if volume.lastBackup == last_backup:
            break
        time.sleep(RETRY_INTERVAL)
    volume = client.by_id_volume(volume_name)
    assert volume.lastBackup == last_backup


def generate_pod_with_pvc_manifest(pod_name, pvc_name):
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
           "name": pod_name,
           "namespace": "default"
        },
        "spec": {
           "containers": [
              {
                 "name": "volume-test",
                 "image": "nginx:stable-alpine",
                 "imagePullPolicy": "IfNotPresent",
                 "volumeMounts": [
                    {
                       "name": "volv",
                       "mountPath": "/data"
                    }
                 ],
                 "ports": [
                    {
                       "containerPort": 80
                    }
                 ]
              }
           ],
           "volumes": [
              {
                 "name": "volv",
                 "persistentVolumeClaim": {
                    "claimName": pvc_name
                 }
              }
           ]
        }
    }

    return pod_manifest


def delete_and_wait_volume_attachment(storage_api, volume_attachment_name):
    try:
        storage_api.delete_volume_attachment(
            name=volume_attachment_name
        )
    except ApiException as e:
        assert e.status == 404

    wait_delete_volume_attachment(storage_api, volume_attachment_name)


def wait_delete_volume_attachment(storage_api, volume_attachment_name):
    for i in range(RETRY_COUNTS):
        found = False
        ret = storage_api.list_volume_attachment()
        for item in ret.items:
            if item.metadata.name == volume_attachment_name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_for_engine_image_deletion(client, core_api, engine_image_name):
    deleted = False

    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)
        deleted = True

        ei_list = client.list_engine_image().data
        for ei in ei_list:
            if ei.name == engine_image_name:
                deleted = False
                break
        if not deleted:
            continue

        labels = "longhorn.io/component=engine-image," \
                 "longhorn.io/engine-image="+engine_image_name
        ei_pod_list = core_api.list_namespaced_pod(
            LONGHORN_NAMESPACE, label_selector=labels).items
        if len(ei_pod_list) != 0:
            deleted = False
            continue
        if deleted:
            break

    assert deleted


def create_snapshot(longhorn_api_client, volume_name):
    volume = longhorn_api_client.by_id_volume(volume_name)
    snapshots = volume.snapshotList(volume=volume_name)
    snap = volume.snapshotCreate()
    snap_name = snap.name

    snapshot_created = False
    for i in range(RETRY_COUNTS):
        snapshots = volume.snapshotList(volume=volume_name)

        for vs in snapshots.data:
            if vs.name == snap_name:
                snapshot_created = True
                break
        if snapshot_created is True:
            break
        time.sleep(RETRY_INTERVAL)

    assert snapshot_created
    return snap


def wait_for_snapshot_count(volume, number, retry_counts=120):
    ok = False
    for _ in range(retry_counts):
        count = 0
        for snapshot in volume.snapshotList():
            if snapshot.removed is False:
                count += 1
        if count == number:
            ok = True
            break
        time.sleep(RETRY_SNAPSHOT_INTERVAL)
    assert ok


def wait_and_get_pv_for_pvc(api, pvc_name):
    found = False
    for i in range(RETRY_COUNTS):
        pvs = api.list_persistent_volume()
        for item in pvs.items:
            if item.spec.claim_ref.name == pvc_name:
                found = True
                pv = item
                break
        if found:
            break
        time.sleep(RETRY_INTERVAL)

    assert found
    return pv


def wait_for_volume_expansion(longhorn_api_client, volume_name):
    complete = False
    for i in range(RETRY_COUNTS):
        volume = longhorn_api_client.by_id_volume(volume_name)
        engine = get_volume_engine(volume)
        if engine.size == volume.size and volume.state == "detached":
            complete = True
            break
        time.sleep(RETRY_INTERVAL)
    assert complete


def check_block_device_size(volume, size):
    dev = get_volume_endpoint(volume)
    # BLKGETSIZE64, result is bytes as unsigned 64-bit integer (uint64)
    req = 0x80081272
    buf = ' ' * 8
    with open(dev) as dev:
        buf = fcntl.ioctl(dev.fileno(), req, buf)
    device_size = struct.unpack('L', buf)[0]
    assert device_size == size


def wait_for_dr_volume_expansion(longhorn_api_client, volume_name, size_str):
    complete = False
    for i in range(RETRY_COUNTS):
        volume = longhorn_api_client.by_id_volume(volume_name)
        if volume.size == size_str:
            engine = get_volume_engine(volume)
            if engine.size == volume.size:
                complete = True
                break
        time.sleep(RETRY_INTERVAL)
    assert complete


def expand_and_wait_for_pvc(api, pvc):
    pvc_name = pvc['metadata']['name']
    api.patch_namespaced_persistent_volume_claim(
        pvc_name, 'default', pvc)
    complete = False
    for i in range(RETRY_COUNTS):
        claim = api.read_namespaced_persistent_volume_claim(
            name=pvc_name, namespace='default')
        if claim.spec.resources.requests['storage'] ==\
                claim.status.capacity['storage']:
            complete = True
            break
        time.sleep(RETRY_INTERVAL)
    assert complete
    return claim


def wait_for_pvc_phase(api, pvc_name, phase):
    complete = False
    for _ in range(RETRY_COUNTS):
        pvc = api.read_namespaced_persistent_volume_claim(
            name=pvc_name, namespace='default')
        try:
            assert pvc.status.phase == phase
            complete = True
            break
        except AssertionError:
            pass
        time.sleep(RETRY_INTERVAL)
    assert complete
    return pvc


def fail_replica_expansion(client, api, volname, size, replicas=None):
    if replicas is None:
        volume = client.by_id_volume(volname)
        replicas = volume.replicas

    for r in replicas:
        tmp_meta_file_name = \
            EXPANSION_SNAP_TMP_META_NAME_PATTERN % size
        # os.path.join() cannot deal with the path containing "/"
        cmd = [
            '/bin/sh', '-c',
            'mkdir %s && sync' %
            (INSTANCE_MANAGER_HOST_PATH_PREFIX + r.dataPath +
             "/" + tmp_meta_file_name)
        ]
        if not r.instanceManagerName:
            raise Exception(
                "Should use replica objects in the running volume,"
                "otherwise the field r.instanceManagerName is emtpy")
        stream(api.connect_get_namespaced_pod_exec,
               r.instanceManagerName,
               LONGHORN_NAMESPACE, command=cmd,
               stderr=True, stdin=False, stdout=True, tty=False)


def wait_for_expansion_failure(client, volume_name, last_failed_at=""):
    failed = False
    for i in range(30):
        volume = client.by_id_volume(volume_name)
        engine = get_volume_engine(volume)
        if engine.lastExpansionFailedAt != last_failed_at:
            failed = True
            break
        time.sleep(RETRY_INTERVAL)
    assert failed


def wait_for_rebuild_complete(client, volume_name):
    completed = 0
    rebuild_statuses = {}
    for i in range(RETRY_COUNTS):
        completed = 0
        v = client.by_id_volume(volume_name)
        rebuild_statuses = v.rebuildStatus
        for status in rebuild_statuses:
            if status.state == "complete":
                assert status.progress == 100
                assert not status.error
                assert not status.isRebuilding
                completed += 1
            elif status.state == "":
                assert not status.error
                assert not status.isRebuilding
                completed += 1
            elif status.state == "in_progress":
                assert status.isRebuilding
            else:
                assert status.state == "error"
                assert status.error != ""
                assert not status.isRebuilding
        if completed == len(rebuild_statuses):
            break
        time.sleep(RETRY_INTERVAL)
    assert completed == len(rebuild_statuses)


def wait_for_rebuild_start(client, volume_name):
    started = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)
        rebuild_statuses = v.rebuildStatus
        for status in rebuild_statuses:
            if status.state == "in_progress":
                started = True
                break
        if started:
            break
        time.sleep(RETRY_INTERVAL)
    assert started
    return status.fromReplica, status.replica


def wait_for_volume_restoration_completed(client, name):
    wait_for_volume_creation(client, name)
    monitor_restore_progress(client, name)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_RESTOREREQUIRED,
                                  False)


def wait_for_backup_restore_completed(client, name, backup_name):
    complete = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(name)
        if v.controllers and len(v.controllers) != 0 and \
                v.controllers[0].lastRestoredBackup == backup_name:
            complete = True
            break
        time.sleep(RETRY_INTERVAL_LONG)
    assert complete


def wait_for_volume_restoration_start(client, volume_name, backup_name,
                                      progress=0):
    wait_for_volume_status(client, volume_name,
                           VOLUME_FIELD_STATE, VOLUME_STATE_ATTACHED)
    started = False
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        for status in volume.restoreStatus:
            if status.state == "in_progress" and \
                    status.progress > progress:
                started = True
                break
        #  Sometime the restore time is pretty short
        #  and the test may not be able to catch the intermediate status.
        if volume.controllers[0].lastRestoredBackup == backup_name:
            started = True
        if started:
            break
        time.sleep(RETRY_INTERVAL)
    assert started
    return status.replica


@pytest.fixture
def make_deployment_with_pvc(request):
    def _generate_deployment_with_pvc_manifest(deployment_name, pvc_name, replicas=1): # NOQA
        make_deployment_with_pvc.deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
               "name": deployment_name,
               "labels": {
                  "name": deployment_name
               }
            },
            "spec": {
               "replicas": replicas,
               "selector": {
                  "matchLabels": {
                     "name": deployment_name
                  }
               },
               "template": {
                  "metadata": {
                     "labels": {
                        "name": deployment_name
                     }
                  },
                  "spec": {
                     "containers": [
                        {
                           "name": deployment_name,
                           "image": "nginx:stable-alpine",
                           "volumeMounts": [
                              {
                                 "name": "volv",
                                 "mountPath": "/data"
                              }
                           ]
                        }
                     ],
                     "volumes": [
                        {
                           "name": "volv",
                           "persistentVolumeClaim": {
                              "claimName": pvc_name
                           }
                        }
                     ]
                  }
               }
            }
        }

        return make_deployment_with_pvc.deployment_manifest

    def finalizer():
        apps_api = get_apps_api_client()
        deployment_name = \
            make_deployment_with_pvc.deployment_manifest["metadata"]["name"]
        delete_and_wait_deployment(
            apps_api,
            deployment_name
        )

    request.addfinalizer(finalizer)

    return _generate_deployment_with_pvc_manifest


def wait_deployment_replica_ready(apps_api, deployment_name,
                                  desired_replica_count, namespace='default'):  # NOQA
    for i in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        deployment = apps_api.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace)

        # deployment is none if deployment is not yet created
        if deployment is not None and \
           deployment.status.ready_replicas == desired_replica_count:
            break

        time.sleep(DEFAULT_DEPLOYMENT_INTERVAL)


def create_and_wait_deployment(apps_api, deployment_manifest):
    apps_api.create_namespaced_deployment(
        body=deployment_manifest,
        namespace='default')

    deployment_name = deployment_manifest["metadata"]["name"]
    desired_replica_count = deployment_manifest["spec"]["replicas"]

    wait_deployment_replica_ready(
        apps_api,
        deployment_name,
        desired_replica_count
    )


def wait_and_get_any_deployment_pod(core_api, deployment_name,
                                    is_phase="Running"):
    for _ in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        label_selector = "name=" + deployment_name
        pods = core_api.list_namespaced_pod(namespace="default",
                                            label_selector=label_selector)
        for pod in pods.items:
            if pod.status.phase == is_phase:
                return pod

        time.sleep(DEFAULT_DEPLOYMENT_INTERVAL)
    assert False


def wait_delete_deployment(apps_api, deployment_name):
    for i in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        ret = apps_api.list_namespaced_deployment(namespace='default')
        found = False
        for item in ret.items:
            if item.metadata.name == deployment_name:
                found = True
                break
        if not found:
            break
        time.sleep(DEFAULT_DEPLOYMENT_INTERVAL)
    assert not found


def delete_and_wait_deployment(apps_api, deployment_name, namespace='default'):
    try:
        apps_api.delete_namespaced_deployment(
            name=deployment_name,
            namespace=namespace
        )
    except ApiException as e:
        assert e.status == 404

    wait_delete_deployment(apps_api, deployment_name)


def get_deployment_pod_names(core_api, deployment):
    label_selector = \
        "name=" + deployment["metadata"]["labels"]["name"]
    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=label_selector)
    pod_names = []
    for pod in deployment_pod_list.items:
        pod_names.append(pod.metadata.name)
    return pod_names


@pytest.fixture
def disable_auto_salvage(client):
    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="false")

    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "false"

    yield

    auto_salvage_setting = client.by_id_setting(SETTING_AUTO_SALVAGE)
    setting = client.update(auto_salvage_setting, value="true")

    assert setting.name == SETTING_AUTO_SALVAGE
    assert setting.value == "true"


def get_liveness_probe_spec(initial_delay=5, period=5):
    pod_liveness_probe_spec = {
        "exec": {
            "command": [
                "ls",
                "/data/lost+found"
            ]
        },
        "initialDelaySeconds": initial_delay,
        "periodSeconds": period
    }

    return pod_liveness_probe_spec


def wait_for_pod_remount(core_api, pod_name, chk_path="/data/lost+found"):
    check_command = [
        '/bin/sh',
        '-c',
        'ls ' + chk_path
    ]

    ready = False
    for i in range(RETRY_EXEC_COUNTS):
        try:
            output = stream(core_api.connect_get_namespaced_pod_exec,
                            pod_name,
                            'default',
                            command=check_command,
                            stderr=True, stdin=False,
                            stdout=True, tty=False)
            if "Input/output error" not in output:
                ready = True
                break
        except Exception:
            pass
        if ready:
            break
        time.sleep(RETRY_EXEC_INTERVAL)
    assert ready


def expand_attached_volume(client, volume_name):
    volume = wait_for_volume_healthy(client, volume_name)
    engine = get_volume_engine(volume)

    volume.detach(hostId="")
    volume = wait_for_volume_detached(client, volume.name)
    volume.expand(size=EXPAND_SIZE)
    wait_for_volume_expansion(client, volume.name)
    volume.attach(hostId=engine.hostId, disableFrontend=False)
    wait_for_volume_healthy(client, volume_name)


def prepare_statefulset_with_data_in_mb(
        client, core_api, statefulset, sts_name, storage_class,
        data_path="/data/test",
        data_size_in_mb=DATA_SIZE_IN_MB_1):
    update_statefulset_manifests(statefulset, storage_class, sts_name)
    statefulset['spec']['replicas'] = 1

    create_storage_class(storage_class)
    create_and_wait_statefulset(statefulset)

    pod_info = get_statefulset_pod_info(core_api, statefulset)
    volumes = client.list_volume()
    assert len(volumes) == statefulset['spec']['replicas']

    vol_name = None
    pod_name = None
    md5sum = None
    for v in volumes:
        info = pod_info[0]
        if v.name == info['pv_name']:
            write_pod_volume_random_data(core_api, info['pod_name'],
                                         data_path, data_size_in_mb)
            md5sum = get_pod_data_md5sum(core_api, info['pod_name'],
                                         data_path)
            stream(core_api.connect_get_namespaced_pod_exec,
                   info['pod_name'], 'default', command=["sync"],
                   stderr=True, stdin=False, stdout=True, tty=False)

            vol_name = v.name
            pod_name = info['pod_name']
            break

    assert vol_name is not None
    assert pod_name is not None
    assert md5sum is not None
    return vol_name, pod_name, md5sum


def prepare_pod_with_data_in_mb(
        client, core_api, csi_pv, pvc, pod_make, volume_name,
        volume_size=str(1*Gi), num_of_replicas=3, data_path="/data/test",
        data_size_in_mb=DATA_SIZE_IN_MB_1, add_liveness_probe=True):# NOQA:

    pod_name = volume_name + "-pod"
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"

    pod = pod_make(name=pod_name)
    csi_pv['metadata']['name'] = pv_name
    csi_pv['spec']['csi']['volumeHandle'] = volume_name
    csi_pv['spec']['capacity']['storage'] = volume_size
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['volumeName'] = pv_name
    pvc['spec']['resources']['requests']['storage'] = volume_size
    pvc['spec']['storageClassName'] = ''
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]

    if add_liveness_probe is True:
        pod_liveness_probe_spec = \
            get_liveness_probe_spec(initial_delay=1,
                                    period=1)
        pod['spec']['containers'][0]['livenessProbe'] = \
            pod_liveness_probe_spec

    create_and_check_volume(client, volume_name,
                            num_of_replicas=num_of_replicas,
                            size=volume_size)
    core_api.create_persistent_volume(csi_pv)
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    create_and_wait_pod(core_api, pod)

    write_pod_volume_random_data(core_api, pod_name,
                                 data_path, data_size_in_mb)
    md5sum = get_pod_data_md5sum(core_api, pod_name, data_path)

    stream(core_api.connect_get_namespaced_pod_exec,
           pod_name, 'default', command=["sync"],
           stderr=True, stdin=False, stdout=True, tty=False)

    return pod_name, pv_name, pvc_name, md5sum


@pytest.fixture
def settings_reset():
    yield

    client = get_longhorn_api_client()
    reset_settings(client)


def crash_engine_process_with_sigkill(client, core_api, volume_name):
    volume = client.by_id_volume(volume_name)
    ins_mgr_name = volume.controllers[0].instanceManagerName

    kill_command = [
            '/bin/sh', '-c',
            "kill -9 `ps aux | grep -i \"controller " +
            volume_name + "\" | grep -v grep | awk '{print $2}'`"]

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        stream(core_api.connect_get_namespaced_pod_exec,
               ins_mgr_name,
               LONGHORN_NAMESPACE, command=kill_command,
               stderr=True, stdin=False, stdout=True, tty=False)


def wait_for_pod_restart(core_api, pod_name, namespace="default"):
    pod = core_api.read_namespaced_pod(name=pod_name,
                                       namespace=namespace)
    restart_count = pod.status.container_statuses[0].restart_count

    pod_restarted = False
    for i in range(RETRY_COUNTS):
        pod = core_api.read_namespaced_pod(name=pod_name,
                                           namespace=namespace)
        count = pod.status.container_statuses[0].restart_count
        if count > restart_count:
            pod_restarted = True
            break

        time.sleep(RETRY_INTERVAL)
    assert pod_restarted


def wait_for_pod_phase(core_api, pod_name, pod_phase, namespace="default"):
    is_phase = False
    for _ in range(RETRY_COUNTS):
        pod = core_api.read_namespaced_pod(name=pod_name,
                                           namespace=namespace)
        if pod.status.phase == pod_phase:
            is_phase = True
            break

        time.sleep(RETRY_INTERVAL_LONG)
    assert is_phase


def wait_for_pods_volume_state(client, pod_list, field, value,  # NOQA
                               retry_counts=RETRY_COUNTS):
    for _ in range(retry_counts):
        volume_names = []
        volumes = client.list_volume()
        for v in volumes:
            for p in pod_list:
                if v.name == p['pv_name'] and v[field] == value:
                    volume_names.append(v.name)
                    break
        time.sleep(RETRY_INTERVAL)
    return len(volume_names) == len(pod_list)


def wait_for_pods_volume_delete(client, pod_list,  # NOQA
                                retry_counts=RETRY_BACKUP_COUNTS):
    volume_deleted = False
    for _ in range(retry_counts):
        volume_deleted = True
        volumes = client.list_volume()
        for v in volumes:
            for p in pod_list:
                if v.name == p['pv_name']:
                    volume_deleted = False
                    break
        time.sleep(RETRY_INTERVAL)
    assert volume_deleted is True


def wait_for_instance_manager_desire_state(client, core_api, im_name,
                                           state, desire=True):
    for i in range(RETRY_COUNTS):
        im = client.by_id_instance_manager(im_name)
        try:
            pod = core_api.read_namespaced_pod(name=im_name,
                                               namespace=LONGHORN_NAMESPACE)
        except Exception as e:
            # Continue with pod restarted case
            if e.reason == "Not Found":
                time.sleep(RETRY_INTERVAL)
                continue
            # Report any other error
            else:
                assert(not e)
        if desire:
            if im.currentState == state.lower() and pod.status.phase == state:
                break
        else:
            if im.currentState != state.lower() and pod.status.phase != state:
                break
        time.sleep(RETRY_INTERVAL)
    if desire:
        assert im.currentState == state.lower()
        assert pod.status.phase == state
    else:
        assert im.currentState != state.lower()
        assert pod.status.phase != state
    return im


def wait_for_backup_delete(client, volume_name, backup_name):

    def find_backup_volume():
        bvs = client.list_backupVolume()
        for bv in bvs:
            if bv.name == volume_name:
                return bv
        return None

    def backup_exists():
        bv = find_backup_volume()
        if bv is not None:
            backups = bv.backupList()
            for b in backups:
                if b.name == backup_name:
                    return True
        return False

    for i in range(RETRY_BACKUP_COUNTS):
        if backup_exists() is False:
            return
        time.sleep(RETRY_BACKUP_INTERVAL)

    assert False, "deleted backup " + backup_name + " for volume " \
                  + volume_name + " is still present"


def assert_backup_state(b_actual, b_expected):
    assert b_expected.name == b_actual.name
    assert b_expected.url == b_actual.url
    assert b_expected.snapshotName == b_actual.snapshotName
    assert b_expected.snapshotCreated == b_actual.snapshotCreated
    assert b_expected.created == b_actual.created
    assert b_expected.volumeName == b_actual.volumeName
    assert b_expected.volumeSize == b_actual.volumeSize
    assert b_expected.volumeCreated == b_actual.volumeCreated
    assert b_expected.messages == b_actual.messages is None


def create_backing_image_with_matching_url(client, name, url):
    backing_images = client.list_backing_image()
    found = False
    for bi in backing_images:
        if bi.name == name:
            found = True
            break
    if found:
        if bi.sourceType != BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD or \
                bi.parameters["url"] != url:
            client.delete(bi)
            bi = client.by_id_backing_image(name=name)
        if bi is None or bi.deletionTimestamp != "":
            wait_for_backing_image_delete(client, name)
            found = False
    if not found:
        expected_checksum = ""
        # Only the following 2 URLs will be used in the integration tests
        # for now.
        if url == BACKING_IMAGE_RAW_URL:
            expected_checksum = BACKING_IMAGE_RAW_CHECKSUM
        elif url == BACKING_IMAGE_QCOW2_URL:
            expected_checksum = BACKING_IMAGE_QCOW2_CHECKSUM
        bi = client.create_backing_image(
            name=name, sourceType=BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD,
            parameters={"url": url}, expectedChecksum=expected_checksum)
    assert bi

    is_ready = False
    for i in range(RETRY_COUNTS):
        bi = client.by_id_backing_image(name)
        if len(bi.diskFileStatusMap) == 1 and bi.currentChecksum != "":
            for disk, status in iter(bi.diskFileStatusMap.items()):
                if status.state == "ready":
                    is_ready = True
                    break
            if is_ready:
                break
        time.sleep(RETRY_INTERVAL)

    return bi


def wait_for_backing_image_disk_cleanup(client, bi_name, disk_id):
    found = False
    for i in range(RETRY_COUNTS):
        found = False
        bi = client.by_id_backing_image(bi_name)
        for disk, status in iter(bi.diskFileStatusMap.items()):
            if disk == disk_id:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found
    return bi


def wait_for_backing_image_delete(client, name):
    found = False
    for i in range(RETRY_COUNTS):
        bi_list = client.list_backing_image()
        found = False
        for bi in bi_list:
            if bi.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def cleanup_all_backing_images(client):
    backing_images = client.list_backing_image()
    for bi in backing_images:
        try:
            client.delete(bi)
        except Exception as e:
            print("\nException when cleanup backing image ", bi)
            print(e)
    for i in range(RETRY_COUNTS):
        backing_images = client.list_backing_image()
        if len(backing_images) == 0:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(client.list_backing_image()) == 0


# this function will check if backing image feature is supported, and is added
# for the case of test_upgrade starting from Longhorn <= v1.1.0
def backing_image_feature_supported(client):
    if hasattr(client.by_id_schema("backingImage"), "id"):
        return True
    else:
        return False


# this function will check if recurring job feature is supported, and is added
# for the case of test_upgrade starting from Longhorn >= v1.2.0
def recurring_job_feature_supported(client):
    if hasattr(client.by_id_schema("volumeRecurringJob"), "id"):
        return True
    else:
        return False


def cleanup_all_recurring_jobs(client):
    recurring_jobs = client.list_recurring_job()
    for recurring_job in recurring_jobs:
        try:
            client.delete(recurring_job)
        except Exception as e:
            print("\nException when cleanup recurring job ", recurring_job)
            print(e)
    wait_for_recurring_jobs_cleanup(client)


def wait_for_recurring_jobs_cleanup(client):
    for _ in range(RETRY_COUNTS):
        policies = client.list_recurring_job()
        if len(policies) == 0:
            break
        time.sleep(RETRY_INTERVAL)
    assert len(client.list_recurring_job()) == 0


# get correct engine image status based on Longhorn version
# Longhorn <= v1.1.0   ei.status == "ready"
# Longhorn >= v1.1.1   ei.status == "deployed"
def get_engine_image_status_value(client, ei_name):
    if hasattr(client.by_id_engine_image(ei_name), "nodeDeploymentMap"):
        return "deployed"
    else:
        return "ready"


def update_setting(client, name, value):
    setting = client.by_id_setting(name)
    client.update(setting, value=value)


def create_recurring_jobs(client, recurring_jobs):
    time.sleep(60 - datetime.utcnow().second)

    for name, spec in recurring_jobs.items():
        client.create_recurring_job(Name=name,
                                    Task=spec["task"],
                                    Groups=spec["groups"],
                                    Cron=spec["cron"],
                                    Retain=spec["retain"],
                                    Concurrency=spec["concurrency"],
                                    Labels=spec["labels"])


def check_recurring_jobs(client, recurring_jobs):
    for name, spec in recurring_jobs.items():
        recurring_job = client.by_id_recurring_job(name)
        assert recurring_job.name == name
        assert recurring_job.task == spec["task"]
        if len(spec["groups"]) > 0:
            assert recurring_job.groups == spec["groups"]
        assert recurring_job.cron == spec["cron"]
        assert recurring_job.retain == spec["retain"]
        assert recurring_job.concurrency == spec["concurrency"]


def update_recurring_job(client, name, groups, labels, # NOQA
                         cron="", retain=0, concurrency=0):
    recurringJob = client.by_id_recurring_job(name)

    update_groups = groups
    update_labels = labels
    update_cron = cron if len(cron) != 0 else recurringJob["cron"]
    update_retain = retain if retain != 0 else recurringJob["retain"]
    update_concurrency = \
        concurrency if concurrency != 0 else recurringJob["concurrency"]

    client.update(recurringJob,
                  groups=update_groups,
                  task=recurringJob["task"],
                  cron=update_cron,
                  retain=update_retain,
                  concurrency=update_concurrency,
                  labels=update_labels)


def get_volume_recurring_jobs_and_groups(volume):
    volumeJobs = volume.recurringJobList()
    jobs = []
    groups = []
    for volumeJob in volumeJobs:
        if volumeJob['isGroup']:
            groups.append(volumeJob['name'])
        else:
            jobs.append(volumeJob['name'])
    return jobs, groups


def wait_for_volume_recurring_job_update(volume, jobs=[], groups=[]):
    ok = False
    for _ in range(RETRY_COUNTS):
        volumeJobs, volumeGroups = get_volume_recurring_jobs_and_groups(volume)
        try:
            assert len(volumeGroups) == len(groups)
            for group in groups:
                assert group in volumeGroups

            assert len(volumeJobs) == len(jobs)
            for job in jobs:
                assert job in volumeJobs

            ok = True
            break
        except AssertionError:
            time.sleep(RETRY_INTERVAL)
    assert ok


def wait_for_cron_job_create(batch_v1_beta_api, label="",
                             retry_counts=RETRY_COUNTS):
    exist = False
    for _ in range(retry_counts):
        job = batch_v1_beta_api.list_namespaced_cron_job('longhorn-system',
                                                         label_selector=label)
        if len(job.items) != 0:
            exist = True
            break
        time.sleep(RETRY_INTERVAL)

    assert exist


def wait_for_cron_job_delete(batch_v1_beta_api, label="",
                             retry_counts=RETRY_COUNTS):
    exist = True
    for _ in range(retry_counts):
        job = batch_v1_beta_api.list_namespaced_cron_job('longhorn-system',
                                                         label_selector=label)
        if len(job.items) == 0:
            exist = False
            break
        time.sleep(RETRY_INTERVAL)

    assert not exist


def wait_for_cron_job_count(batch_v1_beta_api, number, label="",
                            retry_counts=RETRY_COUNTS):
    ok = False
    for _ in range(retry_counts):
        jobs = batch_v1_beta_api.list_namespaced_cron_job('longhorn-system',
                                                          label_selector=label)
        if len(jobs.items) == number:
            ok = True
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def wait_for_pod_annotation(core_api,
                            label_selector, anno_key, anno_val):
    matches = False
    for _ in range(RETRY_COUNTS):
        pods = core_api.list_namespaced_pod(
            namespace='longhorn-system', label_selector=label_selector)
        if anno_val is None:
            if any(pod.metadata.annotations is None or
                   pod.metadata.annotations.get(anno_key, None) is None
                   for pod in pods.items):
                matches = True
                break
        else:
            if any(pod.metadata.annotations is not None and
                    pod.metadata.annotations.get(anno_key, None) == anno_val
                   for pod in pods.items):
                matches = True
                break
        time.sleep(RETRY_INTERVAL)
    assert matches is True


def wait_for_volume_clone_status(client, name, key, value):
    for _ in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume[VOLUME_FIELD_CLONE_STATUS][key] == value:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume[VOLUME_FIELD_CLONE_STATUS][key] == value, \
        f" Expected value={value}\n. " \
        f" Got volume[{VOLUME_FIELD_CLONE_STATUS}][{key}]= " \
        f"{volume[VOLUME_FIELD_CLONE_STATUS][key]}\n. volume={volume}"
    return volume


def get_clone_volume_name(client, source_volume_name):
    for _ in range(RETRY_EXEC_COUNTS):
        volumes = client.list_volume()
        for volume in volumes:
            if volume['cloneStatus']['sourceVolume'] == \
                    source_volume_name:
                return volume.name
        time.sleep(RETRY_INTERVAL_LONG)
    return None


def create_backup_from_volume_attached_to_pod(client, core_api,
                                              volume_name, pod_name,
                                              data_path='/data/test',
                                              data_size=DATA_SIZE_IN_MB_1):
    """
        Write data in the pod and take a backup.
        Args:
            client: The Longhorn client to use in the request.
            core_api: An instance of CoreV1API.
            pod_name: The name of the Pod.
            volume_name: The volume name which is attached to the pod.
            data_path: File name suffixed to the mount point. e.g /data/file
            data_size: Size of the data to be written in the pod.
        Returns:
            The backup volume name, backup, checksum of data written in the
            backup
    """
    write_pod_volume_random_data(core_api, pod_name,
                                 data_path, data_size)
    data_checksum = get_pod_data_md5sum(core_api, pod_name, data_path)

    snap = create_snapshot(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    backup_volume, backup = find_backup(client, volume_name, snap.name)

    return backup_volume, backup, data_checksum


def restore_backup_and_get_data_checksum(client, core_api, backup, pod,
                                         file_name='', command=''):
    """
        Restore the backup in a pod and get the checksum of all the files
        or checksum of a particular file.
        Args:
            client: The Longhorn client to use in the request.
            core_api: An instance of CoreV1API.
            backup: The backup to be restored.
            pod: Pod fixture.
            file_name: Optional - File whose checksum to be computed.
            command: Optional - command to be executed in the pod.
        Returns:
            The checksum as a dictionary as in file_name=checksum and the
            output of the command executed in the pod.
    """
    restore_volume_name = generate_volume_name() + "-restore"
    restore_pod_name = restore_volume_name + "-pod"
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"
    data_checksum = {}

    client.create_volume(name=restore_volume_name, size=str(1 * Gi),
                         fromBackup=backup.url)
    volume = wait_for_volume_detached(client, restore_volume_name)
    create_pv_for_volume(client, core_api, volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, volume, restore_pvc_name)
    pod['metadata']['name'] = restore_pod_name
    pod['spec']['volumes'] = [{
        'name': pod['spec']['containers'][0]['volumeMounts'][0]['name'],
        'persistentVolumeClaim': {
            'claimName': restore_pvc_name,
        },
    }]
    create_and_wait_pod(core_api, pod)

    restore_volume = client.by_id_volume(restore_volume_name)
    assert restore_volume[VOLUME_FIELD_ROBUSTNESS] == VOLUME_ROBUSTNESS_HEALTHY

    if file_name == '':
        file_list = exec_command_in_pod(core_api, 'ls /data', restore_pod_name,
                                        'default')
        file_list = file_list.strip()
        file_list = file_list.split('\n')
        if len(file_list) > 0:
            for file_name in file_list:
                data_path = '/data/' + file_name
                data_checksum[file_name] = \
                    get_pod_data_md5sum(core_api, restore_pod_name, data_path)
    else:
        data_path = '/data/' + file_name
        data_checksum[file_name] = get_pod_data_md5sum(core_api,
                                                       restore_pod_name,
                                                       data_path)

    # This is optional, if you want to execute any command and get the output
    output = ''
    if command != '':
        output = exec_command_in_pod(core_api, command, restore_pod_name,
                                     'default')

    return data_checksum, output, restore_pod_name


def generate_support_bundle(case_name):
    """
        Generate support bundle into folder ./support_bundle/case_name.zip

        Won't generate support bundle if current support bundle count
        greate than MAX_SUPPORT_BINDLE_NUMBER.
        Args:
            case_name: support bundle will named case_name.zip
    """

    os.makedirs("support_bundle", exist_ok=True)
    file_cnt = len(os.listdir("support_bundle"))

    if file_cnt >= MAX_SUPPORT_BINDLE_NUMBER:
        warnings.warn("Ignoring the bundle download because of \
                            avoiding overwhelming the disk usage.")
        return

    # Use API gen support bundle
    client = get_longhorn_api_client()
    url = client._url.replace('schemas', 'supportbundles')
    data = {'description': case_name, 'issueURL': case_name}
    res = requests.post(url, json=data).json()

    id = res['id']
    name = res['name']

    support_bundle_url = '{}/{}/{}'.format(url, id, name)
    for i in range(RETRY_EXEC_COUNTS):
        res = requests.get(support_bundle_url).json()

        if res['progressPercentage'] == 100:
            break
        else:
            time.sleep(RETRY_INTERVAL_LONG)

    if res['progressPercentage'] != 100:
        warnings.warn("Timeout to wait support bundle ready, skip download")
        return

    # Download support bundle
    download_url = '{}/download'.format(support_bundle_url)
    try:
        r = requests.get(download_url, allow_redirects=True, timeout=300)
        r.raise_for_status()
        with open('./support_bundle/{0}.zip'.format(case_name), 'wb') as f:
            f.write(r.content)
    except Exception as e:
        warnings.warn("Error occured while downloading support bundle {}.zip\n\
            The error was {}".format(case_name, e))


def get_volume_running_replica_cnt(client, volume_name):  # NOQA
    nodes = client.list_node()
    cnt = 0

    for node in nodes:
        cnt = cnt + get_host_replica_count(
            client, volume_name, node.name, chk_running=True)

    return cnt
