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
import types
import threading
import re
import ipaddress

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
from urllib.parse import urlparse

Ki = 1024
Mi = (1024 * 1024)
Gi = (1024 * Mi)

SIZE = str(32 * Mi)
# See https://github.com/longhorn/longhorn/issues/8488.
XFS_MIN_SIZE = str(300 * Mi)
EXPAND_SIZE = str(64 * Mi)
VOLUME_NAME = "longhorn-testvol"
ATTACHMENT_TICKET_ID_PREFIX = "test-attachment-ticket"
STATEFULSET_NAME = "longhorn-teststs"
DEV_PATH = "/dev/longhorn/"
VOLUME_RWTEST_SIZE = 512
VOLUME_INVALID_POS = -1

VOLUME_HEAD_NAME = "volume-head"

BACKING_IMAGE_NAME = "bi-test"
BACKING_IMAGE_QCOW2_URL = \
    "https://longhorn-backing-image.s3.dualstack.us-west-1.amazonaws.com/parrot.qcow2"  # NOQA
BACKING_IMAGE_QCOW2_CHECKSUM = \
    "bd79ab9e6d45abf4f3f0adf552a868074dd235c4698ce7258d521160e0ad79ffe555b94" \
    "e7d4007add6e1a25f4526885eb25c53ce38f7d344dd4925b9f2cb5d3b"
BACKING_IMAGE_RAW_URL = \
    "https://longhorn-backing-image.s3.dualstack.us-west-1.amazonaws.com/parrot.raw"    # NOQA
BACKING_IMAGE_RAW_CHECKSUM = \
    "304f3ed30ca6878e9056ee6f1b02b328239f0d0c2c1272840998212f9734b196371560b" \
    "3b939037e4f4c2884ce457c2cbc9f0621f4f5d1ca983983c8cdf8cd9a"
BACKING_IMAGE_EXT4_SIZE = 32 * Mi
BACKING_IMAGE_STATE_READY = "ready"
BACKING_IMAGE_STATE_IN_PROGRESS = "in-progress"
BACKING_IMAGE_STATE_FAILED = "failed"
BACKING_IMAGE_STATE_FAILED_AND_CLEANUP = "failed-and-cleanup"

PORT = ":9500"

RETRY_COMMAND_COUNT = 5
RETRY_COUNTS = 150
RETRY_COUNTS_SHORT = 30
RETRY_COUNTS_LONG = 360
RETRY_INTERVAL = 1
RETRY_INTERVAL_SHORT = 0.5
RETRY_INTERVAL_LONG = 2
RETRY_BACKUP_COUNTS = 300
RETRY_BACKUP_INTERVAL = 1
RETRY_SNAPSHOT_INTERVAL = 1
RETRY_EXEC_COUNTS = 30
RETRY_EXEC_INTERVAL = 5
RETRY_AUTOSCALER_INTERVAL = 30
RETRY_AUTOSCALER_COUNTS = 10*60//RETRY_AUTOSCALER_INTERVAL  # 10 minutes

LONGHORN_NAMESPACE = "longhorn-system"

COMPATIBILTY_TEST_IMAGE_PREFIX = "longhornio/longhorn-test:version-test"
UPGRADE_TEST_IMAGE_PREFIX = "longhornio/longhorn-test:upgrade-test"

ISCSI_DEV_PATH = "/dev/disk/by-path"
ISCSI_PROCESS = "iscsid"

if os.uname().machine == "x86_64":
    if os.environ.get("CLOUDPROVIDER") == "harvester":
        BLOCK_DEV_PATH = "/dev/vdc"
    else:
        BLOCK_DEV_PATH = "/dev/xvdh"
else:
    BLOCK_DEV_PATH = "/dev/nvme1n1"

VOLUME_FIELD_STATE = "state"
VOLUME_STATE_ATTACHED = "attached"
VOLUME_STATE_DETACHED = "detached"

VOLUME_FIELD_ROBUSTNESS = "robustness"
VOLUME_ROBUSTNESS_HEALTHY = "healthy"
VOLUME_ROBUSTNESS_DEGRADED = "degraded"
VOLUME_ROBUSTNESS_FAULTED = "faulted"
VOLUME_ROBUSTNESS_UNKNOWN = "unknown"

VOLUME_FIELD_RESTOREREQUIRED = "restoreRequired"
VOLUME_FIELD_RESTOREINITIATED = "restoreInitiated"
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
POD_DELETION_TIMEOUT = 600

DEFAULT_STATEFULSET_INTERVAL = 1
DEFAULT_STATEFULSET_TIMEOUT = 180

DEFAULT_DEPLOYMENT_INTERVAL = 1
DEFAULT_DEPLOYMENT_TIMEOUT = 240
WAIT_FOR_POD_STABLE_MAX_RETRY = 90

DEFAULT_VOLUME_SIZE = 3  # In Gi
EXPANDED_VOLUME_SIZE = 4  # In Gi

DIRECTORY_PATH = '/var/lib/longhorn/longhorn-test/'

VOLUME_CONDITION_SCHEDULED = "Scheduled"
VOLUME_CONDITION_RESTORE = "Restore"
VOLUME_CONDITION_STATUS = "status"
VOLUME_CONDITION_TOOMANYSNAPSHOTS = "TooManySnapshots"

CONDITION_STATUS_TRUE = "True"
CONDITION_STATUS_FALSE = "False"
CONDITION_STATUS_UNKNOWN = "Unknown"

CONDITION_REASON_SCHEDULING_FAILURE = "ReplicaSchedulingFailure"

VOLUME_FRONTEND_BLOCKDEV = "blockdev"
VOLUME_FRONTEND_ISCSI = "iscsi"
VOLUME_FRONTEND_UBLK = "ublk"
VOLUME_FRONTEND_NVMF = "nvmf"

DEFAULT_DISK_PATH = "/var/lib/longhorn/"
DEFAULT_STORAGE_OVER_PROVISIONING_PERCENTAGE = "100"
DEFAULT_STORAGE_MINIMAL_AVAILABLE_PERCENTAGE = "10"
DEFAULT_LONGHORN_STATIC_STORAGECLASS_NAME = "longhorn-static"

DEFAULT_REPLICA_DIRECTORY = os.path.join(DEFAULT_DISK_PATH, "replicas/")

NODE_CONDITION_MOUNTPROPAGATION = "MountPropagation"
NODE_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_SCHEDULABLE = "Schedulable"
DISK_CONDITION_READY = "Ready"

STREAM_EXEC_TIMEOUT = 60

EXCEPTION_ERROR_REASON_NOT_FOUND = "Not Found"

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
SETTING_DETACH_MANUALLY_ATTACHED_VOLUMES_WHEN_CORDONED = \
    "detach-manually-attached-volumes-when-cordoned"
SETTING_GUARANTEED_INSTANCE_MANAGER_CPU = "guaranteed-instance-manager-cpu"
SETTING_PRIORITY_CLASS = "priority-class"
SETTING_RECURRING_JOB_WHILE_VOLUME_DETACHED = \
    "allow-recurring-job-while-volume-detached"
SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY = "replica-soft-anti-affinity"
SETTING_REPLICA_AUTO_BALANCE = "replica-auto-balance"
SETTING_REPLICA_AUTO_BALANCE_DISK_PRESSURE_PERCENTAGE = \
    "replica-auto-balance-disk-pressure-percentage"
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
SETTING_ORPHAN_AUTO_DELETION = "orphan-auto-deletion"
SETTING_ORPHAN_RESOURCE_AUTO_DELETION = "orphan-resource-auto-deletion"
SETTING_FAILED_BACKUP_TTL = "failed-backup-ttl"
SETTING_CONCURRENT_AUTO_ENGINE_UPGRADE_NODE_LIMIT = \
    "concurrent-automatic-engine-upgrade-per-node-limit"
SETTING_SUPPORT_BUNDLE_FAILED_LIMIT = "support-bundle-failed-history-limit"
SETTING_RESTORE_RECURRING_JOBS = "restore-volume-recurring-jobs"
SETTING_SNAPSHOT_DATA_INTEGRITY = "snapshot-data-integrity"
SETTING_SNAPSHOT_DATA_INTEGRITY_IMMEDIATE_CHECK_AFTER_SNAPSHOT_CREATION = \
    "snapshot-data-integrity-immediate-check-after-snapshot-creation"
SETTING_SNAPSHOT_DATA_INTEGRITY_CRONJOB = "snapshot-data-integrity-cronjob"
SETTING_SNAPSHOT_FAST_REPLICA_REBUILD_ENABLED = "fast-replica-rebuild-enabled"
SETTING_V2_SNAPSHOT_DATA_INTEGRITY = "v2-data-engine-snapshot-data-integrity"
SETTING_V2_SNAPSHOT_FAST_REPLICA_REBUILD_ENABLED = \
    "v2-data-engine-fast-replica-rebuilding"
SETTING_CONCURRENT_VOLUME_BACKUP_RESTORE = \
    "concurrent-volume-backup-restore-per-node-limit"
SETTING_NODE_SELECTOR = "system-managed-components-node-selector"
SETTING_K8S_CLUSTER_AUTOSCALER_ENABLED = \
    "kubernetes-cluster-autoscaler-enabled"
SETTING_CONCURRENT_REPLICA_REBUILD_PER_NODE_LIMIT = \
    "concurrent-replica-rebuild-per-node-limit"
SETTING_AUTO_CLEANUP_SYSTEM_GERERATED_SNAPSHOT = \
    "auto-cleanup-system-generated-snapshot"
SETTING_BACKUP_COMPRESSION_METHOD = "backup-compression-method"
SETTING_BACKUP_CONCURRENT_LIMIT = "backup-concurrent-limit"
SETTING_RESTORE_CONCURRENT_LIMIT = "restore-concurrent-limit"
SETTING_V1_DATA_ENGINE = "v1-data-engine"
SETTING_V2_DATA_ENGINE = "v2-data-engine"
SETTING_ALLOW_EMPTY_NODE_SELECTOR_VOLUME = \
    "allow-empty-node-selector-volume"
SETTING_REPLICA_DISK_SOFT_ANTI_AFFINITY = "replica-disk-soft-anti-affinity"
SETTING_ALLOW_EMPTY_DISK_SELECTOR_VOLUME = "allow-empty-disk-selector-volume"
SETTING_NODE_DRAIN_POLICY = "node-drain-policy"
SETTING_MIN_NUMBER_OF_BACKING_IMAGE_COPIES = \
    "default-min-number-of-backing-image-copies"

DEFAULT_BACKUP_COMPRESSION_METHOD = "lz4"
BACKUP_COMPRESSION_METHOD_LZ4 = "lz4"
BACKUP_COMPRESSION_METHOD_GZIP = "gzip"
BACKUP_COMPRESSION_METHOD_NONE = "none"

SNAPSHOT_DATA_INTEGRITY_IGNORED = "ignored"
SNAPSHOT_DATA_INTEGRITY_DISABLED = "disabled"
SNAPSHOT_DATA_INTEGRITY_ENABLED = "enabled"
SNAPSHOT_DATA_INTEGRITY_FAST_CHECK = "fast-check"

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

K8S_GKE_OS_DISTRO_LABEL = "cloud.google.com/gke-os-distribution"
K8S_GKE_OS_DISTRO_COS = "cos"

K8S_CLUSTER_AUTOSCALER_EVICT_KEY = \
    "cluster-autoscaler.kubernetes.io/safe-to-evict"
K8S_CLUSTER_AUTOSCALER_SCALE_DOWN_DISABLED_KEY = \
    "cluster-autoscaler.kubernetes.io/scale-down-disabled"

BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD = "download"
BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME = "export-from-volume"
BACKING_IMAGE_SOURCE_TYPE_RESTORE = "restore"

JOB_LABEL = "recurring-job.longhorn.io"

MAX_SUPPORT_BINDLE_NUMBER = 20

NODE_UPDATE_RETRY_INTERVAL = 6
NODE_UPDATE_RETRY_COUNT = 30
disk_being_syncing = "being syncing and please retry later"

