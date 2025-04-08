import time
import asyncio

from kubernetes import client
from kubernetes.client.rest import ApiException

from robot.libraries.BuiltIn import BuiltIn

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd
from utility.utility import subprocess_exec_cmd_with_timeout
from utility.constant import LONGHORN_UNINSTALL_TIMEOUT

from workload.constant import IMAGE_UBUNTU
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest


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

def get_longhorn_node_condition_status(node_name, type):
    jsonpath = f"jsonpath={{.status.conditions[?(@.type=='{type}')].status}}"
    exec_cmd = [
        "kubectl", "-n", "longhorn-system", "get",
        "nodes.longhorn.io", node_name, "-o", jsonpath]
    return subprocess_exec_cmd(exec_cmd).decode('utf-8')

def delete_node(node_name):
    exec_cmd = ["kubectl", "delete", "node", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def force_drain_node(node_name, timeout):
    exec_cmd = ["kubectl", "drain", node_name, "--force", "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd_with_timeout(exec_cmd, timeout)

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

def is_node_ready(node_name):
    api = client.CoreV1Api()
    node = api.read_node(node_name)
    conditions = node.status.conditions
    for condition in conditions:
        if condition.type == "Ready" and condition.status == "True":
            return True
    return False

def check_node_cordoned(node_name):
    api = client.CoreV1Api()
    node = api.read_node(node_name)
    assert node.spec.unschedulable is True, f"node {node_name} is not cordoned."

def get_instance_manager_on_node(node_name):
    data_engine = BuiltIn().get_variable_value("${DATA_ENGINE}")
    pods = get_all_pods_on_node(node_name)
    for pod in pods:
        labels = pod.metadata.labels
        if labels.get("longhorn.io/data-engine") == data_engine and \
           labels.get("longhorn.io/component") == "instance-manager":
            return pod.metadata.name
    return None

def check_instance_manager_pdb_not_exist(instance_manager):
    exec_cmd = ["kubectl", "get", "pdb", "-n", "longhorn-system"]
    res = subprocess_exec_cmd(exec_cmd)
    assert instance_manager not in res.decode('utf-8')

def wait_namespaced_job_complete(job_label, namespace):
    retry_count, retry_interval = get_retry_count_and_interval()
    api = client.BatchV1Api()
    for i in range(LONGHORN_UNINSTALL_TIMEOUT):
        target_job = api.list_namespaced_job(namespace=namespace, label_selector=job_label)
        if len(target_job.items) > 0:
            running_jobs = []
            for job in target_job.items:
                conditions = job.status.conditions
                if conditions:
                    for condition in conditions:
                        logging(f"{condition.type}  {condition.status}")
                        if condition.type == "Complete" and condition.status == "True":
                            logging(f"Job {job.metadata.name} is complete.")
                            running_jobs.append(job)
                            break
            if len(running_jobs) == len(target_job.items):
                logging(f"Job is complete: {get_pod_logs(namespace, job_label)}")
                return

        logging(f"Waiting for job with label {job_label} complete, retry ({i}) ...")
        time.sleep(retry_interval)

    assert False, f"Job not complete: {get_pod_logs(namespace, job_label)}"

def wait_namespace_terminated(namespace):
    retry_count, retry_interval = get_retry_count_and_interval()
    api = client.CoreV1Api()
    for i in range(retry_count):
        try:
            target_namespace = api.read_namespace(name=namespace)
            target_namespace_status = target_namespace.status.phase
            logging(f"Waiting for namespace {target_namespace.metadata.name} terminated, current status is {target_namespace_status} retry ({i}) ...")
        except ApiException as e:
            if e.status == 404:
                logging(f"Namespace {namespace} successfully terminated.")
                return
            else:
                logging(f"Error while fetching namespace {namespace} status: {e}")

        time.sleep(retry_interval)

    assert False, f'namespace {target_namespace.metadata.name} not terminated'

def get_all_custom_resources():
    api = client.ApiextensionsV1Api()
    crds = api.list_custom_resource_definition()

    return crds

def get_pod_logs(namespace, pod_label):
    api = client.CoreV1Api()
    logs= ""
    try:
        pods = api.list_namespaced_pod(namespace, label_selector=pod_label)
        for pod in pods.items:
            pod_name = pod.metadata.name
            logs = logs + api.read_namespaced_pod_log(name=pod_name, namespace=namespace)
    except client.exceptions.ApiException as e:
        logging(f"Exception when calling CoreV1Api: {e}")

    return logs

def list_namespace_pods(namespace):
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace=namespace)

    return pods

def delete_namespace(namespace):
    api = client.CoreV1Api()
    try:
        api.delete_namespace(name=namespace)
    except ApiException as e:
        assert e.status == 404

def wait_for_namespace_pods_running(namespace):    
    retry_count, retry_interval = get_retry_count_and_interval()

    for i in range(retry_count):        
        time.sleep(retry_interval)
        pod_list = list_namespace_pods(namespace)        
        all_running = True

        for pod in pod_list.items:
            pod_name = pod.metadata.name
            pod_status = pod.status.phase

            if pod_status != "Running":
                logging(f"Pod {pod_name} is in {pod_status} state, waiting...")
                all_running = False

        if all_running:
            logging(f"All pods in namespace {namespace} are in Running state!")
            return

    assert False, f"wait all pod in namespace {namespace} running failed"
