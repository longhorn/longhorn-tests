from kubernetes import config, client, dynamic
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from longhorn import from_env
import string
import random
import os
import socket
import time
import yaml
from robot.api import logger

RETRY_COUNTS = 150
RETRY_INTERVAL = 1

def logging(msg):
    logger.info(msg, also_console=True)

def generate_volume_name():
    return "vol-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))

def init_k8s_api_client():
    if os.getenv('LONGHORN_CLIENT_URL'):
        # for develop or debug, run test in local environment
        config.load_kube_config()
        logging("Initialized out-of-cluster k8s api client")
    else:
        # for ci, run test in in-cluster environment
        config.load_incluster_config()
        logging("Initialized in-cluster k8s api client")

def list_nodes():
    core_api = client.CoreV1Api()
    obj = core_api.list_node()
    nodes = []
    for item in obj.items:
        if 'node-role.kubernetes.io/control-plane' not in item.metadata.labels and \
                'node-role.kubernetes.io/master' not in item.metadata.labels:
            nodes.append(item.metadata.name)
    return sorted(nodes)

def wait_for_cluster_ready():
    core_api = client.CoreV1Api()
    for i in range(RETRY_COUNTS):
        logging(f"Waiting for cluster ready ({i}) ...")
        try:
            resp = core_api.list_node()
            ready = True
            for item in resp.items:
                for condition in item.status.conditions:
                    if condition.type == 'Ready' and condition.status != 'True':
                        ready = False
                        break
            if ready:
                break
        except Exception as e:
            logging(f"Listing nodes error: {e}")
        time.sleep(RETRY_INTERVAL)
    assert ready, f"expect cluster's ready but it isn't {resp}"

def wait_for_all_instance_manager_running():
    core_api = client.CoreV1Api()
    longhorn_client = get_longhorn_client()
    nodes = list_nodes()

    for _ in range(RETRY_COUNTS):
        logging(f"Waiting for all instance manager running ({_}) ...")
        instance_managers = longhorn_client.list_instance_manager()
        instance_manager_map = {}
        try:
            for im in instance_managers:
                if im.currentState == "running":
                    instance_manager_map[im.nodeID] = im
            if len(instance_manager_map) == len(nodes):
                break
            time.sleep(RETRY_INTERVAL)
        except Exception as e:
            logging(f"Getting instance manager state error: {e}")
    assert len(instance_manager_map) == len(nodes), f"expect all instance managers running: {instance_managers}"

def get_node(index):
    nodes = list_nodes()
    return nodes[int(index)]

def apply_cr(manifest_dict):
    dynamic_client = dynamic.DynamicClient(client.api_client.ApiClient())
    api_version = manifest_dict.get("apiVersion")
    kind = manifest_dict.get("kind")
    resource_name = manifest_dict.get("metadata").get("name")
    namespace = manifest_dict.get("metadata").get("namespace")
    crd_api = dynamic_client.resources.get(api_version=api_version, kind=kind)

    try:
        crd_api.get(namespace=namespace, name=resource_name)
        crd_api.patch(body=manifest_dict,
                      content_type="application/merge-patch+json")
        logging.info(f"{namespace}/{resource_name} patched")
    except dynamic.exceptions.NotFoundError:
        crd_api.create(body=manifest_dict, namespace=namespace)
        logging.info(f"{namespace}/{resource_name} created")

def apply_cr_from_yaml(filepath):
    with open(filepath, 'r') as f:
        manifest_dict = yaml.safe_load(f)
        apply_cr(manifest_dict)

def get_cr(group, version, namespace, plural, name):
    api = client.CustomObjectsApi()
    try:
        resp = api.get_namespaced_custom_object(group, version, namespace, plural, name)
        return resp
    except ApiException as e:
        logging(f"Getting namespaced custom object error: {e}")

def filter_cr(group, version, namespace, plural, field_selector="", label_selector=""):
    api = client.CustomObjectsApi()
    try:
        resp = api.list_namespaced_custom_object(group, version, namespace, plural, field_selector=field_selector, label_selector=label_selector)
        return resp
    except ApiException as e:
        logging(f"Listing namespaced custom object: {e}")

def wait_delete_pod(pod_uid, namespace='default'):
    api = client.CoreV1Api()
    for i in range(RETRY_COUNTS):
        ret = api.list_namespaced_pod(namespace=namespace)
        found = False
        for item in ret.items:
            if item.metadata.uid == pod_uid:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found

def wait_delete_ns(name):
    api = client.CoreV1Api()
    for i in range(RETRY_COUNTS):
        ret = api.list_namespace()
        found = False
        for item in ret.items:
            if item.metadata.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(RETRY_INTERVAL)
    assert not found

def get_mgr_ips():
    ret = client.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-manager",
        watch=False)
    mgr_ips = []
    for i in ret.items:
        mgr_ips.append(i.status.pod_ip)
    return mgr_ips

def get_longhorn_client():
    if os.getenv('LONGHORN_CLIENT_URL'):
        logging(f"Initializing longhorn api client from LONGHORN_CLIENT_URL {os.getenv('LONGHORN_CLIENT_URL')}")
        # for develop or debug
        # manually expose longhorn client
        # to access longhorn manager in local environment
        longhorn_client_url = os.getenv('LONGHORN_CLIENT_URL')
        for i in range(RETRY_COUNTS):
            try:
                longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
                return longhorn_client
            except Exception as e:
                logging(f"Getting longhorn client error: {e}")
                time.sleep(RETRY_INTERVAL)
    else:
        logging(f"Initializing longhorn api client from longhorn manager")
        # for ci, run test in in-cluster environment
        # directly use longhorn manager cluster ip
        for i in range(RETRY_COUNTS):
            try:
                config.load_incluster_config()
                ips = get_mgr_ips()
                # check if longhorn manager port is open before calling get_client
                for ip in ips:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    mgr_port_open = sock.connect_ex((ip, 9500))
                    if mgr_port_open == 0:
                        longhorn_client = from_env(url=f"http://{ip}:9500/v1/schemas")
                        return longhorn_client
            except Exception as e:
                logging(f"Getting longhorn client error: {e}")
                time.sleep(RETRY_INTERVAL)

def get_test_pod_running_node():
    if "NODE_NAME" in os.environ:
        return os.environ["NODE_NAME"]
    else:
        return get_node(0)

def get_test_pod_not_running_node():
    nodes = list_nodes()
    test_pod_running_node = get_test_pod_running_node()
    for node in nodes:
        if node != test_pod_running_node:
            return node

def get_test_case_namespace(test_name):
    return test_name.lower().replace(' ', '-')