FS_TYPE_EXT4 = "ext4"
FS_TYPE_XFS = "xfs"

ACCESS_MODE_RWO = "rwo"
ACCESS_MODE_RWX = "rwx"

ATTACHER_TYPE_CSI_ATTACHER = "csi-attacher"
ATTACHER_TYPE_LONGHORN_API = "longhorn-api"
ATTACHER_TYPE_LONGHORN_UPGRADER = "longhorn-upgrader"

HOST_PROC_DIR = "/host/proc"

BACKUP_TARGET_MESSAGE_EMPTY_URL = "backup target URL is empty"
BACKUP_TARGET_MESSAGES_INVALID = ["failed to init backup target clients",
                                  "failed to list backup volumes in",
                                  "error listing backup volume names"]

FAILED_DELETING_REASONE = "FailedDeleting"
BACKINGIMAGE_FAILED_EVICT_MSG = \
    "since there is no other healthy backing image copy"

# set default data engine for test
enable_v2 = os.environ.get('RUN_V2_TEST')
if enable_v2 == "true":
    DATA_ENGINE = "v2"
    RETRY_COUNTS = RETRY_COUNTS_LONG
    DEFAULT_POD_TIMEOUT = RETRY_COUNTS_LONG
else:
    DATA_ENGINE = "v1"

# customize the timeout for HDD
disktype = os.environ.get('LONGHORN_DISK_TYPE')
if disktype == "hdd":
    RETRY_COUNTS *= 32
    DEFAULT_POD_TIMEOUT *= 32
    DEFAULT_DEPLOYMENT_TIMEOUT *= 32
    DEFAULT_STATEFULSET_TIMEOUT *= 32
    STREAM_EXEC_TIMEOUT *= 32


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
    for _ in range(RETRY_COUNTS):
        try:
            k8sconfig.load_incluster_config()
            ips = get_mgr_ips()

            # check if longhorn manager port is open before calling get_client
            for ip in ips:
                # Determine if IP is IPv6
                family = socket.AF_INET6 if ':' in ip else socket.AF_INET
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.settimeout(RETRY_COUNTS_SHORT)

                try:
                    if sock.connect_ex((ip, 9500)) == 0:
                        return get_client(ip + PORT)
                finally:
                    sock.close()
        except Exception:
            time.sleep(RETRY_INTERVAL)

    raise Exception("Failed to get Longhorn API client after retries")


def cleanup_volume(client, volume):
    """
    Clean up the volume after the test.
    :param client: The Longhorn client to use in the request.
    :param volume: The volume to clean up.
    """
    volume.detach()
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
            wait_for_volume_delete(client, v.name)
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


def create_volume_and_backup(client, vol_name, vol_size, backup_data_size):
    client.create_volume(name=vol_name,
                         numberOfReplicas=1,
                         size=str(vol_size),
                         dataEngine=DATA_ENGINE)
    volume = wait_for_volume_detached(client, vol_name)
    volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, vol_name)

    data = {'pos': 0,
            'len': backup_data_size,
            'content': generate_random_data(backup_data_size)}

    _, backup, _, _ = create_backup(client, vol_name, data)

    return volume, backup


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


def delete_backup(client, bv, backup_name):
    bv.backupDelete(name=backup_name)
    wait_for_backup_delete(client, bv.volumeName, backup_name)


def delete_backup_volume(client, backup_volume_name):
    bv = client.by_id_backupVolume(backup_volume_name)
    client.delete(bv)
    wait_for_backup_volume_delete(client, backup_volume_name)


def delete_backup_backing_image(client, backing_image_name):
    bbi = client.by_id_backupBackingImage(backing_image_name)
    client.delete(bbi)
    wait_for_backup_backing_image_delete(client, backing_image_name)


def create_and_check_volume(client, volume_name,
                            num_of_replicas=3, size=SIZE, backing_image="",
                            frontend=VOLUME_FRONTEND_BLOCKDEV,
                            snapshot_data_integrity=SNAPSHOT_DATA_INTEGRITY_IGNORED,  # NOQA
                            access_mode=ACCESS_MODE_RWO, data_engine=DATA_ENGINE):  # NOQA
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
                         backingImage=backing_image, frontend=frontend,
                         snapshotDataIntegrity=snapshot_data_integrity,
                         accessMode=access_mode, dataEngine=data_engine)
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
        try:
            pod = api.read_namespaced_pod(
                name=pod_name,
                namespace='default')
            if pod is not None and pod.status.phase != 'Pending':
                break
        except Exception as e:
            print(f"Waiting for pod {pod_name} failed: {e}")
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


def delete_statefulset(apps_api, statefulset):
    ss_name = statefulset['metadata']['name']
    ss_namespace = statefulset['metadata']['namespace']
    apps_api.delete_namespaced_stateful_set(
        name=ss_name, namespace=ss_namespace,
        body=k8sclient.V1DeleteOptions()
    )

    for _ in range(DEFAULT_POD_TIMEOUT):
        ret = apps_api.list_namespaced_stateful_set(namespace=ss_namespace)
        found = False
        for item in ret.items:
            if item.metadata.name == ss_name:
                found = True
                break
        if not found:
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert not found


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
        # the status_code is 404.
        assert err.error.code == 404

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


def exec_command_in_pod(api, command, pod_name, namespace, container=None):
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
            container=container, tty=False)


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
        ' bs=1M' + ' count=' + str(size_in_mb) +
        '; sync'
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


def copy_file_to_volume_dev_mb_data(src_path, dest_path,
                                    src_offset, dest_offset, size_in_mb,
                                    timeout_cnt=5):
    cmd = [
        '/bin/sh',
        '-c',
        'dd if=%s of=%s bs=1M count=%d skip=%d seek=%d' %
        (src_path, dest_path, size_in_mb, src_offset, dest_offset)
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT * timeout_cnt,
                 error_message='Timeout on copying file to dev'):
        subprocess.check_call(cmd)


def write_volume_dev_random_mb_data(path, offset_in_mb, length_in_mb,
                                    timeout_cnt=3):
    write_cmd = [
        '/bin/sh',
        '-c',
        'dd if=/dev/urandom of=%s bs=1M seek=%d count=%d' %
        (path, offset_in_mb, length_in_mb)
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT * timeout_cnt,
                 error_message='Timeout on writing dev'):
        subprocess.check_call(write_cmd)


def get_volume_dev_mb_data_md5sum(path, offset_in_mb, length_in_mb):
    md5sum_command = [
        '/bin/sh', '-c',
        'dd if=%s bs=1M skip=%d count=%d | md5sum' %
        (path, offset_in_mb, length_in_mb)
    ]

    with timeout(seconds=STREAM_EXEC_TIMEOUT * 5,
                 error_message='Timeout on computing dev md5sum'):
        output = subprocess.check_output(
            md5sum_command).strip().decode('utf-8')
        return output.split(" ")[1]


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
    for i in range(POD_DELETION_TIMEOUT):
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
def set_node_tags(client, node, tags=[], retry=False):  # NOQA
    """
    Set the tags on a node without modifying its scheduling status.
    Retry if "too many retries error" happened.
    :param client: The Longhorn client to use in the request.
    :param node: The Node to update.
    :param tags: The tags to set on the node.
    :return: The updated Node.
    """
    if not retry:
        return client.update(node, allowScheduling=node.allowScheduling,
                             tags=tags)

    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node = client.update(node,
                                 allowScheduling=node.allowScheduling,
                                 tags=tags)
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break

    return node


def set_node_scheduling(client, node, allowScheduling, retry=False):
    if node.tags is None:
        node.tags = []

    if not retry:
        return client.update(node, allowScheduling=allowScheduling,
                             tags=node.tags)

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node = client.update(node, allowScheduling=allowScheduling,
                                 tags=node.tags)
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break

    return node

def set_node_scheduling_eviction(client, node, allowScheduling, evictionRequested, retry=False):  # NOQA
    if node.tags is None:
        node.tags = []

    if not retry:
        node = client.update(node,
                             allowScheduling=allowScheduling,
                             evictionRequested=evictionRequested)

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node = client.update(node,
                                 allowScheduling=allowScheduling,
                                 evictionRequested=evictionRequested)
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break

    return node


