import os
import socket
import string
import time
import random
import yaml

from longhorn import from_env

from kubernetes import client
from kubernetes import config
from kubernetes import dynamic
from kubernetes.client.rest import ApiException

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from node.utility import get_node_by_index
from node.utility import list_node_names_by_role


def logging(msg, also_report=False):
    if also_report:
        logger.info(msg, also_console=True)
    else:
        logger.console(msg)


def get_retry_count_and_interval():
    retry_count = int(BuiltIn().get_variable_value("${RETRY_COUNT}"))
    retry_interval = int(BuiltIn().get_variable_value("${RETRY_INTERVAL}"))
    return retry_count, retry_interval


def generate_name(name_prefix="test-"):
    return name_prefix + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def generate_volume_name():
    return generate_name("vol-")


def init_k8s_api_client():
    if os.getenv('LONGHORN_CLIENT_URL'):
        # for develop or debug, run test in local environment
        config.load_kube_config()
        logging("Initialized out-of-cluster k8s api client")
    else:
        # for ci, run test in in-cluster environment
        config.load_incluster_config()
        logging("Initialized in-cluster k8s api client")


def wait_for_cluster_ready():
    core_api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
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
        time.sleep(retry_interval)
    assert ready, f"expect cluster's ready but it isn't {resp}"


def wait_for_all_instance_manager_running():
    longhorn_client = get_longhorn_client()
    worker_nodes = list_node_names_by_role("worker")

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        logging(f"Waiting for all instance manager running ({_}) ...")
        instance_managers = longhorn_client.list_instance_manager()
        instance_manager_map = {}
        try:
            for im in instance_managers:
                if im.currentState == "running":
                    instance_manager_map[im.nodeID] = im
            if len(instance_manager_map) == len(worker_nodes):
                break
            time.sleep(retry_interval)
        except Exception as e:
            logging(f"Getting instance manager state error: {e}")
    assert len(instance_manager_map) == len(worker_nodes), f"expect all instance managers running, instance_managers = {instance_managers}, instance_manager_map = {instance_manager_map}"


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


def wait_delete_ns(name):
    api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        ret = api.list_namespace()
        found = False
        for item in ret.items:
            if item.metadata.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(retry_interval)
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
    retry_count, retry_interval = get_retry_count_and_interval()
    if os.getenv('LONGHORN_CLIENT_URL'):
        logging(f"Initializing longhorn api client from LONGHORN_CLIENT_URL {os.getenv('LONGHORN_CLIENT_URL')}")
        # for develop or debug
        # manually expose longhorn client
        # to access longhorn manager in local environment
        longhorn_client_url = os.getenv('LONGHORN_CLIENT_URL')
        for i in range(retry_count):
            try:
                longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
                return longhorn_client
            except Exception as e:
                logging(f"Getting longhorn client error: {e}")
                time.sleep(retry_interval)
    else:
        logging(f"Initializing longhorn api client from longhorn manager")
        # for ci, run test in in-cluster environment
        # directly use longhorn manager cluster ip
        for i in range(retry_count):
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
                time.sleep(retry_interval)


def get_test_pod_running_node():
    if "NODE_NAME" in os.environ:
        return os.environ["NODE_NAME"]
    else:
        return get_node_by_index(0)


def get_test_pod_not_running_node():
    worker_nodes = list_node_names_by_role("worker")
    test_pod_running_node = get_test_pod_running_node()
    for worker_node in worker_nodes:
        if worker_node != test_pod_running_node:
            return worker_node


def get_test_case_namespace(test_name):
    return test_name.lower().replace(' ', '-')
