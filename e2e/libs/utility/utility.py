import os
import socket
import string
import time
import random
import yaml
import signal
import subprocess
import shlex
import json
import utility.constant
from datetime import datetime, timedelta, timezone

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from longhorn import from_env

from kubernetes import client
from kubernetes import config
from kubernetes import dynamic
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException

from utility.constant import NAME_PREFIX
from utility.constant import STREAM_EXEC_TIMEOUT
from utility.constant import STORAGECLASS_NAME_PREFIX
from utility.constant import DEFAULT_BACKUPSTORE


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


def set_longhorn_namespace(ns):
    utility.constant.LONGHORN_NAMESPACE = ns


def get_longhorn_namespace():
    return utility.constant.LONGHORN_NAMESPACE


def logging(msg, also_report=False):
    if also_report:
        logger.info(msg, also_console=True)
    else:
        logger.console(msg)


def get_retry_count_and_interval():
    retry_count = int(BuiltIn().get_variable_value("${RETRY_COUNT}"))
    retry_interval = int(BuiltIn().get_variable_value("${RETRY_INTERVAL}"))
    return retry_count, retry_interval


def generate_random_id(num_bytes):
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(num_bytes))


def generate_name_random(name_prefix="test-"):
    return name_prefix + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))


def is_integer(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def generate_name_with_suffix(kind, suffix):
    if not is_integer(suffix):
        return suffix
    else:
        if kind == "storageclass":
            return f"{STORAGECLASS_NAME_PREFIX}-{suffix}"
        else:
            return f"{NAME_PREFIX}-{kind}-{suffix}"


def init_k8s_api_client():
    if os.getenv('LONGHORN_CLIENT_URL'):
        # for develop or debug, run test in local environment
        config.load_kube_config()
        logging("Initialized out-of-cluster k8s api client")
    else:
        # for ci, run test in in-cluster environment
        config.load_incluster_config()
        logging("Initialized in-cluster k8s api client")


def get_backupstore():
    return os.environ.get('LONGHORN_BACKUPSTORE', DEFAULT_BACKUPSTORE)


def subprocess_exec_cmd(cmd, input=None, timeout=None, verbose=True):
    if verbose:
        logging(f"Executing command {cmd}")

    if isinstance(cmd, str):
        try:
            res = subprocess.check_output(cmd, input=input, timeout=timeout, shell=True, text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            res = e.output
    elif isinstance(cmd, list):
        try:
            res = subprocess.check_output(cmd, input=input, timeout=timeout, text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            res = e.output
    else:
        raise ValueError("Command must be a string or list")

    if verbose:
        logging(f"Executed command {cmd} with result {res}")
    return res


def wait_for_cluster_ready():
    core_api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
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

        logging(f"Waiting for cluster ready ({i}) ...")
        time.sleep(retry_interval)
    assert ready, f"expect cluster's ready but it isn't {resp}"


def pod_exec(pod_name, namespace, cmd):

    core_api = client.CoreV1Api()
    exec_cmd = ['/bin/sh', '-c', cmd]
    logging(f"Issued command: {cmd} on {pod_name}")

    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message=f'Timeout on executing stream {pod_name} {cmd}'):
        output = stream(core_api.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace, command=exec_cmd,
                        stderr=True, stdin=False, stdout=True, tty=False)
        logging(f"Issued command: {cmd} on {pod_name} with result {output}")
        return output


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
    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        try:
            resp = api.get_namespaced_custom_object(group, version, namespace, plural, name)
            return resp
        except ApiException as e:
            logging(f"Getting namespaced custom object error: {e}")
        time.sleep(retry_interval)
    assert False, "Getting namespaced custom object error"


def get_all_crs(group, version, namespace, plural):
    api = client.CustomObjectsApi()
    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        try:
            resp = api.list_namespaced_custom_object(group, version, namespace, plural)
            return resp
        except ApiException as e:
            logging(f"Getting namespaced custom object error: {e}")
        time.sleep(retry_interval)
    assert False, "Getting namespaced custom object error"


def filter_cr(group, version, namespace, plural, field_selector="", label_selector=""):
    api = client.CustomObjectsApi()
    try:
        resp = api.list_namespaced_custom_object(group, version, namespace, plural, field_selector=field_selector, label_selector=label_selector)
        return resp
    except ApiException as e:
        logging(f"Listing namespaced custom object: {e}")


def list_namespaced_pod(namespace, label_selector=""):
    api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        try:
            resp = api.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector)
            return resp.items
        except Exception as e:
            logging(f"Failed to list namespaced {namespace} pods with error: {e}")
        time.sleep(retry_interval)
    assert False, f"Failed to list namespaced {namespace} pods"


def set_annotation(group, version, namespace, plural, name, annotation_key, annotation_value):
    api = client.CustomObjectsApi()
    # retry conflict error
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        logging(f"Try to set custom resource {plural} {name} annotation {annotation_key}={annotation_value} ... ({i})")
        try:
            cr = get_cr(group, version, namespace, plural, name)
            annotations = cr['metadata'].get('annotations', {})
            annotations[annotation_key] = f"{annotation_value}"
            cr['metadata']['annotations'] = annotations
            api.replace_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=name,
                body=cr
            )
            break
        except Exception as e:
            if e.status == 409:
                logging(f"Conflict error: {e.body}, retry ({i}) ...")
            else:
                raise e
        time.sleep(retry_interval)