def set_node_cordon(api, node_name, to_cordon):
    """
    Set a kubernetes node schedulable status
    """
    payload = {
        "spec": {
            "unschedulable": to_cordon
        }
    }

    api.patch_node(node_name, payload)


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
                    'image': 'busybox:1.34.0',
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
                'image': 'busybox:1.34.0',
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
def batch_v1_api(request):
    """
    Create a new BatchV1Api instance.
    Returns:
        A new BatchV1Api Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.BatchV1Api()

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


def check_pvc_in_specific_status(api, pvc_name, status):
    for i in range(RETRY_EXEC_COUNTS):
        claim = \
            api.read_namespaced_persistent_volume_claim(name=pvc_name,
                                                        namespace='default')
        if claim.status.phase == status:
            break
        time.sleep(RETRY_INTERVAL)

    assert claim.status.phase == status


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
                        'image': 'busybox:1.34.0',
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
def rwx_statefulset(request):
    statefulset_manifest = {
        'apiVersion': 'apps/v1',
        'kind': 'StatefulSet',
        'metadata': {
            'name': 'rwx-test-statefulset',
            'namespace': 'default',
        },
        'spec': {
            'selector': {
                'matchLabels': {
                    'app': 'rwx-test-statefulset'
                }
            },
            'serviceName': 'rwx-test-statefulset',
            'replicas': 1,
            'template': {
                'metadata': {
                    'labels': {
                        'app': 'rwx-test-statefulset'
                    }
                },
                'spec': {
                    'terminationGracePeriodSeconds': 10,
                    'containers': [{
                        'image': 'busybox:1.34.0',
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
                        'ReadWriteMany'
                    ],
                    'storageClassName': 'longhorn',
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
def crypto_secret(request):
    core_api = get_core_api_client()

    def get_crypto_secret(namespace=LONGHORN_NAMESPACE):
        crypto_secret.manifest = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': 'longhorn-crypto',
                'namespace': namespace,
            },
            'stringData': {
                'CRYPTO_KEY_VALUE': 'simple',
                'CRYPTO_KEY_PROVIDER': 'secret'
            }
        }

        if is_k8s_node_gke_cos(core_api):
            # GKE COS's cryptsetup does not natively support "argon2i" and
            # "argon2id".
            # https://github.com/longhorn/longhorn/issues/10049
            crypto_secret.manifest['stringData']['CRYPTO_PBKDF'] = 'pbkdf2'

        return crypto_secret.manifest

    def finalizer():
        try:
            core_api.delete_namespaced_secret(
                name=crypto_secret.manifest['metadata']['name'],
                namespace=crypto_secret.manifest['metadata']['namespace'])
        except ApiException as e:
            assert e.status == 404

    request.addfinalizer(finalizer)

    return get_crypto_secret


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
        if DATA_ENGINE == "v2":
            # if the v2 data engine is enabled, both a file system disk
            # and a block disk will coexist. This is because a v2 backing image
            # requires a file system disk to function.
            assert len(node.disks) == 2
        else:
            assert len(node.disks) == 1

        update_disks = get_update_disks(node.disks)
        update_disks[list(update_disks)[0]].tags = tags["disk"]
        new_node = update_node_disks(client, node.name, disks=update_disks,
                                     retry=True)
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
        new_node = update_node_disks(client, node.name, disks=update_disks,
                                     retry=True)
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

    api_client = None

    # check if longhorn manager port is open before calling get_client
    for ip in ips:
        family = socket.AF_INET6 if ':' in ip else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)

        try:
            if sock.connect_ex((ip, 9500)) == 0:
                api_client = get_client(ip + PORT)
                break
        finally:
            sock.close()

    if api_client is None:
        raise RuntimeError(
            "Failed to connect to any Longhorn manager on ports 9500")

    hosts = api_client.list_node()
    assert len(hosts) == len(ips)

    request.addfinalizer(lambda: cleanup_client())

    if not os.path.exists(DIRECTORY_PATH):
        try:
            os.makedirs(DIRECTORY_PATH)
        except OSError as e:
            raise Exception(
                f"Failed to create directory {DIRECTORY_PATH}: {e}"
            )

    cleanup_client()

    return api_client


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
    core_api = k8sclient.CoreV1Api()
    client = get_longhorn_api_client()

    enable_default_disk(client)

    cleanup_all_volumes(client)

    # cleanup test disks
    cleanup_test_disks(client)

    if recurring_job_feature_supported(client):
        cleanup_all_recurring_jobs(client)

    if backing_image_feature_supported(client):
        cleanup_all_backing_images(client)

    cleanup_crypto_secret()
    cleanup_storage_class()
    if system_backup_feature_supported(client):
        system_restores_cleanup(client)

    cleanup_all_support_bundles(client)

    # enable nodes scheduling
    reset_node(client, core_api)
    reset_settings(client)
    reset_disks_for_all_nodes(client)
    scale_up_engine_image_daemonset(client)
    reset_engine_image(client)
    wait_for_all_instance_manager_running(client)

    enable_v2 = os.environ.get('RUN_V2_TEST')
    if enable_v2 == "true":
        return

    # check replica subdirectory of default disk path
    if not os.path.exists(DEFAULT_REPLICA_DIRECTORY):
        subprocess.check_call(
            ["mkdir", "-p", DEFAULT_REPLICA_DIRECTORY])


def reset_nodes_taint(client):
    core_api = get_core_api_client()
    nodes = client.list_node()

    for node in nodes:
        core_api.patch_node(node.id, {
            "spec": {"taints": []}
        })


def cleanup_disks_on_node(client, node_id, *disks):  # NOQA
    # Disable scheduling for the new disks on self node
    node = client.by_id_node(node_id)
    for name, disk in node.disks.items():
        if disk.path != DEFAULT_DISK_PATH:
            disk.allowScheduling = False

    # Update disks of self node
    update_disks = get_update_disks(node.disks)
    update_node_disks(client, node.name, disks=update_disks, retry=True)
    node = wait_for_disk_update(client, node_id, len(update_disks))

    # Remove new disks on self node and enable scheduling for the default disk
    default_disks = {}
    for name, disk in iter(node.disks.items()):
        if disk.path == DEFAULT_DISK_PATH:
            disk.allowScheduling = True
            default_disks[name] = disk

    # Update disks of self node
    update_disks = get_update_disks(node.disks)
    update_node_disks(client, node.name, disks=default_disks, retry=True)
    wait_for_disk_update(client, node_id, len(default_disks))

    # Cleanup host disks
    for disk in disks:
        cleanup_host_disks(client, disk)


def get_client(address_with_port):
    # Split IP and port
    if address_with_port.count(':') > 1:
        ip_part, port = address_with_port.rsplit(':', 1)
        ip = ipaddress.ip_address(ip_part)
        if ip.version == 6:
            formatted_address = f"[{ip_part}]:{port}"
        else:
            formatted_address = f"{ip_part}:{port}"
    else:
        formatted_address = address_with_port

    url = f'http://{formatted_address}/v1/schemas'
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
    return os.environ.get("NODE_NAME")


def get_backupstore_url():
    backupstore = os.environ.get("LONGHORN_BACKUPSTORES", "")
    backupstore = backupstore.replace(" ", "")
    backupstores = backupstore.split(",")

    assert len(backupstores) != 0
    return backupstores


def get_backupstore_poll_interval():
    poll_interval = os.environ.get("LONGHORN_BACKUPSTORE_POLL_INTERVAL", "")
    assert len(poll_interval) != 0
    return poll_interval


def get_backupstores():
    backupstore = os.environ.get("LONGHORN_BACKUPSTORES", "")

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
        if v.conditions.Scheduled.status == "False" and \
                v.conditions.Scheduled.reason == \
                "ReplicaSchedulingFailure":
            scheduling_failure = True
        if scheduling_failure:
            break
        time.sleep(RETRY_INTERVAL)
    assert scheduling_failure, f" Scheduled Status = " \
        f"{v.conditions.Scheduled.status}, Scheduled reason = " \
        f"{v.conditions.Scheduled.reason}, volume = {v}"


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


def wait_for_volume_healthy(client, name, retry_count=RETRY_COUNTS):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED, retry_count)
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_ROBUSTNESS,
                           VOLUME_ROBUSTNESS_HEALTHY, retry_count)
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
    # Comment out detach status check because status transition
    # were too fast recently
    # wait_for_volume_status(client, name,
    #                       VOLUME_FIELD_STATE,
    #                       VOLUME_STATE_DETACHED)
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_ROBUSTNESS,
                                  VOLUME_ROBUSTNESS_FAULTED)


def wait_for_volume_status(client, name, key, value,
                           retry_count=RETRY_COUNTS_LONG):
    wait_for_volume_creation(client, name)
    for i in range(retry_count):
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


def wait_for_backup_backing_image_delete(client, name):
    for _ in range(RETRY_COUNTS):
        bbis = client.list_backupBackingImage()
        found = False
        for bbi in bbis:
            if bbi.name == name:
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


def is_replica_available(r):
    return r is not None and r.running and not \
        r.failedAt and r.mode == 'RW'


def wait_for_volume_frontend_disabled(client, volume_name, state=True):
    for _ in range(RETRY_COUNTS):
        vol = client.by_id_volume(volume_name)
        try:
            assert vol.disableFrontend is state
            break
        except AssertionError:
            time.sleep(RETRY_INTERVAL)


def wait_for_volume_option_trim_auto_removing_snapshots(client, volume_name, enabled):  # NOQA
    for i in range(RETRY_COUNTS_SHORT):
        volume = client.by_id_volume(volume_name)
        if volume.controllers[0].unmapMarkSnapChainRemovedEnabled == enabled:
            break
        time.sleep(RETRY_INTERVAL)
    assert volume.controllers[0].unmapMarkSnapChainRemovedEnabled == enabled
    return volume


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
    # should be removed or "marked as removed" in the case of
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
        time.sleep(RETRY_INTERVAL_SHORT)
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


def wait_for_engine_image_incompatible(client, image_name):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image.incompatible:
            break
        time.sleep(RETRY_INTERVAL)
    assert image.incompatible
    return image


def wait_for_engine_image_condition(client, image_name, state):
    """
    state: "True", "False"
    """
    # Indicate many times we want to see the ENGINE_NAME in the STATE.
    # This helps to prevent the flaky test case in which the ENGINE_NAME
    # is flapping between ready and not ready a few times before settling
    # down to the ready state
    # https://github.com/longhorn/longhorn/issues/7438
    state_count = 1
    if state == "True":
        state_count = 60

    c = 0
    for i in range(RETRY_COUNTS):
        wait_for_engine_image_creation(client, image_name)
        image = client.by_id_engine_image(image_name)
        if image['conditions'][0]['status'] == state:
            c += 1
            if c >= state_count:
                break
        time.sleep(RETRY_INTERVAL_SHORT)
    assert image['conditions'][0]['status'] == state
    return image


def wait_for_engine_image_ref_count(client, image_name, count):
    wait_for_engine_image_creation(client, image_name)
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image.refCount == count:
            break
        time.sleep(RETRY_INTERVAL)
    assert image.refCount == count, f"image = {image}"
    if count == 0:
        assert image.noRefSince != ""
    return image


def json_string_go_to_python(str):
    return str.replace("u\'", "\"").replace("\'", "\""). \
        replace("True", "true").replace("False", "false")


def delete_replica_on_test_node(client, volume_name): # NOQA

    lht_host_id = get_self_host_id()

    volume = client.by_id_volume(volume_name)
    for replica in volume.replicas:
        if replica.hostId == lht_host_id:
            replica_name = replica.name
    volume.replicaRemove(name=replica_name)
    wait_for_volume_degraded(client, volume_name)


def delete_replica_processes(client, api, volname):
    replica_map = {}
    volume = client.by_id_volume(volname)
    for r in volume.replicas:
        replica_map[r.instanceManagerName] = r.name

    for rm_name, r_name in replica_map.items():
        delete_command = 'longhorn-instance-manager process delete ' + \
                         '--name ' + r_name
        exec_instance_manager(api, rm_name, delete_command)


class AssertErrorCheckThread(threading.Thread):
    """
        This class is used for catching exception caused in threads,
        especially for AssertionError now.

        Parameters:
            target  :       The threading function.
            args    :       Arguments of the target function.
    """
    def __init__(self, target, args):
        threading.Thread.__init__(self)
        self.target = target
        self.args = args
        self.asserted = None

    def run(self):
        try:
            self.target(*self.args)
        except AssertionError as e:
            self.asserted = e

    def join(self):
        threading.Thread.join(self)
        if self.asserted:
            raise self.asserted


def create_assert_error_check_thread(func, *args):
    """
        Do func by threading with arguments

        Parameters:
            func:   function that want to do things in parallel.
            args:   arguments for function.
    """
    assert isinstance(func, types.FunctionType), "First arg is not a function."

    t = AssertErrorCheckThread(target=func, args=args)
    t.start()

    return t


def assert_from_assert_error_check_threads(thrd_list):
    """
        Check all threads in thrd_list are done and their status

        Parameters:
            thrd_list: thread list created by create_assert_error_check_thread.
    """
    assert isinstance(thrd_list, list), "thrd_list is not a list"

    err_list = []
    for t in thrd_list:
        try:
            t.join()
        except AssertionError as e:
            print(e)
            err_list.append(e)
    if err_list:
        assert False, err_list


def crash_replica_processes(client, api, volname, replicas=None,
                            wait_to_fail=True):
    threads = []

    if replicas is None:
        volume = client.by_id_volume(volname)
        replicas = volume.replicas

    for r in replicas:
        assert r.instanceManagerName != ""

        pgrep_command = f"pgrep -f {r['dataPath']}"
        pid = exec_instance_manager(api, r.instanceManagerName, pgrep_command)
        assert pid != ""

        kill_command = f"kill {pid}"
        exec_instance_manager(api, r.instanceManagerName, kill_command)

        if wait_to_fail is True:
            thread = create_assert_error_check_thread(
                wait_for_replica_failed,
                client, volname, r['name'], RETRY_COUNTS, RETRY_INTERVAL_SHORT
            )
            threads.append(thread)

    if wait_to_fail:
        assert_from_assert_error_check_threads(threads)


def exec_instance_manager(api, im_name, cmd):
    exec_cmd = ['/bin/sh', '-c', cmd]

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        output = stream(api.connect_get_namespaced_pod_exec,
                        im_name,
                        LONGHORN_NAMESPACE, command=exec_cmd,
                        stderr=True, stdin=False, stdout=True, tty=False)
        return output


def wait_for_replica_failed(client, volname, replica_name,
                            retry_cnts=RETRY_COUNTS, retry_ivl=RETRY_INTERVAL):
    failed = True
    debug_replica_not_failed = None
    debug_replica_in_im = None

    for i in range(retry_cnts):
        failed = True
        debug_replica_not_failed = None
        debug_replica_in_im = None
        volume = client.by_id_volume(volname)
        for r in volume.replicas:
            if r['name'] != replica_name:
                continue
            if r['running'] or r['failedAt'] == "":
                failed = False
                debug_replica_not_failed = r
                break
            if r['instanceManagerName'] != "":
                im = client.by_id_instance_manager(r['instanceManagerName'])

                instance_dict = {}
                # We still check the 'instances' for backward compatibility
                # with older versions (<v1.5.x).
                if im['instances'] is not None:
                    instance_dict.update(im['instances'])
                if im['instanceReplicas'] is not None:
                    instance_dict.update(im['instanceReplicas'])

                if r['name'] in instance_dict:
                    failed = False
                    debug_replica_in_im = im
                    break
        if failed:
            break
        time.sleep(retry_ivl)

    err_msg = "Vol({}), Replica({}): {}, Instance_Manager: {}".format(
        volname, replica_name, debug_replica_not_failed, debug_replica_in_im
    )
    assert failed, err_msg


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

                instance_dict = {}
                # We still check the 'instances' for backward compatibility
                # with older versions (<v1.5.x).
                if im['instances'] is not None:
                    instance_dict.update(im['instances'])
                if im['instanceReplicas'] is not None:
                    instance_dict.update(im['instanceReplicas'])

                if r['name'] in instance_dict:
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
        unexpect_fail = max(0, expect_fail)

        expect_nodes = set(to_nodes)
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
                if expect_fail >= 0:
                    unexpect_fail -= 1

        if scheduled == expect_success and unexpect_fail == 0:
            break

        time.sleep(RETRY_INTERVAL)

    assert scheduled == expect_success, f" Volume = {volume}"
    assert unexpect_fail == 0, f"Got {unexpect_fail} unexpected fail"

    if expect_fail >= 0:
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


def generate_attachment_ticket_id():
    return ATTACHMENT_TICKET_ID_PREFIX + "-" + \
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
    parsed = urlparse(iscsi)
    return parsed.hostname


def get_iscsi_port(iscsi):
    parsed = urlparse(iscsi)
    return parsed.port


def get_iscsi_target(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    return iscsi_endpoint[1]


def get_iscsi_lun(iscsi):
    iscsi_endpoint = parse_iscsi_endpoint(iscsi)
    return iscsi_endpoint[2]


def exec_nsenter(cmd, process_name=None):
    if process_name:
        proc_pid = find_process_pid(process_name)
        cmd_parts = cmd.split()
    else:
        proc_pid = find_dockerd_pid() or "1"
        cmd_parts = ["bash", "-c", cmd]

    exec_cmd = ["nsenter", "--mount=/host/proc/{}/ns/mnt".format(proc_pid),
                "--net=/host/proc/{}/ns/net".format(proc_pid)]
    exec_cmd.extend(cmd_parts)
    return subprocess.check_output(exec_cmd)


def exec_local(cmd):
    exec_cmd = cmd.split()
    return subprocess.check_output(exec_cmd)


def parse_nvmf_endpoint(nvmf):
    return nvmf[7:].split('/')


def get_nvmf_ip(nvmf):
    nvmf_endpoint = parse_nvmf_endpoint(nvmf)
    return nvmf_endpoint[0].split(':')[0]


def get_nvmf_port(nvmf):
    nvmf_endpoint = parse_nvmf_endpoint(nvmf)
    return nvmf_endpoint[0].split(':')[1]


def get_nvmf_nqn(nvmf):
    nvmf_endpoint = parse_nvmf_endpoint(nvmf)
    return nvmf_endpoint[1]


def nvmf_login(nvmf):
    # Related commands are documented at:
    # https://github.com/longhorn/longhorn-tests/wiki/Connect-to-the-NVMf-frontend-volume # NOQA
    ip = get_nvmf_ip(nvmf)
    port = get_nvmf_port(nvmf)
    # NVMe Qualified Name
    nqn = get_nvmf_nqn(nvmf)

    cmd_connect = f"nvme connect -t tcp -a {ip} -s {port} -n {nqn}"
    subprocess.check_output(cmd_connect.split())
    return wait_for_nvme_device()


def nvmf_logout(nvmf):
    nqn = get_nvmf_nqn(nvmf)
    try:
        subprocess.check_call(["nvme", "disconnect", "-n", nqn])
        print(f"Disconnected from {nqn}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to disconnect from {nqn}: {e}")


def wait_for_nvme_device():
    for _ in range(RETRY_COUNTS):
        try:
            output = subprocess.check_output(["nvme", "list"], text=True)
            print(f"nvme list output =\n {output}")
            for line in output.splitlines():
                if line.startswith("/dev/nvme"):
                    dev_path = line.split()[0]
                    return dev_path
        except subprocess.CalledProcessError as e:
            print(f"nvme list failed: {e.output}")
        time.sleep(RETRY_INTERVAL)

    raise Exception("NVMe device not found after retries")


def iscsi_login(iscsi_ep):
    ip = get_iscsi_ip(iscsi_ep)
    port = get_iscsi_port(iscsi_ep)
    target = get_iscsi_target(iscsi_ep)
    lun = get_iscsi_lun(iscsi_ep)
    # discovery
    cmd_discovery = "iscsiadm -m discovery -t st -p " + ip
    exec_nsenter(cmd_discovery, ISCSI_PROCESS)
    # login
    cmd_login = "iscsiadm -m node -T " + target + " -p " + ip + " --login"
    exec_nsenter(cmd_login, ISCSI_PROCESS)
    blk_name = "ip-%s:%s-iscsi-%s-lun-%s" % (ip, port, target, lun)
    wait_for_device_login(ISCSI_DEV_PATH, blk_name)
    dev = os.path.realpath(ISCSI_DEV_PATH + "/" + blk_name)
    return dev


def iscsi_logout(iscsi_ep):
    ip = get_iscsi_ip(iscsi_ep)
    target = get_iscsi_target(iscsi_ep)
    cmd_logout = "iscsiadm -m node -T " + target + " -p " + ip + " --logout"
    exec_nsenter(cmd_logout, ISCSI_PROCESS)
    cmd_rm_discovery = "iscsiadm -m discovery -p " + ip + " -o delete"
    exec_nsenter(cmd_rm_discovery, ISCSI_PROCESS)


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


def find_process_pid(process_name):
    for file in os.listdir(HOST_PROC_DIR):
        if not os.path.isdir(os.path.join(HOST_PROC_DIR, file)):
            continue

        # Check if file name is an integer
        if not file.isdigit():
            continue

        with open(os.path.join(HOST_PROC_DIR, file, 'status'), 'r') as file:
            status_content = file.readlines()

        proc_status_content = None
        name_pattern = re.compile(r'^Name:\s+(.+)$')

        for line in status_content:
            name_match = name_pattern.match(line)
            if name_match and name_match.group(1) == process_name:
                proc_status_content = status_content
                break

        if proc_status_content is None:
            continue

        pid_pattern = re.compile(r'^Pid:\s+(\d+)$')

        for line in proc_status_content:
            pid_match = pid_pattern.match(line)
            if pid_match:
                return int(pid_match.group(1))

    raise Exception(f"Failed to find the {process_name} PID")


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


def wait_for_volume_condition_toomanysnapshots(client, name, key, value,
                                               expected_message=None):
    wait_for_volume_creation(client, name)
    for _ in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        conditions = volume.conditions
        if conditions is not None and \
                conditions != {} and \
                VOLUME_CONDITION_TOOMANYSNAPSHOTS in conditions and \
                conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] and \
                conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] == value:
            if expected_message is not None:
                current_message = \
                    conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS]['message']
                if current_message == expected_message:
                    break
            else:
                break
        time.sleep(RETRY_INTERVAL)
    conditions = volume.conditions
    assert conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS][key] == value
    if expected_message is not None:
        current_message = \
            conditions[VOLUME_CONDITION_TOOMANYSNAPSHOTS]['message']
        assert current_message == expected_message, \
            f"Expected message = {expected_message},\n" \
            f"but get '{current_message}'\n"
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
    assert disks[disk_name][key] == value, \
        f"Wrong disk({disk_name}) {key} status.\n" \
        f"Expect={value}\n" \
        f"Got={disks[disk_name][key]}\n" \
        f"node={client.by_id_node(node_name)}\n" \
        f"volumes={client.list_volume()}\n"
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

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node.diskUpdate(disks=update_disks)
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break

    for name, disk in iter(disks.items()):
        wait_for_disk_status(client, node_name,
                             name, "allowScheduling", False)

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node.diskUpdate(disks={})
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break

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
        if v.frontend == VOLUME_FRONTEND_BLOCKDEV or \
           v.frontend == VOLUME_FRONTEND_UBLK:
            assert endpoint == os.path.join(DEV_PATH, v.name)
        elif v.frontend == VOLUME_FRONTEND_ISCSI:
            assert endpoint.startswith("iscsi://")
        elif v.frontend == VOLUME_FRONTEND_NVMF:
            assert endpoint.startswith("nvmf://")
        else:
            raise Exception("Unexpected volume frontend:", v.frontend)
    return endpoint


def find_backup_volume(client, volume_name, retry=1):
    for _ in range(retry):
        bvs = client.list_backupVolume()
        for bv in bvs:
            volumeName = getattr(bv, 'volumeName', bv.name)
            if volumeName == volume_name and bv.created != "":
                return bv
        time.sleep(RETRY_BACKUP_INTERVAL)
    return None


def wait_for_backup_volume_backing_image_synced(
        client, volume_name, backing_image, retry_count=RETRY_BACKUP_COUNTS):

    completed = False
    for _ in range(retry_count):
        bv = find_backup_volume(client, volume_name)
        if bv is not None:
            if bv.backingImageName == backing_image:
                completed = True
                break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert completed is True, f" Backup Volume = {bv}," \
                              f" Backing Image = {backing_image}," \
                              f" Volume = {volume_name}"
    return bv


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


def wait_for_backup_failed(client, volume_name, snapshot_name=None,
                           retry_count=RETRY_BACKUP_COUNTS):
    failed = False
    for _ in range(retry_count):
        v = client.by_id_volume(volume_name)
        for b in v.backupStatus:
            if b.state == "Error":
                assert b.progress == 0
                assert b.error != ""
                failed = True
                break
        if failed:
            break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert failed is True
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
    for i in range(RETRY_COUNTS_LONG):
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


def wait_for_volume_migration_node(client, volume_name, node_id,
                                   expected_replica_count=-1):
    ready = False
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(volume_name)

        if expected_replica_count == -1:
            expected_replica_count = v.numberOfReplicas
        assert expected_replica_count >= 0

        engines = v.controllers
        replicas = v.replicas
        if len(engines) == 1 and len(replicas) == expected_replica_count:
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


def reset_node(client, core_api):
    # remove nodes taint
    reset_nodes_taint(client)

    nodes = client.list_node()
    for node in nodes:
        try:
            set_node_cordon(core_api, node.id, False)
            node = client.by_id_node(node.id)

            node = set_node_tags(client, node, tags=[])
            node = wait_for_node_tag_update(client, node.id, [])
            node = set_node_scheduling(client, node, allowScheduling=True)
            wait_for_node_update(client, node.id,
                                 "allowScheduling", True)
        except Exception as e:
            print("\nException when reset node scheduling and tags", node)
            print(e)

    managed_k8s_cluster = os.getenv("MANAGED_K8S_CLUSTER").lower() == 'true'
    if not managed_k8s_cluster:
        reset_longhorn_node_zone(client)


def reset_longhorn_node_zone(client):
    core_api = get_core_api_client()

    # No need to reset zone label for GKE COS node as the node zone label is
    # periodically updated with the actual GCP zone.
    # https://github.com/longhorn/longhorn-tests/pull/1819
    if is_k8s_node_gke_cos(core_api):
        return

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


def set_k8s_node_label(core_api, node_name, key, value):
    payload = {
        "metadata": {
            "labels": {
                key: value}
        }
    }

    core_api.patch_node(node_name, body=payload)


def is_k8s_node_label(core_api, label_key, label_value, node_name):
    node = core_api.read_node(node_name)

    if label_key in node.metadata.labels:
        if node.metadata.labels[label_key] == label_value:
            return True
    return False


def set_k8s_node_zone_label(core_api, node_name, zone_name):
    if is_k8s_node_label(core_api, K8S_ZONE_LABEL, zone_name, node_name):
        return

    k8s_zone_label = get_k8s_zone_label()

    set_k8s_node_label(core_api, node_name, k8s_zone_label, zone_name)


def set_and_wait_k8s_nodes_zone_label(core_api, node_zone_map):
    k8s_zone_label = get_k8s_zone_label()

    for _ in range(RETRY_COUNTS):
        for node_name, zone_name in node_zone_map.items():
            set_k8s_node_label(core_api, node_name, k8s_zone_label, zone_name)

        is_updated = False
        for node_name, zone_name in node_zone_map.items():
            is_updated = \
                is_k8s_node_label(core_api,
                                  k8s_zone_label, zone_name, node_name)
            if not is_updated:
                break

        if is_updated:
            break

        time.sleep(RETRY_INTERVAL)

    assert is_updated, \
        f"Timeout while waiting for nodes zone label to be updated\n" \
        f"Expected: {node_zone_map}"


def is_k8s_node_gke_cos(core_api):
    return is_k8s_node_label(core_api,
                             K8S_GKE_OS_DISTRO_LABEL,
                             K8S_GKE_OS_DISTRO_COS,
                             get_self_host_id())


def get_k8s_zone_label():
    ver_api = get_version_api_client()
    k8s_ver_data = ver_api.get_code()

    k8s_ver_major = k8s_ver_data.major
    assert k8s_ver_major == '1'

    k8s_ver_minor = k8s_ver_data.minor

    # k8s_ver_minor no needs to be an int
    # it could be "24+" in eks
    if int(re.sub('\\D', '', k8s_ver_minor)) >= 17:
        k8s_zone_label = K8S_ZONE_LABEL
    else:
        k8s_zone_label = DEPRECATED_K8S_ZONE_LABEL

    return k8s_zone_label


def cleanup_test_disks(client):
    try:
        del_dirs = os.listdir(DIRECTORY_PATH)
    except FileNotFoundError:
        del_dirs = []

    host_id = get_self_host_id()
    node = client.by_id_node(host_id)
    disks = node.disks
    for name, disk in iter(disks.items()):
        for del_dir in del_dirs:
            dir_path = os.path.join(DIRECTORY_PATH, del_dir)
            if dir_path == disk.path:
                disk.allowScheduling = False
    update_disks = get_update_disks(disks)

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
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
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print("\nException when update node disks", node)
            print(e)
            raise
        else:
            break

    # delete test disks
    disks = node.disks
    update_disks = {}
    for name, disk in iter(disks.items()):
        if disk.allowScheduling:
            update_disks[name] = disk
    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node.diskUpdate(disks=update_disks)
            wait_for_disk_update(client, host_id, len(update_disks))
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print("\nException when delete node test disks", node)
            print(e)
            raise
        else:
            break
    # cleanup host disks
    for del_dir in del_dirs:
        try:
            cleanup_host_disk(del_dir)
        except Exception as e:
            print("\nException when cleanup host disk", del_dir)
            print(e)
            pass


def reset_disks_for_all_nodes(client, add_block_disks=False):  # NOQA
    default_disks = {
        "v1": {
            "path": DEFAULT_DISK_PATH,
            "type": "filesystem",
            "default": True,
        }
    }

    if v2_data_engine_cr_supported(client):
        enable_v2 = os.environ.get('RUN_V2_TEST')
        if enable_v2 == "true" or add_block_disks is True:
            default_disks["v2"] = {
                "path": BLOCK_DEV_PATH,
                "type": "block",
                "default": True,
            }
            default_disks["v1"]["default"] = False

    nodes = client.list_node()
    for n in nodes:
        node = n  # Captures the correct value of n in the closure.

        # Reset default disk if default disks are not the only disks
        # on the node.
        cleanup_required = False
        if len(node.disks) != len(default_disks):
            cleanup_required = True

        for name, disk in iter(node.disks.items()):
            if cleanup_required:
                break

            if disk.path not in [v["path"] for v in default_disks.values()]:
                cleanup_required = True
                break

            if name == "default-disk":
                for data_engine, disk in default_disks.items():
                    if not disk["default"]:
                        continue

                    if disk["path"] != node.disks[name].path:
                        cleanup_required = True
                    break

        if cleanup_required:
            update_disks = get_update_disks(node.disks)
            for disk_name, disk in iter(update_disks.items()):
                disk.allowScheduling = False
                update_disks[disk_name] = disk
                node = update_node_disks(client, node.name, disks=update_disks,
                                         retry=True)
            update_disks = {}
            node = update_node_disks(client, node.name, disks=update_disks,
                                     retry=True)
            node = wait_for_disk_update(client, node.name, 0)

        if len(node.disks) != len(default_disks):
            update_disks = {}
            for data_engine, disk in default_disks.items():
                disk_name = data_engine
                if disk["default"]:
                    disk_name = "default-disk"

                update_disks[disk_name] = {
                    "path": disk["path"],
                    "diskType": disk["type"],
                    "allowScheduling": True
                }

            node = update_node_disks(client, node.name, disks=update_disks,
                                     retry=True)
            node = wait_for_disk_update(client, node.name, len(default_disks))
            assert len(node.disks) == len(default_disks)
        # wait for node controller to update disk status
        disks = node.disks
        update_disks = {}
        for name, disk in iter(disks.items()):
            update_disk = disk
            update_disk.allowScheduling = True
            if disk.diskType == "filesystem":
                reserved_storage = int(update_disk.storageMaximum * 30 / 100)
            else:
                reserved_storage = 0
            update_disk.storageReserved = reserved_storage
            update_disk.tags = []
            update_disks[name] = update_disk
        node = update_node_disks(client, node.name, disks=update_disks,
                                 retry=True)
        for name, disk in iter(node.disks.items()):
            # wait for node controller update disk status
            wait_for_disk_status(client, node.name, name,
                                 "allowScheduling", True)
            wait_for_disk_status(client, node.name, name,
                                 "storageScheduled", 0)

            expected_reserved_storage = 0
            if disk.diskType == "filesystem":
                expected_reserved_storage = reserved_storage
            wait_for_disk_status(client, node.name, name,
                                 "storageReserved",
                                 expected_reserved_storage)


def reset_settings(client):

    for setting in client.list_setting():
        setting_name = setting.name
        setting_default_value = setting.definition.default
        setting_readonly = setting.definition.readOnly

        # We don't provide the setup for the storage network, hence there is no
        # default value. We need to skip here to avoid test failure when
        # resetting this to an empty default value.
        if setting_name == "storage-network":
            continue
        # The test CI deploys Longhorn with the setting value longhorn-critical
        # for the setting priority-class. Don't reset it to empty (which is
        # the default value defined in longhorn-manager code) because this will
        # restart Longhorn managed components and fail the test cases.
        # https://github.com/longhorn/longhorn/issues/7413#issuecomment-1881707958
        if setting.name == SETTING_PRIORITY_CLASS:
            continue

        # The version of the support bundle kit will be specified by a command
        # option when starting the manager. And setting requires a value.
        #
        # Longhorn has a default version for each release provided to the
        # manager when starting. Meaning this setting doesn't have a default
        # value.
        #
        # The design grants the ability to update later by cases for
        # troubleshooting purposes. Meaning this setting is editable.
        #
        # So we need to skip here to avoid test failure when resetting this to
        # an empty default value.
        if setting_name == "support-bundle-manager-image":
            continue

        if setting_name == "registry-secret":
            continue

        if setting_name == "v2-data-engine":
            if v2_data_engine_cr_supported(client):
                setting = client.by_id_setting(SETTING_V2_DATA_ENGINE)
                try:
                    client.update(setting, value="true")
                except Exception as e:
                    print(f"\nException setting {setting_name} to true")
                    print(e)
                continue

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


# ensure that the engine image daemonset scale up for longhorn
# after scaling down daemonset
def scale_up_engine_image_daemonset(client):
    apps_api = get_apps_api_client()
    default_img = get_default_engine_image(client)
    ds_name = "engine-image-" + default_img.name
    body = [{
        "op": "replace",
        "path": "/spec/template/spec/nodeSelector",
        "value": None
    }]
    try:
        apps_api.patch_namespaced_daemon_set(
            name=ds_name, namespace='longhorn-system', body=body)
    except ApiException as e:
        # for scaling up a running daemond set,
        # the status_code is 422 server error.
        assert e.status == 422

    # make sure default engine image deployed ready
    wait_for_deployed_engine_image_count(client, default_img.name, 3)


def wait_for_deployed_engine_image_count(client, image_name, expected_cnt,
                                         exclude_nodes=[]):
    for i in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)
        image = client.by_id_engine_image(image_name)
        deployed_cnt = 0
        if image.nodeDeploymentMap is None:
            continue
        for node_name in image.nodeDeploymentMap:
            if node_name in exclude_nodes:
                continue
            if image.nodeDeploymentMap[node_name] is True:
                deployed_cnt = deployed_cnt + 1
        if deployed_cnt == expected_cnt:
            break

    assert deployed_cnt == expected_cnt, f"image = {image}"


def wait_for_tainted_node_engine_image_undeployed(client,
                                                  img_name, tainted_node):
    for _ in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)
        tainted_node_excluded = False
        img = client.by_id_engine_image(img_name)
        if img.nodeDeploymentMap is None:
            continue
        for node_name in img.nodeDeploymentMap:
            if node_name != tainted_node:
                continue
            if img.nodeDeploymentMap[node_name] is False:
                tainted_node_excluded = True
                break
        if tainted_node_excluded:
            break
    assert img.nodeDeploymentMap[tainted_node] is False


def wait_for_running_engine_image_count(image_name, engine_cnt):
    core_api = get_core_api_client()
    for i in range(RETRY_COUNTS):
        exist_engine_cnt = 0
        longhorn_pod_list = core_api.list_namespaced_pod('longhorn-system')
        for pod in longhorn_pod_list.items:
            if "engine-image-" + image_name in pod.metadata.name and \
                    pod.status.phase == "Running":
                exist_engine_cnt += 1
        if exist_engine_cnt == engine_cnt:
            break
        time.sleep(RETRY_INTERVAL)

    assert exist_engine_cnt == engine_cnt


def restart_and_wait_ready_engine_count(client, ready_engine_count): # NOQA
    """
    Delete/restart engine daemonset and wait ready engine image count after
    daemonset restart
    """

    apps_api = get_apps_api_client()
    default_img = get_default_engine_image(client)
    ds_name = "engine-image-" + default_img.name
    apps_api.delete_namespaced_daemon_set(ds_name, LONGHORN_NAMESPACE)
    wait_for_engine_image_condition(client, default_img.name, "False")
    wait_for_engine_image_state(client, default_img.name, "deploying")
    wait_for_running_engine_image_count(default_img.name, ready_engine_count)


def wait_for_all_instance_manager_running(client):
    core_api = get_core_api_client()

    nodes = client.list_node()

    for _ in range(RETRY_COUNTS):
        instance_managers = client.list_instance_manager()
        node_to_instance_manager_map = {}
        try:
            for im in instance_managers:
                if im.managerType == "aio":
                    node_to_instance_manager_map[im.nodeID] = im
                else:
                    print("\nFound unknown instance manager:", im)
            if len(node_to_instance_manager_map) != len(nodes):
                time.sleep(RETRY_INTERVAL)
                continue

            for _, im in node_to_instance_manager_map.items():
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


def is_backupTarget_cifs(s):
    return s.startswith("cifs://")


def is_backupTarget_azurite(s):
    return s.startswith("azblob://")


def wait_for_backup_volume(client, bv_name, backing_image=""):
    for _ in range(RETRY_BACKUP_COUNTS):
        bv = client.by_id_backupVolume(bv_name)
        if bv is not None:
            if backing_image == "":
                break
            if bv.backingImageName == backing_image \
                    and bv.backingImageChecksum != "":
                break
        time.sleep(RETRY_BACKUP_INTERVAL)
    assert bv is not None, "failed to find backup volume " + bv_name


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

    bv = None
    for i in range(120):
        if bv is None:
            bv = find_backup_volume(client, vol_name)
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

    for i in range(RETRY_COUNTS):
        print(f"wait for Longhorn components ready ... ({i})")
        try:
            longhorn_pod_list = core_api.list_namespaced_pod('longhorn-system')
            for item in longhorn_pod_list.items:
                labels = item.metadata.labels

                if not labels:
                    pass
                elif labels.get('longhorn.io/component', '') == 'engine-image'\
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
                break
            else:
                for item in longhorn_pod_list.items:
                    print(f"{item.metadata.name}    {item.status.phase}")

        except ApiException as e:
            if (e.status == 404):
                ready = False

        time.sleep(RETRY_INTERVAL)

    assert ready, "Failed to wait for Longhorn components ready"


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


def create_crypto_secret(secret_manifest, namespace=LONGHORN_NAMESPACE):
    api = get_core_api_client()
    api.create_namespaced_secret(namespace,
                                 body=secret_manifest)


def delete_crypto_secret(namespace, name):
    api = get_core_api_client()
    try:
        api.delete_namespaced_secret(namespace=namespace, name=name)
    except ApiException as e:
        assert e.status == 404


def cleanup_crypto_secret():
    secret_deletes = ["longhorn-crypto"]
    api = get_core_api_client()
    ret = api.list_namespaced_secret(namespace=LONGHORN_NAMESPACE)
    for sc in ret.items:
        if sc.metadata.name in secret_deletes:
            delete_crypto_secret(name=sc.metadata.name,
                                 namespace=LONGHORN_NAMESPACE)

    ok = False
    for _ in range(RETRY_COUNTS):
        ok = True
        ret = api.list_namespaced_secret(namespace=LONGHORN_NAMESPACE)
        for s in ret.items:
            if s.metadata.name in secret_deletes:
                ok = False
                break
        if ok:
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def create_storage_class(sc_manifest, data_engine=DATA_ENGINE):
    api = get_storage_api_client()
    sc_manifest['parameters']['dataEngine'] = data_engine
    api.create_storage_class(
        body=sc_manifest)


def delete_storage_class(sc_name):
    api = get_storage_api_client()
    try:
        api.delete_storage_class(sc_name, body=k8sclient.V1DeleteOptions())
    except ApiException as e:
        assert e.status == 404


def cleanup_storage_class():
    # premium-rwo, standard-rwo and standard are installed in gke by default
    # azurefile-csi, azurefile-csi-premium, azurefile-premium, managed,
    # managed-csi, managed-csi-premium, managed-premium are installed
    # in aks by default
    skip_sc_deletes = ["longhorn", "local-path",
                       "premium-rwo", "standard-rwo", "standard",
                       "azurefile-csi", "azurefile-csi-premium",
                       "azurefile-premium", "managed", "managed-csi",
                       "managed-csi-premium", "managed-premium"]
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


def create_pvc_for_volume(client, core_api, volume, pvc_name, pvc_namespace="default"): # NOQA
    volume.pvcCreate(namespace=pvc_namespace, pvcName=pvc_name)
    for i in range(RETRY_COUNTS):
        if check_pvc_existence(core_api, pvc_name, pvc_namespace):
            break
        time.sleep(RETRY_INTERVAL)
    assert check_pvc_existence(core_api, pvc_name, pvc_namespace)

    ks = {
        'pvStatus': 'Bound',
        'namespace': pvc_namespace,
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
    snap = volume.snapshotCRCreate()
    snap_name = snap.name

    snapshot_created = False
    for i in range(RETRY_COUNTS):
        snapshots = volume.snapshotList(volume=volume_name)

        for vs in snapshots.data:
            if vs.name == snap_name:
                snapshot_created = True
                snap = vs
                break
        if snapshot_created is True:
            break
        time.sleep(RETRY_INTERVAL)

    assert snapshot_created
    return snap


def wait_for_snapshot_count(volume, number,
                            retry_counts=120,
                            count_removed=False):
    for _ in range(retry_counts):
        count = 0
        for snapshot in volume.snapshotList():
            if snapshot.removed is False or count_removed:
                count += 1

        if count == number:
            return
        time.sleep(RETRY_SNAPSHOT_INTERVAL)

    assert False, \
        f"failed to wait for snapshot.\n" \
        f"Expect count={number}\n" \
        f"Got count={count}"


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


def wait_for_volume_expansion(longhorn_api_client,
                              volume_name,
                              expected_size=""):
    complete = False
    for i in range(RETRY_COUNTS):
        volume = longhorn_api_client.by_id_volume(volume_name)
        engine = get_volume_engine(volume)
        if expected_size != "" and engine.size != expected_size:
            time.sleep(RETRY_INTERVAL)
            continue
        if engine.size == volume.size:
            complete = True
            break
        time.sleep(RETRY_INTERVAL)
    assert complete


def wait_for_expansion_error_clear(longhorn_api_client, volume_name):
    complete = False
    for i in range(RETRY_COUNTS):
        volume = longhorn_api_client.by_id_volume(volume_name)
        engine = get_volume_engine(volume)
        if engine.lastExpansionFailedAt == "" and \
                engine.lastExpansionError == "":
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
        time.sleep(RETRY_INTERVAL_LONG)
    assert complete


def expand_and_wait_for_pvc(api, pvc, size):
    pvc['spec']['resources'] = {
        'requests': {
            'storage': size_to_string(size)
        }
    }

    pvc_name = pvc['metadata']['name']
    api.patch_namespaced_persistent_volume_claim(
        pvc_name, 'default', pvc)
    complete = False
    for i in range(RETRY_COUNTS_LONG):
        claim = api.read_namespaced_persistent_volume_claim(
            name=pvc_name, namespace='default')
        if claim.spec.resources.requests['storage'] ==\
                claim.status.capacity['storage']:
            complete = True
            break
        time.sleep(RETRY_INTERVAL_LONG)
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
                "otherwise the field r.instanceManagerName is empty")
        stream(api.connect_get_namespaced_pod_exec,
               r.instanceManagerName,
               LONGHORN_NAMESPACE, command=cmd,
               stderr=True, stdin=False, stdout=True, tty=False)


def fix_replica_expansion_failure(client, api, volname, size, replicas=None):
    if replicas is None:
        volume = client.by_id_volume(volname)
        replicas = volume.replicas

    for r in replicas:
        if not r.instanceManagerName:
            raise Exception(
                "Should use replica objects in the running volume,"
                "otherwise the field r.instanceManagerName is empty")

        tmp_meta_file_name = \
            EXPANSION_SNAP_TMP_META_NAME_PATTERN % size
        tmp_meta_file_path = \
            INSTANCE_MANAGER_HOST_PATH_PREFIX + \
            r.dataPath + "/" + tmp_meta_file_name

        removed = False
        for i in range(RETRY_COMMAND_COUNT):
            # os.path.join() cannot deal with the path containing "/"
            cmd = [
                '/bin/sh', '-c',
                'rm -rf %s && sync' % tmp_meta_file_path
            ]
            stream(api.connect_get_namespaced_pod_exec,
                   r.instanceManagerName,
                   LONGHORN_NAMESPACE, command=cmd,
                   stderr=True, stdin=False, stdout=True, tty=False)
            cmd = ['/bin/sh', '-c', 'ls %s' % tmp_meta_file_path]
            output = stream(
                api.connect_get_namespaced_pod_exec,
                r.instanceManagerName, LONGHORN_NAMESPACE, command=cmd,
                stderr=True, stdin=False, stdout=True, tty=False)
            if "No such file or directory" in output:
                removed = True
                break
            time.sleep(RETRY_INTERVAL_LONG)
        assert removed


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


def wait_for_rebuild_complete(client, volume_name, retry_count=RETRY_COUNTS):
    completed = 0
    rebuild_statuses = {}
    for i in range(retry_count):
        completed = 0
        v = client.by_id_volume(volume_name)
        rebuild_statuses = v.rebuildStatus
        for status in rebuild_statuses:
            if status.state == "complete":
                assert status.progress == 100, f"status = {status}"
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


def wait_for_rebuild_start(client, volume_name,
                           retry_count=RETRY_COUNTS,
                           retry_interval=RETRY_INTERVAL):
    started = False
    for i in range(retry_count):
        v = client.by_id_volume(volume_name)
        rebuild_statuses = v.rebuildStatus
        for status in rebuild_statuses:
            if status.state == "in_progress":
                started = True
                break
        if started:
            break
        time.sleep(retry_interval)
    assert started
    return status.fromReplica, status.replica


def wait_for_restoration_start(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_RESTOREINITIATED,
                                  True)


def wait_for_volume_restoration_completed(client, name):
    wait_for_volume_creation(client, name)
    wait_for_restoration_start(client, name)
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
        time.sleep(RETRY_INTERVAL_SHORT)
    assert started
    return status.replica


@pytest.fixture
def make_deployment_with_pvc(request):
    def _generate_deployment_with_pvc_manifest(deployment_name, pvc_name, replicas=1): # NOQA
        if not hasattr(make_deployment_with_pvc, 'deployment_manifests'):
            make_deployment_with_pvc.deployment_manifests = []
        make_deployment_with_pvc.deployment_manifests.append({
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
        })

        return make_deployment_with_pvc.deployment_manifests[-1]

    def finalizer():
        apps_api = get_apps_api_client()
        if not hasattr(make_deployment_with_pvc, 'deployment_manifests'):
            return
        for deployment_manifest in \
                make_deployment_with_pvc.deployment_manifests:
            deployment_name = deployment_manifest["metadata"]["name"]
            delete_and_wait_deployment(
                apps_api,
                deployment_name
            )

    request.addfinalizer(finalizer)

    return _generate_deployment_with_pvc_manifest


@pytest.fixture
def make_deployment_cpu_request(request):
    def _generate_deployment_cpu_request_manifest(deployment_name, cpu_request, replicas=1): # NOQA
        make_deployment_cpu_request.deployment_manifest = {
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
                           "resources": {
                               "limits": {
                                   "cpu": str(cpu_request * 2)+"m",
                                   "memory": "30Mi",
                               },
                               "requests": {
                                   "cpu": str(cpu_request)+"m",
                                   "memory": "15Mi",
                               }
                           }
                        }
                     ],
                  }
               }
            }
        }

        return make_deployment_cpu_request.deployment_manifest

    def finalizer():
        apps_api = get_apps_api_client()
        deployment_name = \
            make_deployment_cpu_request.deployment_manifest["metadata"]["name"]
        delete_and_wait_deployment(
            apps_api,
            deployment_name
        )

    request.addfinalizer(finalizer)

    return _generate_deployment_cpu_request_manifest


def wait_deployment_replica_ready(apps_api, deployment_name,
                                  desired_replica_count, namespace='default'):  # NOQA
    ok = False
    for i in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        deployment = apps_api.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace)

        # deployment is none if deployment is not yet created
        if deployment is not None and \
           deployment.status.ready_replicas == desired_replica_count:
            ok = True
            break

        time.sleep(DEFAULT_DEPLOYMENT_INTERVAL)
    assert ok


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
    """
    Add mechanism to wait for a stable running pod when deployment restarts its
    workload, since Longhorn manager could create/delete the new workload pod
    multiple times, it's possible that we get an unstable pod which will be
    deleted immediately, so add a wait mechanism to get a stable running pod.
    ref: https://github.com/longhorn/longhorn/issues/4814
    """
    stable_pod = None
    wait_for_stable_retry = 0

    for _ in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        label_selector = "name=" + deployment_name
        pods = core_api.list_namespaced_pod(namespace="default",
                                            label_selector=label_selector)
        for pod in pods.items:
            if pod.status.phase == is_phase:
                if stable_pod is None or \
                        stable_pod.status.start_time != pod.status.start_time:
                    stable_pod = pod
                    wait_for_stable_retry = 0
                    break
                else:
                    wait_for_stable_retry += 1
                    if wait_for_stable_retry == WAIT_FOR_POD_STABLE_MAX_RETRY:
                        return stable_pod

        time.sleep(DEFAULT_DEPLOYMENT_INTERVAL)
    assert False


def wait_delete_deployment(apps_api, deployment_name, namespace='default'):
    for i in range(DEFAULT_DEPLOYMENT_TIMEOUT):
        ret = apps_api.list_namespaced_deployment(namespace=namespace)
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

    wait_delete_deployment(apps_api, deployment_name, namespace)


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


def offline_expand_attached_volume(client, volume_name, size=EXPAND_SIZE):
    volume = wait_for_volume_healthy(client, volume_name)
    engine = get_volume_engine(volume)

    volume.detach()
    volume = wait_for_volume_detached(client, volume.name)
    volume.expand(size=size)
    wait_for_volume_expansion(client, volume.name)
    volume = wait_for_volume_detached(client, volume.name)
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
        data_size_in_mb=DATA_SIZE_IN_MB_1, add_liveness_probe=True,
        access_mode=ACCESS_MODE_RWO, data_engine=DATA_ENGINE):# NOQA:

    pod_name = volume_name + "-pod"
    pv_name = volume_name
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
                            size=volume_size,
                            access_mode=access_mode,
                            data_engine=data_engine)
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
            "kill `pgrep -f \"controller " + volume_name + "\"`"]

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        stream(core_api.connect_get_namespaced_pod_exec,
               ins_mgr_name,
               LONGHORN_NAMESPACE, command=kill_command,
               stderr=True, stdin=False, stdout=True, tty=False)


def remount_volume_read_only(client, core_api, volume_name):
    volume_name_hash = hashlib.sha256(volume_name.encode()).hexdigest()

    volume = client.by_id_volume(volume_name)
    instance_manager_name = volume.controllers[0].instanceManagerName

    print(f"Remounting volume {volume_name} as read-only: {volume_name_hash}")

    command = [
            '/bin/sh', '-c',
            f"mount -o remount,ro /host/var/lib/kubelet/plugins/kubernetes.io/csi/driver.longhorn.io/{volume_name_hash}/globalmount"    # NOQA
    ]

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        stream(core_api.connect_get_namespaced_pod_exec,
               instance_manager_name, LONGHORN_NAMESPACE, command=command,
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
        try:
            pod = core_api.read_namespaced_pod(name=pod_name,
                                               namespace=namespace)
            if pod.status.phase == pod_phase:
                is_phase = True
                break
        except Exception as e:
            print(f"Waiting for pod {pod_name} {pod_phase} failed: {e}")

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
            if e.reason == EXCEPTION_ERROR_REASON_NOT_FOUND:
                time.sleep(RETRY_INTERVAL)
                continue
            # Report any other error
            else:
                assert (not e)
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

    def backup_exists():
        bv = find_backup_volume(client, volume_name)
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


def create_backing_image_with_matching_url(client, name, url,
                                           minNumberOfCopies=1,
                                           nodeSelector=[], diskSelector=[],
                                           dataEngine=DATA_ENGINE):
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
            if dataEngine == "v2":
                expected_checksum = BACKING_IMAGE_RAW_CHECKSUM
            else:
                expected_checksum = BACKING_IMAGE_QCOW2_CHECKSUM
        bi = client.create_backing_image(
            name=name, sourceType=BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD,
            parameters={"url": url}, expectedChecksum=expected_checksum,
            minNumberOfCopies=minNumberOfCopies,
            nodeSelector=nodeSelector, diskSelector=diskSelector,
            dataEngine=dataEngine)
    assert bi

    is_ready = False
    for i in range(RETRY_COUNTS):
        bi = client.by_id_backing_image(name)
        if (len(bi.diskFileStatusMap) == minNumberOfCopies and
                bi.currentChecksum != ""):
            for disk, status in iter(bi.diskFileStatusMap.items()):
                if status.state == "ready":
                    is_ready = True
                    break
            if is_ready:
                break
        time.sleep(RETRY_INTERVAL)

    return bi


def check_backing_image_disk_map_status(client, bi_name, expect_cnt, expect_disk_state): # NOQA
    # Number of expect_cnt should equal to number of disk map
    # that have expect_disk_state

    for i in range(RETRY_COUNTS):
        backing_image = client.by_id_backing_image(bi_name)

        count = 0
        for disk_id, status in iter(backing_image.diskFileStatusMap.items()):
            if status.state == expect_disk_state:
                count = count + 1

        if expect_cnt == count:
            break
        time.sleep(RETRY_INTERVAL)

    assert expect_cnt == count


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


# this function checks if create v2 data engine CRs for upgrade is supported,
# and is added for the case of test_upgrade starting from Longhorn >= v1.8.0
# - v2 volumes cannot be upgraded from v1.7 to v1.8:
#   https://github.com/longhorn/longhorn/issues/10053
# - v2 backing images are not supported before v1.8.
def v2_data_engine_cr_supported(client):
    longhorn_version = client.by_id_setting('current-longhorn-version').value
    version_doesnt_support_v2_backimg_image = ['v1.5', 'v1.6', 'v1.7']
    if any(_version in longhorn_version for
           _version in version_doesnt_support_v2_backimg_image):
        print(f'{longhorn_version} doesn\'t support v2 cr for test')
        return False
    else:
        return True


# this function will check if system backup feature is supported, and is added
# for the case of test_upgrade starting from Longhorn >= v1.4.0
def system_backup_feature_supported(client):
    if hasattr(client.by_id_schema("systemBackup"), "id"):
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
    for _ in range(RETRY_COUNTS):
        try:
            setting = client.by_id_setting(name)
            setting = client.update(setting, value=value)
            break
        except Exception as e:
            print(e)
            time.sleep(RETRY_INTERVAL)
    value = "" if value is None else value
    assert setting.value == value, \
        f"expect update setting {name} to be {value}, but it's {setting.value}"


def update_persistent_volume_claim(core_api, name, namespace, claim):
    for _ in range(RETRY_COUNTS):
        try:
            core_api.replace_namespaced_persistent_volume_claim(
                name, namespace, claim
            )
            break
        except Exception as e:
            print(e)
            time.sleep(RETRY_INTERVAL)


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

        expect_retain = spec["retain"]
        if recurring_job.task == "snapshot-cleanup" or \
                recurring_job.task == "filesystem-trim":
            expect_retain = 0
        assert recurring_job.retain == expect_retain

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


def wait_for_cron_job_create(batch_v1_api, label="",
                             retry_counts=RETRY_COUNTS):
    exist = False
    for _ in range(retry_counts):
        job = batch_v1_api.list_namespaced_cron_job('longhorn-system',
                                                    label_selector=label)
        if len(job.items) != 0:
            exist = True
            break
        time.sleep(RETRY_INTERVAL)

    assert exist


def wait_for_cron_job_delete(batch_v1_api, label="",
                             retry_counts=RETRY_COUNTS):
    exist = True
    for _ in range(retry_counts):
        job = batch_v1_api.list_namespaced_cron_job('longhorn-system',
                                                    label_selector=label)
        if len(job.items) == 0:
            exist = False
            break
        time.sleep(RETRY_INTERVAL)

    assert not exist


def wait_for_cron_job_count(batch_v1_api, number, label="",
                            retry_counts=RETRY_COUNTS):
    ok = False
    for _ in range(retry_counts):
        jobs = batch_v1_api.list_namespaced_cron_job('longhorn-system',
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
        try:
            if volume[VOLUME_FIELD_CLONE_STATUS][key] == value:
                break
        except Exception as e:
            print("\nVOLUME_FIELD_CLONE_STATUS is not ready")
            print(e)
        finally:
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
                         fromBackup=backup.url,
                         dataEngine=DATA_ENGINE)
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


def cleanup_all_support_bundles(client):
    """
    Clean up all support bundles
    :param client: The Longhorn client to use in the request.
    """
    support_bundles = client.list_support_bundle()
    for support_bundle in support_bundles:
        id = support_bundle['id']
        name = support_bundle['name']
        # ignore the error when clean up
        try:
            delete_support_bundle(id, name, client)
        except Exception as e:
            print("\nException when cleanup support_bundle ", support_bundle)
            print(e)

    ok = False
    for _ in range(RETRY_COUNTS):
        support_bundles = client.list_support_bundle()
        if len(support_bundles) == 0:
            ok = True
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def check_all_support_bundle_managers_deleted():
    apps_api = get_apps_api_client()
    deployments = get_all_support_bundle_manager_deployments(apps_api)
    for support_bundle_manager in deployments:
        wait_delete_deployment(apps_api, support_bundle_manager.metadata.name,
                               namespace=LONGHORN_NAMESPACE)

    assert len(get_all_support_bundle_manager_deployments(apps_api)) == 0


def create_support_bundle(client):  # NOQA
    data = {'description': 'Test', 'issueURL': ""}
    return requests.post(get_support_bundle_url(client), json=data).json()


def delete_support_bundle(node_id, name, client):
    url = get_support_bundle_url(client)
    support_bundle_url = '{}/{}/{}'.format(url, node_id, name)
    return requests.delete(support_bundle_url)


def download_support_bundle(node_id, name, client, target_path=""):  # NOQA
    url = get_support_bundle_url(client)
    support_bundle_url = '{}/{}/{}'.format(url, node_id, name)
    download_url = '{}/download'.format(support_bundle_url)
    r = requests.get(download_url, allow_redirects=True, timeout=300)
    r.raise_for_status()

    if target_path != "":
        with open(target_path, 'wb') as f:
            f.write(r.content)


def get_all_support_bundle_manager_deployments(apps_api):  # NOQA
    name_prefix = 'longhorn-support-bundle-manager'
    support_bundle_managers = []

    deployments = apps_api.list_namespaced_deployment(LONGHORN_NAMESPACE)
    for deployment in deployments.items:
        if deployment.metadata.name.startswith(name_prefix):
            support_bundle_managers.append(deployment)

    return support_bundle_managers


def get_support_bundle_url(client):  # NOQA
    return client._url.replace('schemas', 'supportbundles')


def get_support_bundle(node_id, name, client):  # NOQA
    url = get_support_bundle_url(client)
    resp = requests.get('{}/{}/{}'.format(url, node_id, name))
    assert resp.status_code == 200
    return resp.json()


def wait_for_support_bundle_cleanup(client):  # NOQA
    ok = False
    for _ in range(RETRY_COUNTS):
        support_bundles = client.list_support_bundle()
        if len(support_bundles) == 0:
            ok = True
            break

        time.sleep(RETRY_INTERVAL)
    assert ok


def wait_for_support_bundle_state(state, node_id, name, client):  # NOQA
    ok = False
    for _ in range(RETRY_COUNTS):
        support_bundle = get_support_bundle(node_id, name, client)
        try:
            assert support_bundle['state'] == state
            ok = True
            break
        except Exception:
            time.sleep(RETRY_INTERVAL)

    assert ok


def generate_support_bundle(case_name):  # NOQA
    """
        Generate support bundle into folder ./support_bundle/case_name.zip

        Won't generate support bundle if current support bundle count
        greater than MAX_SUPPORT_BINDLE_NUMBER.
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
    cleanup_all_support_bundles(client)

    url = client._url.replace('schemas', 'supportbundles')
    data = {'description': case_name, 'issueURL': case_name}
    try:
        res_raw = requests.post(url, json=data)
        res_raw.raise_for_status()
        res = res_raw.json()
    except Exception as e:
        warnings.warn(f"Error while generating support bundle: {e}")
        return
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
        warnings.warn("Error occurred when downloading support bundle {}.zip\n\
            The error was {}".format(case_name, e))


