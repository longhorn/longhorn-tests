import time
import os
import stat
import random
import string

import pytest

import cattle

from kubernetes import client as k8sclient, config as k8sconfig

SIZE = str(16 * 1024 * 1024)
VOLUME_NAME = "longhorn-testvol"
DEV_PATH = "/dev/longhorn/"
VOLUME_RWTEST_SIZE = 512
VOLUME_INVALID_POS = -1
PORT = ":9500"

RETRY_COUNTS = 300
RETRY_ITERVAL = 0.5

LONGHORN_NAMESPACE = "longhorn-system"

COMPATIBILTY_TEST_IMAGE_PREFIX = "rancher/longhorn-test:version-test"
UPGRADE_TEST_IMAGE_PREFIX = "rancher/longhorn-test:upgrade-test"

ISCSI_DEV_PATH = "/dev/disk/by-path"


@pytest.fixture
def clients(request):
    k8sconfig.load_incluster_config()
    ips = get_mgr_ips()
    client = get_client(ips[0] + PORT)
    hosts = client.list_node()
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


def wait_for_volume_state(client, name, state):
    wait_for_volume_creation(client, name)
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


def volume_read(dev, start, count):
    r_data = ""
    fdev = open(dev, 'rb')
    if fdev is not None:
        fdev.seek(start)
        r_data = fdev.read(count)
        fdev.close()
    return r_data


def volume_write(dev, start, data):
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