def get_annotation_value(group, version, namespace, plural, name, annotation_key):
    try:
        cr = get_cr(group, version, namespace, plural, name)
        return cr['metadata']['annotations'].get(annotation_key)
    except Exception as e:
        logging(f"Failed to get annotation {annotation_key} from {plural} {name} in {namespace}: {e}")
        return ""


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


def delete_pod(name, namespace='default'):
    core_api = client.CoreV1Api()
    try:
        core_api.delete_namespaced_pod(name=name, namespace=namespace, grace_period_seconds=0)
        wait_delete_pod(name, namespace)
    except ApiException as e:
        assert e.status == 404


def wait_delete_pod(name, namespace='default'):
    api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        ret = api.list_namespaced_pod(namespace=namespace)
        found = False
        for item in ret.items:
            if item.metadata.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(retry_interval)
    assert not found


def get_pod(name, namespace='default'):
    try:
        core_api = client.CoreV1Api()
        return core_api.read_namespaced_pod(name=name, namespace=namespace)
    except Exception as e:
        if isinstance(e, ApiException) and e.reason == 'Not Found':
            return None
        raise e


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
        # for develop or debug
        # manually expose longhorn client
        # to access longhorn manager in local environment
        longhorn_client_url = os.getenv('LONGHORN_CLIENT_URL')
        for i in range(retry_count):
            try:
                longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
                return longhorn_client
            except Exception as e:
                logging(f"Getting longhorn client error: {e}, retry ({i}) ...")
                time.sleep(retry_interval)
    else:
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
                logging(f"Getting longhorn client error: {e}, retry ({i}) ...")
                time.sleep(retry_interval)


def get_test_case_namespace(test_name):
    return test_name.lower().replace(' ', '-')


def get_name_suffix(*args):
    suffix = ""
    for arg in args:
        if arg:
            suffix += f"-{arg}"
    return suffix


def convert_size_to_bytes(size):
    size = size.replace(" ", "")

    if size.endswith(("GiB", "Gi")):
        return int(size.rstrip("GiB").rstrip("Gi")) * 1024 * 1024 * 1024

    if size.endswith(("MiB", "Mi")):
        return int(size.rstrip("MiB").rstrip("Mi")) * 1024 * 1024

    if size.isdigit():
        return int(size)

    raise ValueError(f"Invalid size format: {size}")


def is_json_object(s):
    parsed = json.loads(s)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError(f"input {s} is not a valid json object")


def get_cron_after(minutes):
    future = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return f"{future.minute} {future.hour} * * *"