def get_volume_running_replica_cnt(client, volume_name):  # NOQA
    nodes = client.list_node()
    cnt = 0

    for node in nodes:
        cnt = cnt + get_host_replica_count(
            client, volume_name, node.name, chk_running=True)

    return cnt


def create_rwx_volume_with_storageclass(client,
                                        core_api,
                                        storage_class):

    VOLUME_SIZE = str(DEFAULT_VOLUME_SIZE * Gi)

    pvc_name = generate_volume_name()

    pvc_spec = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
                "name": pvc_name,
        },
        "spec": {
            "accessModes": [
                "ReadWriteMany"
            ],
            "storageClassName": storage_class['metadata']['name'],
            "resources": {
                "requests": {
                    "storage": VOLUME_SIZE
                }
            }
        }
    }

    core_api.create_namespaced_persistent_volume_claim(
        'default',
        pvc_spec
    )

    check_pvc_in_specific_status(core_api, pvc_name, 'Bound')

    volume_name = get_volume_name(core_api, pvc_name)

    wait_for_volume_creation(client, volume_name)
    if storage_class['parameters']['fromBackup'] != "":
        wait_for_volume_restoration_completed(client, volume_name)
    wait_for_volume_detached(client, volume_name)

    return volume_name


def create_volume(client, vol_name, size, node_id, r_num):
    volume = client.create_volume(name=vol_name, size=size,
                                  numberOfReplicas=r_num,
                                  dataEngine=DATA_ENGINE)
    assert volume.numberOfReplicas == r_num
    assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

    volume = wait_for_volume_detached(client, vol_name)
    assert len(volume.replicas) == r_num

    assert volume.state == "detached"
    assert volume.created != ""

    volumeByName = client.by_id_volume(vol_name)
    assert volumeByName.name == volume.name
    assert volumeByName.size == volume.size
    assert volumeByName.numberOfReplicas == volume.numberOfReplicas
    assert volumeByName.state == volume.state
    assert volumeByName.created == volume.created

    volume.attach(hostId=node_id)
    volume = wait_for_volume_healthy(client, vol_name)

    return volume


