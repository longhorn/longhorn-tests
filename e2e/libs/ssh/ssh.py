import yaml
import os
from utility.utility import subprocess_exec_cmd


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
    return subprocess_exec_cmd(cmd)
