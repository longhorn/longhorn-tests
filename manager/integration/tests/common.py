import time
import os
import random
import string

import pytest

import cattle

from kubernetes import client as k8sclient, config as k8sconfig

SIZE = str(16 * 1024 * 1024)
VOLUME_NAME = "longhorn-testvol"
DEV_PATH = "/dev/longhorn/"

PORT = ":9500"

RETRY_COUNTS = 300
RETRY_ITERVAL = 0.5

LONGHORN_NAMESPACE = "longhorn-system"

COMPATIBILTY_TEST_IMAGE_PREFIX = "rancher/longhorn-test:version-test"
UPGRADE_TEST_IMAGE_PREFIX = "rancher/longhorn-test:upgrade-test"


@pytest.fixture
def clients(request):
    k8sconfig.load_incluster_config()
    ips = get_mgr_ips()
    client = get_client(ips[0] + PORT)
    hosts = client.list_host()
    assert len(hosts) == len(ips)
    clis = get_clients(hosts)
    request.addfinalizer(lambda: cleanup_clients(clis))
    cleanup_clients(clis)
    return clis


def cleanup_clients(clis):
    client = clis.itervalues().next()
    volumes = client.list_volume()
    for v in volumes:
        # ignore the error when clean up
        try:
            client.delete(v)
        except Exception:
            pass
    images = client.list_engine_image()
    for img in images:
        if not img["default"]:
            # ignore the error when clean up
            try:
                client.delete(img)
            except Exception:
                pass


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


def get_backupstore_url():
    backupstore = os.environ['LONGHORN_BACKUPSTORE']
    assert backupstore != ""
    return backupstore


def get_clients(hosts):
    clients = {}
    for host in hosts:
        assert host["uuid"] is not None
        assert host["address"] is not None
        clients[host["uuid"]] = get_client(host["address"] + PORT)
    return clients


def wait_for_volume_state(client, name, state):
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume["state"] == state:
            break
        time.sleep(RETRY_ITERVAL)
    assert volume["state"] == state
    return volume


def wait_for_volume_delete(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        found = False
        for volume in volumes:
            if volume["name"] == name:
                found = True
        if not found:
            break
        time.sleep(RETRY_ITERVAL)
    assert not found


def wait_for_volume_engine_image(client, name, image):
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume["engineImage"] == image:
            break
        time.sleep(RETRY_ITERVAL)
    assert volume["engineImage"] == image
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


def wait_for_engine_image_state(client, image_name, state):
    for i in range(RETRY_COUNTS):
        image = client.by_id_engine_image(image_name)
        if image["state"] == state:
            break
        time.sleep(RETRY_ITERVAL)
    assert image["state"] == state
    return image


def wait_for_engine_image_ref_count(client, image_name, count):
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
def csi_pvc_name(request):
    return generate_volume_name()


def generate_volume_name():
    return VOLUME_NAME + "-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def get_backupstore_credential():
    backupcredential = os.environ['LONGHORN_BACKUPSTORE_CREDENTIAL_SECRET']
    assert backupcredential != ""
    return backupcredential


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


def get_upgrade_test_image(cli_v, cli_minv,
                           ctl_v, ctl_minv,
                           data_v, data_minv):
    return "%s.%d-%d.%d-%d.%d-%d" % (UPGRADE_TEST_IMAGE_PREFIX,
                                     cli_v, cli_minv,
                                     ctl_v, ctl_minv,
                                     data_v, data_minv)