def cleanup_volume_by_name(client, vol_name):
    volume = client.by_id_volume(vol_name)
    volume.detach()
    client.delete(volume)
    wait_for_volume_delete(client, vol_name)


def create_host_disk(client, vol_name, size, node_id):
    # create a single replica volume and attach it to node
    volume = create_volume(client, vol_name, size, node_id, 1)

    # prepare the disk in the host filesystem
    disk_path = prepare_host_disk(get_volume_endpoint(volume), volume.name)
    return disk_path


def cleanup_host_disks(client, *args):
    # clean disk
    for vol_name in args:
        # umount disk
        cleanup_host_disk(vol_name)
        # clean volume
        cleanup_volume_by_name(client, vol_name)


def update_node_disks(client, node_name, disks, retry=False):
    node = client.by_id_node(node_name)

    if not retry:
        return node.diskUpdate(disks=disks)

    # Retry if "too many retries error" happened.
    for _ in range(NODE_UPDATE_RETRY_COUNT):
        try:
            node = node.diskUpdate(disks=disks)
        except Exception as e:
            if disk_being_syncing in str(e.error.message):
                time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                continue
            print(e)
            raise
        else:
            break
    return node


def enable_default_disk(client):
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    disks = get_update_disks(node.disks)
    for disk in disks.values():
        if disk["path"] == DEFAULT_DISK_PATH:
            disk.allowScheduling = True
            disk.evictionRequested = False

    update_node_disks(client, node.name, disks=disks, retry=True)


