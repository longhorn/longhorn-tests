import json
import os
import boto3

from utility.utility import subprocess_exec_cmd
from utility.utility import logging
from utility.utility import get_retry_count_and_interval

def get_public_ip(node_name):
    host_provider = os.environ.get("HOST_PROVIDER", "aws")
    if host_provider == "aws":
        with open('/tmp/instance_mapping', 'r') as f:
            instance_mapping = json.load(f)
        instance_id = instance_mapping[node_name]
        ec2 = boto3.client('ec2')
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        instance = resp['Reservations'][0]['Instances'][0]
        if instance.get('PublicIpAddress'):
            return instance['PublicIpAddress']
        for iface in instance.get('NetworkInterfaces', []):
            for ipv6 in iface.get('Ipv6Addresses', []):
                return f"[{ipv6['Ipv6Address']}]"
    elif host_provider == "harvester":
        result = json.loads(subprocess_exec_cmd(["kubectl", "get", "nodes", "-o", "json"]))
        for node in result['items']:
            provider_id = node['spec'].get('providerID', '')
            key = provider_id.split('/')[-1] if provider_id else node['metadata']['name']
            if key == node_name:
                for addr in node['status']['addresses']:
                    if addr['type'] == 'InternalIP':
                        return addr['address']
    raise Exception(f"Cannot determine public IP for node {node_name} with HOST_PROVIDER={host_provider!r}")


def ssh_exec(node_name, cmd):

    distro = os.environ.get("DISTRO", "sles")
    host_provider = os.environ.get("HOST_PROVIDER", "aws")
    if distro in ["ubuntu"] or host_provider == "harvester":
        username = distro
    else:
        username = "ec2-user"

    ip = get_public_ip(node_name)

    cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{ip} {cmd}"

    try:
        res = subprocess_exec_cmd(cmd)
        return res
    except Exception as e:
        output = getattr(e, 'output', None)
        logging(f"SSH command {cmd} on node {node_name} failed: {e}, output: {output}")
        raise Exception(f"SSH command {cmd} on node {node_name} failed: {e}, output: {output}")
