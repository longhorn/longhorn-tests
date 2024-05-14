import time
import subprocess
import asyncio
from kubernetes import client
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.constant import IMAGE_UBUNTU
from utility.utility import subprocess_exec_cmd
from utility.utility import logging
from utility.utility import get_retry_count_and_interval

async def restart_kubelet(node_name, downtime_in_sec=10):
    manifest = new_pod_manifest(
        image=IMAGE_UBUNTU,
        command=["/bin/bash"],
        args=["-c", f"sleep 10 && systemctl stop k3s-agent && sleep {downtime_in_sec} && systemctl start k3s-agent"],
        node_name=node_name
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    await asyncio.sleep(downtime_in_sec)

    delete_pod(pod_name)

def delete_node(node_name):
    exec_cmd = ["kubectl", "delete", "node", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def force_drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--force", "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def cordon_node(node_name):
    exec_cmd = ["kubectl", "cordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def uncordon_node(node_name):
    exec_cmd = ["kubectl", "uncordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def get_all_pods_on_node(node_name):
    api = client.CoreV1Api()
    all_pods = api.list_namespaced_pod(namespace='longhorn-system', field_selector='spec.nodeName=' + node_name)
    user_pods = [p for p in all_pods.items if (p.metadata.namespace != 'kube-system')]
    return user_pods

def wait_all_pods_evicted(node_name):
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        pods = get_all_pods_on_node(node_name)
        logging(f"Waiting for pods evicted from {node_name} ... ({i})")
        evicted = True
        for pod in pods:
            # check non DaemonSet Pods are evicted or terminating (deletionTimestamp != None)
            pod_type = pod.metadata.owner_references[0].kind
            pod_delete_timestamp = pod.metadata.deletion_timestamp

            if (pod_type != 'DaemonSet' and pod_type != 'BackingImageManager') and pod_delete_timestamp == None:
                evicted = False
                break

        if evicted:
             break

        time.sleep(retry_interval)

    assert evicted, 'failed to evict pods'