def wait_for_backing_image_status(client, backing_img_name, image_status):

    status_matched = False
    for _ in range(RETRY_EXEC_COUNTS):
        if status_matched:
            break

        backing_image = client.by_id_backing_image(backing_img_name)
        try:
            if backing_image.diskFileStatusMap.items():
                for _, status in iter(backing_image.diskFileStatusMap.items()):
                    if status.state == image_status:
                        status_matched = True
        except Exception as e:
            print(e)
        time.sleep(RETRY_EXEC_INTERVAL)

    assert status_matched is True


def wait_for_backing_image_in_disk_fail(client, backing_img_name, disk_uuid):

    failed = False
    for i in range(RETRY_BACKUP_COUNTS):
        if failed is False:
            backing_image = client.by_id_backing_image(backing_img_name)
            for uuid, status in iter(backing_image.diskFileStatusMap.items()):
                if uuid == disk_uuid and status.state == "failed":
                    failed = True
        if failed is True:
            break
        time.sleep(0.1)
    assert failed is True


def get_disk_uuid():

    f = open('/var/lib/longhorn/longhorn-disk.cfg')
    data = json.load(f)

    return data["diskUUID"]


def get_engine_host_id(client, vol_name):
    volume = client.by_id_volume(vol_name)

    engines = volume.controllers
    if len(engines) != 1:
        return

    return engines[0].hostId


