import atexit
import hashlib
import os
import pytest
import subprocess
import random
import string
import datetime

from common import create_and_check_volume
from common import create_and_wait_pod
from common import create_pvc_for_volume
from common import create_pv_for_volume
from common import create_snapshot
from common import delete_and_wait_longhorn
from common import delete_and_wait_pod
from common import delete_and_wait_pv
from common import delete_and_wait_pvc
from common import delete_and_wait_volume_attachment
from common import DIRECTORY_PATH
from common import find_backup
from common import generate_pod_with_pvc_manifest
from common import generate_random_data
from common import get_core_api_client
from common import get_longhorn_api_client
from common import get_self_host_id
from common import get_storage_api_client
from common import get_volume_endpoint
from common import Gi
from common import mount_disk
from common import read_volume_data
from common import RETRY_COUNTS
from common import set_random_backupstore
from common import SETTING_BACKUP_TARGET
from common import umount_disk
from common import wait_for_backup_completion
from common import wait_for_snapshot_purge
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import wait_for_volume_healthy_no_frontend
from common import wait_for_volume_replica_count
from common import wait_for_volume_restoration_completed
from common import write_pod_volume_data
from kubernetes.stream import stream
from random import randrange
from test_scheduling import wait_new_replica_ready


# Configuration options
N_RANDOM_ACTIONS = 10
WAIT_REPLICA_REBUILD = True   # True, False, None=random
PURGE_DELETED_SNAPSHOT = None  # True, False, None=random
WAIT_BACKUP_COMPLETE = True  # True, False, None=random


NPODS = os.getenv("STRESS_TEST_NPODS")

if NPODS is None:
    NPODS = 1
else:
    NPODS = int(NPODS)

count = [str(i) for i in range(NPODS)]


STRESS_POD_NAME_PREFIX = "stress-test-pod-"
STRESS_PVC_NAME_PREFIX = "stress-test-pvc-"
STRESS_PV_NAME_PREFIX = "stress-test-pv-"
STRESS_VOLUME_NAME_PREFIX = "stress-test-volume-"


STRESS_RANDOM_DATA_DIR = "/tmp/"
STRESS_DATAFILE_NAME_PREFIX = "data-"
STRESS_DATAFILE_NAME_SUFFIX = ".bin"
STRESS_DEST_DIR = '/data/'

VOLUME_SIZE = str(2 * Gi)
TEST_DATA_BYTES = 1 * Gi

READ_MD5SUM_TIMEOUT = 120


class snapshot_data:
    def __init__(self, snapshot_name):
        self.snapshot_name = snapshot_name
        self.removed = False
        self.backup_name = None
        self.backup_url = None
        self.data_md5sum = None

    def set_backup_name(self, backup_name):
        self.backup_name = backup_name

    def set_backup_url(self, backup_url):
        self.backup_url = backup_url

    def set_data_md5sum(self, data_md5sum):
        self.data_md5sum = data_md5sum

    def mark_as_removed(self):
        self.removed = True


def time_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# set random backupstore if not defined
def check_and_set_backupstore(client):
    setting = client.by_id_setting(SETTING_BACKUP_TARGET)

    if setting["value"] == "":
        set_random_backupstore(client)


def get_random_suffix():
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(6))


