import yaml
import os
from utility.utility import subprocess_exec_cmd
from utility.utility import logging
from utility.utility import get_retry_count_and_interval


def ssh_exec(node_name, cmd):

    distro = os.environ.get("DISTRO", "sles")
    host_provider = os.environ.get("HOST_PROVIDER", "aws")
    if distro in ["ubuntu"] or host_provider == "harvester":
        username = distro
    else:
        username = "ec2-user"

    with open('/tmp/public_ip_mapping', 'r') as f:
        mapping = yaml.safe_load(f)
    ip = mapping[node_name]

    cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{ip} {cmd}"

    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        try:
            res = subprocess_exec_cmd(cmd)
            return res
        except Exception as e:
            logging(f"SSH command {cmd} on node {node_name} failed: {e} ... ({i})")
            time.sleep(retry_interval)
    assert False, f"Failed to SSH command {cmd} on node {node_name}"