def system_backups_cleanup(client):
    """
    Clean up all system backups
    :param client: The Longhorn client to use in the request.
    """

    system_backups = client.list_system_backup()
    for system_backup in system_backups:
        # ignore the error when clean up
        try:
            client.delete(system_backup)
        except Exception as e:
            name = system_backup['name']
            print("\nException when cleanup system backup ", name)
            print(e)

    ok = False
    for _ in range(RETRY_COUNTS):
        system_backups = client.list_system_backup()
        if len(system_backups) == 0:
            ok = True
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def system_backup_random_name():
    return "test-system-backup-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def system_backup_wait_for_state(state, name, client):  # NOQA
    ok = False
    for _ in range(RETRY_COUNTS):
        try:
            system_backup = client.by_id_system_backup(name)
            assert system_backup.state == state
            ok = True
            break
        except Exception:
            time.sleep(RETRY_INTERVAL)

    assert ok


def system_restores_cleanup(client):
    """
    Clean up all system restores
    :param client: The Longhorn client to use in the request.
    """

    system_restores = client.list_system_restore()
    for system_restore in system_restores:
        # ignore the error when clean up
        try:
            client.delete(system_restore)
        except Exception as e:
            name = system_restore['name']
            print("\nException when cleanup system restore ", name)
            print(e)

    ok = False
    for _ in range(RETRY_COUNTS):
        system_restores = client.list_system_restore()
        if len(system_restores) == 0:
            ok = True
            break
        time.sleep(RETRY_INTERVAL)
    assert ok


