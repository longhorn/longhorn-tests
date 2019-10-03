import atexit
import hashlib
import os
import pytest
import subprocess
import random
import string
import time

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
from common import generate_pod_with_pvc_manifest
from common import generate_random_data
from common import get_core_api_client
from common import get_longhorn_api_client
from common import get_self_host_id
from common import get_storage_api_client
from common import Gi
from common import read_volume_data
from common import wait_for_snapshot_purge
from common import wait_for_volume_detached
from common import write_pod_volume_data
from common import wait_for_volume_healthy
from kubernetes.stream import stream
from random import randrange


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

READ_MD5SUM_TIMEOUT = 90


def get_random_suffix():
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(6))


def get_md5sum(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def revert_random_snapshot(client, core_api, volume_name, pod_manifest, snapshots_md5sum): # NOQA
    volume = client.by_id_volume(volume_name)
    host_id = get_self_host_id()
    pod_name = pod_manifest["metadata"]["name"]
    snapshots = volume.snapshotList(volume=volume_name)
    snapshots_count = len(snapshots.data)

    while True:
        snapshot_id = randrange(0, snapshots_count)

        if snapshots.data[snapshot_id].name == "volume-head":
            continue
        else:
            break
    snapshot_name = snapshots.data[snapshot_id].name

    delete_and_wait_pod(core_api, pod_name)
    wait_for_volume_detached(client, volume_name)

    # wait for one second before trying to attach volume again
    time.sleep(1)

    volume = client.by_id_volume(volume_name)

    volume.attach(hostId=host_id, disableFrontend=True)

    wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    volume.snapshotRevert(name=snapshot_name)

    volume = client.by_id_volume(volume_name)

    volume.detach()

    wait_for_volume_detached(client, volume_name)
    create_and_wait_pod(core_api, pod_manifest)

    current_md5sum = read_data_md5sum(core_api, pod_name)

    checksum_ok = False
    for snap_data in snapshots_md5sum:
        if snap_data["snap_name"] == snapshot_name:
            if snap_data["md5sum"] == current_md5sum:
                checksum_ok = True
                break

    assert checksum_ok

def snapshot_create_and_record_md5sum(client, core_api, volume_name, pod_name, snapshots_md5sum): # NOQA
    data_md5sum = read_data_md5sum(core_api, pod_name)
    snap = create_snapshot(client, volume_name)

    snapshots_md5sum.append({"snap_name": snap["name"],
                             "md5sum": data_md5sum})


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


def write_data(k8s_api_client, pod_name):
    file_name = get_data_filename(pod_name)

    src_file_path = os.path.join(STRESS_RANDOM_DATA_DIR, file_name)
    dest_file_path = os.path.join(STRESS_DEST_DIR, file_name)

    src_file = open('%s' % src_file_path, 'wb')
    src_file.write(os.urandom(TEST_DATA_BYTES))
    src_file.close()
    src_file_md5sum = get_md5sum(src_file_path)
    command = 'kubectl cp ' + src_file_path + \
              ' ' + pod_name + ':' + dest_file_path
    subprocess.call(command, shell=True)

    res = read_data_md5sum(k8s_api_client, pod_name)

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


def delete_random_snapshot(longhorn_api_client, volume_name):
    volume = longhorn_api_client.by_id_volume(volume_name)

    snapshots = volume.snapshotList(volume=volume_name)

    snapshots_count = len(snapshots.data)

    while True:
        snapshot_id = randrange(0, snapshots_count)

        if snapshots.data[snapshot_id].name == "volume-head":
            continue
        else:
            break
    snapshot_name = snapshots.data[snapshot_id].name

    volume.snapshotDelete(name=snapshot_name)

    trigger_purge = randrange(0, 2)

    if trigger_purge == 1:
        purge_random_snapshot(longhorn_api_client, volume_name, snapshot_name)


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

    snapshots_md5sum = list()

    write_data(k8s_api_client, pod_name)

    snapshot_create_and_record_md5sum(longhorn_api_client,
                                      k8s_api_client,
                                      volume_name,
                                      pod_name,
                                      snapshots_md5sum)

    write_data(k8s_api_client, pod_name)

    snapshot_create_and_record_md5sum(longhorn_api_client,
                                      k8s_api_client,
                                      volume_name,
                                      pod_name,
                                      snapshots_md5sum)

    write_data(k8s_api_client, pod_name)

    snapshot_create_and_record_md5sum(longhorn_api_client,
                                      k8s_api_client,
                                      volume_name,
                                      pod_name,
                                      snapshots_md5sum)

    revert_random_snapshot(longhorn_api_client,
                           k8s_api_client,
                           volume_name,
                           pod_manifest,
                           snapshots_md5sum)

    delete_data(k8s_api_client, pod_name)

    delete_random_snapshot(longhorn_api_client, volume_name)

    # execute 5 more random actions
    for round in range(5):
        action = randrange(0, 5)

        if action == 0:
            write_data(k8s_api_client, pod_name)
        elif action == 1:
            delete_data(k8s_api_client, pod_name)
        elif action == 2:
            snapshot_create_and_record_md5sum(longhorn_api_client,
                                              k8s_api_client,
                                              volume_name,
                                              pod_name,
                                              snapshots_md5sum)
        elif action == 3:
            delete_random_snapshot(longhorn_api_client, volume_name)
        elif action == 4:
            revert_random_snapshot(longhorn_api_client,
                                   k8s_api_client,
                                   volume_name,
                                   pod_manifest,
                                   snapshots_md5sum)


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
