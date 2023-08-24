from kubernetes import config, client
from longhorn import from_env
import string
import random
import os
import socket
import time

RETRY_COUNTS = 150
RETRY_INTERVAL = 1

class Utility:

    def generate_volume_name(cls):
        return "vol-" + \
            ''.join(random.choice(string.ascii_lowercase + string.digits)
                    for _ in range(6))

    def init_k8s_api_client(cls):
        print('init_k8s_api_client')
        if os.getenv('LONGHORN_CLIENT_URL'):
            # for develop or debug, run test in local environment
            config.load_kube_config()
        else:
            # for ci, run test in in-cluster environment
            config.load_incluster_config()

    def get_mgr_ips(cls):
        ret = client.CoreV1Api().list_pod_for_all_namespaces(
            label_selector="app=longhorn-manager",
            watch=False)
        mgr_ips = []
        for i in ret.items:
            mgr_ips.append(i.status.pod_ip)
        return mgr_ips

    def get_longhorn_client(cls):
        print('get_longhorn_client')
        if os.getenv('LONGHORN_CLIENT_URL'):
            # for develop or debug
            # manually expose longhorn client
            # to access longhorn manager in local environment
            longhorn_client_url = os.getenv('LONGHORN_CLIENT_URL')
            longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
            return longhorn_client
        else:
            # for ci, run test in in-cluster environment
            # directly use longhorn manager cluster ip
            for i in range(RETRY_COUNTS):
                try:
                    config.load_incluster_config()
                    ips = cls.get_mgr_ips()
                    # check if longhorn manager port is open before calling get_client
                    for ip in ips:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        mgr_port_open = sock.connect_ex((ip, 9500))
                        if mgr_port_open == 0:
                            longhorn_client = from_env(url=f"http://{ip}:9500/v1/schemas")
                            return longhorn_client
                except Exception as e:
                    print(f"get longhorn client error: {e}")
                    time.sleep(RETRY_INTERVAL)