def get_md5sum(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_random_snapshot(snapshots_md5sum):
    snapshots = list(snapshots_md5sum.keys())

    snapshots_count = len(snapshots)

    if snapshots_count == 0:
        return None

    for i in range(RETRY_COUNTS):
        snapshot_id = randrange(0, snapshots_count)
        snapshot = snapshots[snapshot_id]

        if snapshots_md5sum[snapshot].removed is True:
            continue
        else:
            break

    if snapshots_md5sum[snapshot].removed is True:
        return None
    else:
        return snapshot


def get_random_backup_snapshot_data(snapshots_md5sum):
    snapshots = list(snapshots_md5sum.keys())

    snapshots_count = len(snapshots)

    if snapshots_count == 0:
        return None

    for i in range(RETRY_COUNTS):
        snapshot_id = randrange(0, snapshots_count)
        snapshot = snapshots[snapshot_id]

        if snapshots_md5sum[snapshot].backup_name is None:
            continue
        else:
            break

    if snapshots_md5sum[snapshot].backup_name is None:
        return None
    else:
        return snapshots_md5sum[snapshot]


def get_recurring_jobs():
    backup_job = {"name": "backup", "cron": "*/5 * * * *",
                  "task": "backup", "retain": 3}

    snapshot_job = {"name": "snap", "cron": "*/2 * * * *",
                    "task": "snapshot", "retain": 5}

    return [backup_job, snapshot_job]


def create_recurring_jobs(client, volume_name):
    volume = client.by_id_volume(volume_name)

    recurring_jobs = get_recurring_jobs()

    volume.recurringUpdate(jobs=recurring_jobs)


def read_data_md5sum(k8s_api_client, pod_name):
    file_name = get_data_filename(pod_name)
    dest_file_path = os.path.join(STRESS_DEST_DIR, file_name)

    exec_command = exec_command = ['/bin/sh']
    resp = stream(k8s_api_client.connect_get_namespaced_pod_exec,
                  pod_name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=False,
                  _preload_content=False)

    resp.write_stdin("md5sum " + dest_file_path + "\n")
    res = resp.readline_stdout(timeout=READ_MD5SUM_TIMEOUT).split()[0]

    return res


def snapshot_create_and_record_md5sum(client, core_api, volume_name, pod_name, snapshots_md5sum): # NOQA
    data_md5sum = read_data_md5sum(core_api, pod_name)
    snap = create_snapshot(client, volume_name)

    snap_data = snapshot_data(snap["name"])
    snap_data.set_data_md5sum(data_md5sum)
    snapshots_md5sum[snap["name"]] = snap_data

    return snap["name"]


def revert_random_snapshot(client, core_api, volume_name, pod_manifest, snapshots_md5sum): # NOQA
    volume = client.by_id_volume(volume_name)
    host_id = get_self_host_id()
    pod_name = pod_manifest["metadata"]["name"]

    snapshot = get_random_snapshot(snapshots_md5sum)

    if snapshot is None:
        return

    delete_and_wait_pod(core_api, pod_name)

    wait_for_volume_detached(client, volume_name)

    volume = client.by_id_volume(volume_name)

    volume.attach(hostId=host_id, disableFrontend=True)

    volume = wait_for_volume_healthy_no_frontend(client, volume_name)

    volume.snapshotRevert(name=snapshot)

    volume = client.by_id_volume(volume_name)

    volume.detach()

    wait_for_volume_detached(client, volume_name)

    create_and_wait_pod(core_api, pod_manifest)

    current_md5sum = read_data_md5sum(core_api, pod_name)

    assert current_md5sum == snapshots_md5sum[snapshot].data_md5sum


def backup_create_and_record_md5sum(client, core_api, volume_name, pod_name, snapshots_md5sum): # NOQA
    volume = client.by_id_volume(volume_name)

    data_md5sum = read_data_md5sum(core_api, pod_name)

    snap_name = snapshot_create_and_record_md5sum(client,
                                                  core_api,
                                                  volume_name,
                                                  pod_name,
                                                  snapshots_md5sum)
    snap = snapshot_data(snap_name)

    snapshots_md5sum[snap_name] = snap

    volume.snapshotBackup(name=snap_name)

    global WAIT_BACKUP_COMPLETE
    if WAIT_BACKUP_COMPLETE is None:
        WAIT_BACKUP_COMPLETE = bool(random.getrandbits(1))

    if WAIT_BACKUP_COMPLETE is True:
        wait_for_backup_completion(client, volume_name, snap_name)

    _, b = find_backup(client, volume_name, snap_name)

    snap.set_backup_name(b["name"])
    snap.set_backup_url(b["url"])
    snap.set_data_md5sum(data_md5sum)


def restore_and_check_random_backup(client, core_api, volume_name, pod_name, snapshots_md5sum): # NOQA
    res_volume_name = volume_name + '-restore'

    host_id = get_self_host_id()

    snap_data = get_random_backup_snapshot_data(snapshots_md5sum)

    if snap_data is None:
        return

    backup_url = snap_data.backup_url

    client.create_volume(name=res_volume_name,
                         size=VOLUME_SIZE,
                         fromBackup=backup_url)

    wait_for_volume_restoration_completed(client, res_volume_name)

    wait_for_volume_detached(client, res_volume_name)

    res_volume = client.by_id_volume(res_volume_name)

    res_volume.attach(hostId=host_id)

    res_volume = wait_for_volume_healthy(client, res_volume_name)

    dev = get_volume_endpoint(res_volume)

    mount_path = os.path.join(DIRECTORY_PATH, res_volume_name)

    command = ['mkdir', '-p', mount_path]
    subprocess.check_call(command)

    mount_disk(dev, mount_path)

    datafile_name = get_data_filename(pod_name)
    datafile_path = os.path.join(mount_path, datafile_name)

    command = ['md5sum', datafile_path]
    output = subprocess.check_output(command)

    bkp_data_md5sum = output.split()[0].decode('utf-8')

    bkp_checksum_ok = False
    if snap_data.data_md5sum == bkp_data_md5sum:
        bkp_checksum_ok = True

    umount_disk(mount_path)

    command = ['rmdir', mount_path]
    subprocess.check_call(command)

    res_volume = client.by_id_volume(res_volume_name)

    res_volume.detach()

    wait_for_volume_detached(client, res_volume_name)

    delete_and_wait_longhorn(client, res_volume_name)

    assert bkp_checksum_ok


def delete_replica(client, volume_name):
    volume = client.by_id_volume(volume_name)

    replica_count = len(volume.replicas)

    healthy_replica_count = 0
    for replica in volume.replicas:
        if replica.running is True and replica.mode == "RW":
            healthy_replica_count += 1

    # return if there is only one healthy replica left
    if healthy_replica_count == 1:
        return

    replica_id = randrange(0, replica_count)

    replica_name = volume["replicas"][replica_id]["name"]

    volume.replicaRemove(name=replica_name)

    global WAIT_REPLICA_REBUILD
    if WAIT_REPLICA_REBUILD is None:
        WAIT_REPLICA_REBUILD = bool(random.getrandbits(1))

    if WAIT_REPLICA_REBUILD is True:
        wait_for_volume_replica_count(client, volume_name, replica_count)
        replica_names = map(lambda replica: replica.name, volume["replicas"])
        wait_new_replica_ready(client, volume_name, replica_names)


def write_data(k8s_api_client, pod_name):
    src_dir_path = STRESS_RANDOM_DATA_DIR
    dest_dir_path = '/data/'
    file_name = get_data_filename(pod_name)

    src_file_path = src_dir_path + file_name
    dest_file_path = dest_dir_path + file_name

    src_file = open('%s' % src_file_path, 'wb')
    src_file.write(os.urandom(TEST_DATA_BYTES))
    src_file.close()
    src_file_md5sum = get_md5sum(src_file_path)
    command = 'kubectl cp ' + src_file_path + \
              ' ' + pod_name + ':' + dest_file_path
    subprocess.call(command, shell=True)

    exec_command = exec_command = ['/bin/sh']
    resp = stream(k8s_api_client.connect_get_namespaced_pod_exec,
                  pod_name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=False,
                  _preload_content=False)

    resp.write_stdin("md5sum " + dest_file_path + "\n")
    res = resp.readline_stdout(timeout=READ_MD5SUM_TIMEOUT).split()[0]

    assert res == src_file_md5sum


def delete_data(k8s_api_client, pod_name):
    file_name = 'data-' + pod_name + '.bin'
    test_data = generate_random_data(0)

    write_pod_volume_data(k8s_api_client,
                          pod_name,
                          test_data,
                          filename=file_name)

    volume_data = read_volume_data(k8s_api_client,
                                   pod_name,
                                   filename=file_name)

    assert volume_data == ""


def purge_random_snapshot(longhorn_api_client, volume_name, snapshot_name):

    volume = longhorn_api_client.by_id_volume(volume_name)

    volume.snapshotPurge()

    wait_for_snapshot_purge(
        longhorn_api_client,
        volume_name,
        snapshot_name
    )


def delete_random_snapshot(client, volume_name, snapshots_md5sum):
    volume = client.by_id_volume(volume_name)

    snapshot = get_random_snapshot(snapshots_md5sum)

    if snapshot is None:
        return

    volume.snapshotDelete(name=snapshot)

    snapshots_md5sum[snapshot].mark_as_removed()

    global PURGE_DELETED_SNAPSHOT
    if PURGE_DELETED_SNAPSHOT is None:
        PURGE_DELETED_SNAPSHOT = bool(random.getrandbits(1))

    if PURGE_DELETED_SNAPSHOT is True:
        purge_random_snapshot(client, volume_name, snapshot)


def get_data_filename(pod_name):
    return STRESS_DATAFILE_NAME_PREFIX + pod_name + STRESS_DATAFILE_NAME_SUFFIX


def remove_datafile(pod_name):
    file_path = os.path.join(STRESS_RANDOM_DATA_DIR,
                             get_data_filename(pod_name))

    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.mark.stress
def test_stress(generate_load):
    pass


@pytest.fixture
def generate_load(request):

    index = get_random_suffix()

    longhorn_api_client = get_longhorn_api_client()
    k8s_api_client = get_core_api_client()

    check_and_set_backupstore(longhorn_api_client)

    volume_name = STRESS_VOLUME_NAME_PREFIX + index
    pv_name = STRESS_PV_NAME_PREFIX + index
    pvc_name = STRESS_PVC_NAME_PREFIX + index
    pod_name = STRESS_POD_NAME_PREFIX + index

    atexit.register(remove_datafile, pod_name)
    atexit.register(delete_and_wait_longhorn, longhorn_api_client, volume_name)
    atexit.register(delete_and_wait_pv, k8s_api_client, pv_name)
    atexit.register(delete_and_wait_pvc, k8s_api_client, pvc_name)
    atexit.register(delete_and_wait_pod, k8s_api_client, pod_name)

    longhorn_volume = create_and_check_volume(
        longhorn_api_client,
        volume_name,
        size=VOLUME_SIZE
    )

    wait_for_volume_detached(longhorn_api_client, volume_name)

    pod_manifest = generate_pod_with_pvc_manifest(pod_name, pvc_name)

    create_pv_for_volume(longhorn_api_client,
                         k8s_api_client,
                         longhorn_volume,
                         pv_name)

    create_pvc_for_volume(longhorn_api_client,
                          k8s_api_client,
                          longhorn_volume,
                          pvc_name)

    create_and_wait_pod(k8s_api_client, pod_manifest)

    snapshots_md5sum = dict()

    write_data(k8s_api_client, pod_name)
    create_recurring_jobs(longhorn_api_client, volume_name)

    global N_RANDOM_ACTIONS
    for round in range(N_RANDOM_ACTIONS):
        action = randrange(0, 8)

        if action == 0:
            print("write data started: " + time_now(), end=', ')
            write_data(k8s_api_client, pod_name)
            print("ended: " + time_now())

        elif action == 1:
            print("delete data started: " + time_now(), end=', ')
            delete_data(k8s_api_client, pod_name)
            print("ended: " + time_now())

        elif action == 2:
            print("create snapshot started: " + time_now(), end=', ')
            snapshot_create_and_record_md5sum(longhorn_api_client,
                                              k8s_api_client,
                                              volume_name,
                                              pod_name,
                                              snapshots_md5sum)
            print("ended: " + time_now())

        elif action == 3:
            print("delete random snapshot  started: " + time_now(), end=', ')
            delete_random_snapshot(longhorn_api_client,
                                   volume_name,
                                   snapshots_md5sum)
            print("ended: " + time_now())

        elif action == 4:
            print("revert random snapshot started: " + time_now(), end=', ')
            revert_random_snapshot(longhorn_api_client,
                                   k8s_api_client,
                                   volume_name,
                                   pod_manifest,
                                   snapshots_md5sum)
            print("ended: " + time_now())

        elif action == 5:
            print("create backup started: " + time_now(), end=', ')
            backup_create_and_record_md5sum(longhorn_api_client,
                                            k8s_api_client,
                                            volume_name,
                                            pod_name,
                                            snapshots_md5sum)
            print("ended: " + time_now())

        elif action == 6:
            print("delete replica started: " + time_now(), end=', ')
            delete_replica(longhorn_api_client, volume_name)
            print("ended: " + time_now())

        elif action == 7:
            print("restore random backup started: " + time_now(), end=', ')
            restore_and_check_random_backup(longhorn_api_client,
                                            k8s_api_client,
                                            volume_name,
                                            pod_name,
                                            snapshots_md5sum)

            print("ended: " + time_now())


@pytest.mark.stress
def test_reset_env():
    k8s_api_client = get_core_api_client()
    k8s_storage_client = get_storage_api_client()
    longhorn_api_client = get_longhorn_api_client()

    pod_list = k8s_api_client.list_namespaced_pod("default")
    for pod in pod_list.items:
        if STRESS_POD_NAME_PREFIX in pod.metadata.name:
            delete_and_wait_pod(k8s_api_client, pod.metadata.name)

    pvc_list = \
        k8s_api_client.list_namespaced_persistent_volume_claim("default")
    for pvc in pvc_list.items:
        if STRESS_PVC_NAME_PREFIX in pvc.metadata.name:
            delete_and_wait_pvc(k8s_api_client, pvc.metadata.name)

    pv_list = k8s_api_client.list_persistent_volume()
    for pv in pv_list.items:
        pv_name = pv.metadata.name
        if STRESS_PV_NAME_PREFIX in pv_name:
            try:
                delete_and_wait_pv(k8s_api_client, pv_name)
            except AssertionError:
                volumeattachment_list = \
                    k8s_storage_client.list_volume_attachment()
                for volumeattachment in volumeattachment_list.items:
                    volume_attachment_name = \
                        volumeattachment.spec.source.persistent_volume_name
                    if volume_attachment_name == pv_name:
                        delete_and_wait_volume_attachment(
                            k8s_storage_client,
                            volume_attachment_name
                        )
                        delete_and_wait_pv(k8s_api_client, pv.metadata.name)

    volume_list = \
        longhorn_api_client.list_volume()
    for volume in volume_list.data:
        if STRESS_VOLUME_NAME_PREFIX in volume.name:
            delete_and_wait_longhorn(longhorn_api_client, volume.name)
