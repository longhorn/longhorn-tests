import time
import os
import stat
import random
import string

import pytest

import cattle

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.stream import stream

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

VOLUME_FIELD_STATE = "state"
VOLUME_STATE_ATTACHED = "attached"
VOLUME_STATE_DETACHED = "detached"

VOLUME_FIELD_ROBUSTNESS = "robustness"
VOLUME_ROBUSTNESS_HEALTHY = "healthy"
VOLUME_ROBUSTNESS_FAULTED = "faulted"

DEFAULT_LONGHORN_PARAMS = {
    'numberOfReplicas': '3',
    'staleReplicaTimeout': '30'
}

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180

DEFAULT_VOLUME_SIZE = 3  # In Gi

Gi = (1 * 1024 * 1024 * 1024)


def create_and_wait_pod(api, pod_name, volume):
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
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': pod_name
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
                    'name': volume['name'],
                    'mountPath': '/data'
                }],
            }],
            'volumes': [volume]
        }
    }
    api.create_namespaced_pod(
        body=pod_manifest,
        namespace='default')
    for i in range(DEFAULT_POD_TIMEOUT):
        pod = api.read_namespaced_pod(
            name=pod_name,
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
    return str(volume_size >> 30) + 'Gi'


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
    return k8sclient.CoreV1Api()


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


def check_data(dev, data):
    """
    Checks if the data written on the block device matches the inputted data.
    """
    resp = volume_read(dev, data['pos'], data['len'])
    assert resp == data['content']


def write_random_data(dev):
    """
    Generate random data and write it to the specified block device.
    """
    data = generate_random_data(VOLUME_RWTEST_SIZE)
    data_pos = generate_random_pos(VOLUME_RWTEST_SIZE)
    data_len = volume_write(dev, data_pos, data)

    return {
        'content': data,
        'pos': data_pos,
        'len': data_len
    }


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
