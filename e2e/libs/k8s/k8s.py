import time
import asyncio
import os
import json
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from robot.libraries.BuiltIn import BuiltIn

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd
from utility.constant import LONGHORN_UNINSTALL_TIMEOUT
from utility.constant import DRAIN_TIMEOUT
import utility.constant as constant

from node import Node

from workload.constant import IMAGE_UBUNTU
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest

from datetime import datetime, timezone

async def restart_kubelet(node_name, downtime_in_sec=10):
    k8s_distro = os.environ.get("K8S_DISTRO", "k3s")
    node_type = "control-plane" if node_name in Node().list_node_names_by_role("control-plane") else "worker"
    if k8s_distro == "k3s":
        service_name = "k3s-agent" if node_type == "worker" else "k3s"
    elif k8s_distro == "rke2":
        service_name = "rke2-agent" if node_type == "worker" else "rke2-server"

    manifest = new_pod_manifest(
        image=IMAGE_UBUNTU,
        command=["/bin/bash"],
        args=["-c", f"sleep 10 && systemctl stop {service_name} && sleep {downtime_in_sec} && systemctl start {service_name}"],
        node_name=node_name
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    await asyncio.sleep(downtime_in_sec)

    delete_pod(pod_name)

def get_longhorn_node_condition_status(node_name, type):
    jsonpath = f"jsonpath={{.status.conditions[?(@.type=='{type}')].status}}"
    exec_cmd = [
        "kubectl", "-n", constant.LONGHORN_NAMESPACE, "get",
        "nodes.longhorn.io", node_name, "-o", jsonpath]
    return subprocess_exec_cmd(exec_cmd)

def delete_node(node_name):
    exec_cmd = ["kubectl", "delete", "node", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def set_k8s_node_zone(node_name, zone_name=""):
    if zone_name:
        logging(f"Setting node {node_name} zone to {zone_name}")
        exec_cmd = ["kubectl", "label", "node", node_name, f"topology.kubernetes.io/zone={zone_name}", "--overwrite"]
        res = subprocess_exec_cmd(exec_cmd)
    else:
        logging(f"Resetting node {node_name} zone")
        exec_cmd = ["kubectl", "label", "node", node_name, f"topology.kubernetes.io/zone-", "--overwrite"]
        res = subprocess_exec_cmd(exec_cmd)

def drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def force_drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--force", "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd, timeout=DRAIN_TIMEOUT)

def cordon_node(node_name):
    exec_cmd = ["kubectl", "cordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def uncordon_node(node_name):
    exec_cmd = ["kubectl", "uncordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def get_all_pods_on_node(node_name):
    api = client.CoreV1Api()
    all_pods = api.list_namespaced_pod(namespace=constant.LONGHORN_NAMESPACE, field_selector='spec.nodeName=' + node_name)
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
    exec_cmd = ["kubectl", "get", "pdb", "-n", constant.LONGHORN_NAMESPACE]
    res = subprocess_exec_cmd(exec_cmd)
    assert instance_manager not in res

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

def get_latest_pod_logs(namespace, pod_label):
    api = client.CoreV1Api()
    try:
        pods = api.list_namespaced_pod(namespace, label_selector=pod_label)
        latest_pod = max(pods.items, key=lambda pod: pod.status.start_time)
        logs = api.read_namespaced_pod_log(name=latest_pod.metadata.name, namespace=namespace)
        return logs
    except client.exceptions.ApiException as e:
        logging(f"Exception when calling CoreV1Api: {e}")

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

def verify_pod_log_after_time_contains(pod_name, expect_log, test_start_time, namespace):
    # Convert test_start_time to UTC and format it for kubectl --since-time use
    test_start_time = test_start_time.astimezone(timezone.utc)
    test_start_time = test_start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    exec_cmd = [
        "kubectl", "logs", pod_name,
        "-n", namespace,
        f"--since-time={test_start_time}"
    ]

    pod_log = subprocess_exec_cmd(exec_cmd)
    logging(f"logs in pod {pod_name} after {test_start_time}:\n {pod_log}")

    assert expect_log in pod_log, f"Expected log '{expect_log}' was not found in pod '{pod_name}' logs"
def deploy_system_upgrade_controller():
    logging(f"Deploying system upgrade controller")
    cmd = "kubectl apply -f https://github.com/rancher/system-upgrade-controller/releases/latest/download/crd.yaml -f https://raw.githubusercontent.com/yangchiu/longhorn-tests/refs/heads/k8s-upgrade-test/e2e/templates/system_upgrade_controller/system_upgrade_controller.yaml"
    subprocess_exec_cmd(cmd)

def upgrade_k8s_to_latest_version(drain=False):
    logging(f"Upgrading K8s to latest version")
    k8s_distro = os.environ.get("K8S_DISTRO", "k3s")

    filepath = "./templates/system_upgrade_controller/k8s_upgrade_plan.yaml"
    with open(filepath, 'r') as f:
        yaml_content = f.read()

    yaml_content = yaml_content.replace("k3s", k8s_distro)
    if drain:
        yaml_docs = list(yaml.safe_load_all(yaml_content))
        yaml_docs[1]["spec"]["drain"] = {
            "force": True,
            "disableEviction": True
        }
        yaml_content = yaml.safe_dump_all(yaml_docs, sort_keys=False)

    logging(yaml_content)

    cmd = f"kubectl apply -f -"
    subprocess_exec_cmd(cmd, input=yaml_content)

    wait_for_k8s_upgrade_completed()

def wait_for_k8s_upgrade_completed():
    retry_count, retry_interval = get_retry_count_and_interval()

    cmd = "kubectl -n system-upgrade get plan server-plan -ojson"
    completed = False
    for i in range(retry_count):
        logging(f"Waiting for k8s upgrade server plan completed ... ({i})")
        try:
            plan = json.loads(subprocess_exec_cmd(cmd, verbose=False))
            plan_conditions = plan.get("status", {}).get("conditions", {})
            for condition in plan_conditions:
                if condition.get("type") == "Complete" and condition.get("status") == "True":
                    completed = True
                    break
        except Exception as e:
            logging(f"Waiting for k8s upgrade server plan completed error: {e}")
        if completed:
            break
        time.sleep(retry_interval)

    if not completed:
        logging(f"Failed to wait for k8s upgrade server plan completed")
        time.sleep(retry_count)
    assert completed, f"Failed to wait for k8s upgrade server plan completed"

    cmd = "kubectl -n system-upgrade get plan agent-plan -ojson"
    completed = False
    for i in range(retry_count):
        logging(f"Waiting for k8s upgrade agent plan completed ... ({i})")
        try:
            plan = json.loads(subprocess_exec_cmd(cmd, verbose=False))
            plan_conditions = plan.get("status", {}).get("conditions", {})
            for condition in plan_conditions:
                if condition.get("type") == "Complete" and condition.get("status") == "True":
                    completed = True
                    break
        except Exception as e:
            logging(f"Waiting for k8s upgrade agent plan completed error: {e}")
        if completed:
            break
        time.sleep(retry_interval)

    if not completed:
        logging(f"Failed to wait for k8s upgrade agent plan completed")
        time.sleep(retry_count)
    assert completed, f"Failed to wait for k8s upgrade agent plan completed"