def system_restore_random_name():
    return "test-system-restore-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def system_restore_wait_for_state(state, name, client):  # NOQA
    ok = False
    for _ in range(RETRY_COUNTS):
        system_restore = client.by_id_system_restore(name)
        try:
            system_restore = client.by_id_system_restore(name)
            assert system_restore.state == state
            ok = True
            break
        except Exception:
            time.sleep(RETRY_INTERVAL_LONG)

    assert ok, \
        f" Expected state {state}, " \
        f" but got {system_restore.state} after {RETRY_COUNTS} attempts"


def create_volume_and_write_data(client, volume_name, volume_size=SIZE,
                                 data_engine=DATA_ENGINE):
    """
    1. Create and attach a volume
    2. Write the data to volume
    """
    # Step 1
    volume = create_and_check_volume(client,
                                     volume_name,
                                     size=volume_size,
                                     data_engine=data_engine)
    volume = volume.attach(hostId=get_self_host_id())
    volume = wait_for_volume_healthy(client, volume_name)

    # Step 2
    volume_data = write_volume_random_data(volume)

    return volume, volume_data


def get_instance_manager_names(client, data_engine=DATA_ENGINE):
    ims = client.list_instance_manager()
    result = []

    for im in ims:
        if im.dataEngine == data_engine:
            result.append(im.name)
    return result


def wait_for_instance_manager_count(client, number, retry_counts=120):
    for _ in range(retry_counts):
        im_counts = 0
        ims = client.list_instance_manager()
        for im in ims:
            if im.dataEngine == DATA_ENGINE:
                im_counts = im_counts + 1

        if im_counts == number:
            break
        time.sleep(RETRY_INTERVAL_LONG)
    return im_counts


def create_deployment_and_write_data(client, # NOQA
                                     core_api, # NOQA
                                     make_deployment_with_pvc, # NOQA
                                     volume_name, # NOQA
                                     size, # NOQA
                                     replica_count, # NOQA
                                     data_size, # NOQA
                                     attach_node_id=None): # NOQA
    apps_api = get_apps_api_client()
    volume = client.create_volume(name=volume_name,
                                  size=size,
                                  numberOfReplicas=replica_count,
                                  dataEngine=DATA_ENGINE)
    volume = wait_for_volume_detached(client, volume_name)

    pvc_name = volume_name + "-pvc"
    create_pv_for_volume(client, core_api, volume, volume_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name)
    deployment_name = volume_name + "-dep"
    deployment = make_deployment_with_pvc(deployment_name, pvc_name)
    if attach_node_id:
        deployment["spec"]["template"]["spec"]["nodeSelector"] \
            = {"kubernetes.io/hostname": attach_node_id}

    create_and_wait_deployment(apps_api, deployment)

    data_path = '/data/test'
    deployment_pod_names = get_deployment_pod_names(core_api,
                                                    deployment)
    write_pod_volume_random_data(core_api,
                                 deployment_pod_names[0],
                                 data_path,
                                 data_size)

    checksum = get_pod_data_md5sum(core_api,
                                   deployment_pod_names[0],
                                   data_path)

    volume = client.by_id_volume(volume_name)
    return volume, deployment_pod_names[0], checksum, deployment


def wait_delete_dm_device(api, name):
    path = os.path.join("/dev/mapper", name)
    for i in range(RETRY_COUNTS):
        found = os.path.exists(path)
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found


def wait_for_volume_replica_rebuilt_on_same_node_different_disk(client, node_name, volume_name, old_disk_name):  # NOQA
    new_disk_name = ""
    for _ in range(RETRY_COUNTS_SHORT):
        time.sleep(RETRY_INTERVAL_LONG)

        node = client.by_id_node(node_name)
        disks = node.disks
        new_disk_name = ""
        for name, disk in disks.items():
            # if scheduledReplica has prefix of volume-name
            for scheduledReplica, _ in disk.scheduledReplica.items():
                if scheduledReplica.startswith(volume_name):
                    new_disk_name = name
                    break
        if new_disk_name != old_disk_name:
            break

    assert new_disk_name != old_disk_name, \
        "Failed to rebuild replica disk to another disk"


def set_tags_for_node_and_its_disks(client, node, node_tags, disks_tags_map): # NOQA
    for disk_name in node.disks.keys():
        if disk_name in disks_tags_map:
            node.disks[disk_name].tags = disks_tags_map[disk_name]

    node = update_node_disks(client, node.name, disks=node.disks)
    for disk_name in node.disks.keys():
        if disk_name in disks_tags_map:
            assert node.disks[disk_name].tags == disks_tags_map[disk_name]

    if len(node_tags) == 0:
        expected_tags = []
    else:
        expected_tags = list(node_tags)

    node = set_node_tags(client, node, node_tags)
    assert node.tags == expected_tags


def set_tags_for_node_and_its_disks(client, node, tags): # NOQA
    if len(tags) == 0:
        expected_tags = []
    else:
        expected_tags = list(tags)

    for disk_name in node.disks.keys():
        node.disks[disk_name].tags = tags
    node = update_node_disks(client, node.name, disks=node.disks)
    for disk_name in node.disks.keys():
        assert node.disks[disk_name].tags == expected_tags

    node = set_node_tags(client, node, tags)
    assert node.tags == expected_tags

    return node


def get_node_by_disk_id(client, disk_id): # NOQA
    nodes = client.list_node()

    for node in nodes:
        disks = node.disks
        for name, disk in iter(disks.items()):
            if disk.diskUUID == disk_id:
                return node
    # should handle empty result in caller
    return ""


def check_backing_image_single_copy_disk_eviction(client, bi_name, old_disk_id): # NOQA
    for i in range(RETRY_COUNTS):
        backing_image = client.by_id_backing_image(bi_name)
        current_disk_id = next(iter(backing_image.diskFileStatusMap))
        if current_disk_id != old_disk_id:
            break

        time.sleep(RETRY_INTERVAL)

    assert current_disk_id != old_disk_id


def check_backing_image_single_copy_node_eviction(client, bi_name, old_node): # NOQA
    for i in range(RETRY_COUNTS):
        backing_image = client.by_id_backing_image(bi_name)
        current_disk_id = next(iter(backing_image.diskFileStatusMap))
        current_node = get_node_by_disk_id(client, current_disk_id)
        if current_node.name != old_node.name:
            break

        time.sleep(RETRY_INTERVAL)

    assert current_node.name != old_node.name


def check_backing_image_eviction_failed(name): # NOQA
    core_client = get_core_api_client()
    selector = "involvedObject.kind=BackingImage,involvedObject.name=" + name
    check = False

    for i in range(RETRY_COUNTS_LONG):
        events = core_client.list_namespaced_event(
            namespace=LONGHORN_NAMESPACE,
            field_selector=selector,
        ).items
        if len(events) == 0:
            continue

        for j in range(len(events)):
            if (events[j].reason == FAILED_DELETING_REASONE and
                    BACKINGIMAGE_FAILED_EVICT_MSG in events[j].message):
                check = True
                break

        if check:
            break

        time.sleep(RETRY_INTERVAL)

    assert check


def wait_for_replica_count(client, volume_name, replica_count):
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(volume_name)
        if len(volume.replicas) == replica_count:
            break
        time.sleep(RETRY_INTERVAL)

    volume = client.by_id_volume(volume_name)
    assert len(volume.replicas) == replica_count
