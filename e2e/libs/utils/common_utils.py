import os
import requests
import warnings
import string
import random
import time
import socket
import longhorn

from utils import config_utils
from kubernetes import config, client
from kubernetes.client import Configuration
from longhorn import from_env

PORT = ":9500"
MAX_SUPPORT_BUNDLE_NUMBER = 20
RETRY_EXEC_COUNTS = 150
RETRY_INTERVAL = 1
RETRY_INTERVAL_LONG = 2

def k8s_core_api():
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    config.load_incluster_config()
    core_api = client.CoreV1Api()
    return core_api

def k8s_cr_api():
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    config.load_incluster_config()
    cr_api = client.CustomObjectsApi()
    return cr_api

def get_longhorn_api_client():
    for i in range(RETRY_EXEC_COUNTS):
        try:
            config.load_incluster_config()
            ips = get_mgr_ips()

            # check if longhorn manager port is open before calling get_client
            for ip in ips:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                mgr_port_open = sock.connect_ex((ip, 9500))

                if mgr_port_open == 0:
                    client = 'http://' + ip + PORT + '/' #get_client(ip + PORT)
                    break
            return client
        except Exception:
            time.sleep(RETRY_INTERVAL)

def get_mgr_ips():
    ret = k8s_core_api().list_pod_for_all_namespaces(
            label_selector="app=longhorn-manager",
            watch=False)
    mgr_ips = []
    for i in ret.items:
        mgr_ips.append(i.status.pod_ip)
    return mgr_ips

def get_client(address):
    url = 'http://' + address + '/v1/schemas'
    c = longhorn.from_env(url=url)
    return c

def generate_volume_name():
    return "vol-" + \
        ''.join(random.choice(string.ascii_lowercase + string.digits)
                for _ in range(6))

def get_longhorn_client():
    # manually expose longhorn client node port
    # otherwise the test is needed to be run in in-cluster environment
    # to access longhorn manager cluster ip
    longhorn_client_url =   get_longhorn_api_client()
    longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
    return longhorn_client

def get_support_bundle_url():
    client = get_longhorn_client()
    return client._url.replace('schemas', 'supportbundles')

def generate_support_bundle(case_name):  # NOQA
    """
        Generate support bundle into folder ./support_bundle/case_name.zip

        Won't generate support bundle if current support bundle count
        greate than MAX_SUPPORT_BUNDLE_NUMBER.
        Args:
            case_name: support bundle will named case_name.zip
    """
    os.makedirs("support_bundle", exist_ok=True)
    file_cnt = len(os.listdir("support_bundle"))

    if file_cnt >= MAX_SUPPORT_BUNDLE_NUMBER:
        warnings.warn("Ignoring the bundle download because of \
                            avoiding overwhelming the disk usage.")
        return

    url = get_support_bundle_url()
    data = {'description': case_name, 'issueURL': case_name}
    try:
        res_raw = requests.post(url, json=data)
        res_raw.raise_for_status()
        res = res_raw.json()
    except Exception as e:
        warnings.warn(f"Error while generating support bundle: {e}")
        return
    id = res['data'][0]['id']
    name = res['data'][0]['name']

    support_bundle_url = '{}/{}/{}'.format(url, id, name)
    for i in range(RETRY_EXEC_COUNTS):
        res = requests.get(support_bundle_url).json()

        if res['progressPercentage'] == 100:
            break
        else:
            time.sleep(RETRY_INTERVAL_LONG)

    if res['progressPercentage'] != 100:
        warnings.warn(
            "Timeout to wait support bundle ready, skip download")
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
