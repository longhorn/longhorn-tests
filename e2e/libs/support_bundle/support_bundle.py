import time
import requests

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import get_longhorn_client

def get_support_bundle_url():
    return get_longhorn_client()._url.replace('schemas', 'supportbundles')

def create_support_bundle():
    data = {'description': 'Test', 'issueURL': ""}
    return requests.post(get_support_bundle_url(), json=data).json()

def get_support_bundle(node_id, name):
    url = get_support_bundle_url()
    resp = requests.get(f"{url}/{node_id}/{name}")
    assert resp.status_code == 200
    return resp.json()

def wait_for_support_bundle_state(state, node_id, name):
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        support_bundle = get_support_bundle(node_id, name)
        logging(f"Wait for support bundle {name} to be {state}, currently it's {support_bundle['state']} ... ({i})")
        try:
            assert support_bundle['state'] == state
            return
        except Exception:
            time.sleep(retry_interval)
    assert False, f"Failed to wait for support bundle {name} to be {state} state"


def generate_support_bundle():
    resp = create_support_bundle()
    node_id = resp['id']
    name = resp['name']
    wait_for_support_bundle_state("ReadyForDownload", node_id, name)
