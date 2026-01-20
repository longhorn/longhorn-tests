import time
import requests
import os, zipfile, tempfile, shutil

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

def generate_support_bundle(download=False):
    resp = create_support_bundle()
    node_id = resp['id']
    name = resp['name']
    wait_for_support_bundle_state("ReadyForDownload", node_id, name)

    if download is True:
        download_support_bundle(node_id, name)

def download_support_bundle(node_id, name, output_file="lh-support-bundle.zip"):
    url = get_support_bundle_url()
    download_url = f"{url}/{node_id}/{name}/download"

    logging(f"Downloading support bundle from {download_url} to {output_file} ...")

    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(output_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    logging(f"Support bundle downloaded to {output_file}")

def check_bundle_contains_host_logs(host_log_files, node_name, bundle_zip_path):
    """
    Check if all files in host_log_files exist inside node zip in support bundle.
    """
    tmp_dir = tempfile.mkdtemp(prefix="sb_extract_")
    try:
        # extract lh-support-bundle.zip
        with zipfile.ZipFile(bundle_zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
        logging(f"Extracted support bundle to {tmp_dir}")

        supportbundle_dirs = [
            d for d in os.listdir(tmp_dir)
            if d.startswith("supportbundle_") and os.path.isdir(os.path.join(tmp_dir, d))
        ]
        if not supportbundle_dirs:
            assert False, "No supportbundle_* folder found in extracted tmp dir"
        bundle_root = os.path.join(tmp_dir, supportbundle_dirs[0])

        # find nodes/<node_name>.zip
        node_zip_path = os.path.join(bundle_root, "nodes", f"{node_name}.zip")
        if not os.path.exists(node_zip_path):
            assert False, f"Node zip {node_name}.zip not found in bundle"

        # read node zip content
        with zipfile.ZipFile(node_zip_path, "r") as node_zip:
            bundle_files = [os.path.basename(f) for f in node_zip.namelist()]

        missing_files = []
        for filename in host_log_files:
            if filename not in bundle_files:
                missing_files.append(filename)
                logging(f"FAILED: {filename} not found in bundle")
            else:
                logging(f"PASSED: {filename} found in bundle")

        if missing_files:
            assert False, f"The following log files are missing in support bundle: {missing_files}"

        logging("All host log files are present in the support bundle.")
        return True
    finally:
        shutil.rmtree(tmp_dir)
