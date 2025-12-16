import time
import asyncio
import json

from kubernetes import client
from kubernetes.stream import stream

from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import list_namespaced_pod

from workload.constant import WAIT_FOR_POD_STABLE_MAX_RETRY
from workload.constant import WAIT_FOR_POD_KEPT_IN_STATE_TIME
from workload.constant import CNI_NETWORK_STATUS_ANNOTATION
from workload.pod import is_pod_terminated_by_kubelet
from workload.pod import wait_for_pod_status


def get_workload_pod_names(workload_name, namespace="default"):
    pod_list = get_workload_pods(workload_name, namespace)
    pod_names = []
    for pod in pod_list:
        pod_names.append(pod.metadata.name)
    return pod_names


def get_workload_pods(workload_name, namespace="default", label_selector=""):
    if label_selector == "":
        label_selector = f"app={workload_name}"

    pods = list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector)

    if len(pods) == 0:
        logging(f"No pods found for workload {workload_name} in namespace {namespace}")
        return []

    filtered_pods = []
    for pod in pods:
        # https://github.com/longhorn/longhorn/issues/8550#issuecomment-2109276522
        if is_pod_terminated_by_kubelet(pod):
            logging(f"Skipping pod {pod.metadata.name} because it is terminated by kubelet")
            continue

        filtered_pods.append(pod)

    return filtered_pods


def get_workload_volume_name(workload_name):
    api = client.CoreV1Api()
    pvc_name = get_workload_persistent_volume_claim_name(workload_name)
    pvc = api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return pvc.spec.volume_name


def get_workload_persistent_volume_claim_name(workload_name, index=0):
    return get_workload_persistent_volume_claim_names(workload_name)[int(index)]


def get_workload_persistent_volume_claim_names(workload_name, namespace="default"):
    claim_names = []
    api = client.CoreV1Api()
    label_selector = f"app={workload_name}"
    claim = api.list_namespaced_persistent_volume_claim(
        namespace=namespace,
        label_selector=label_selector
    )

    for item in claim.items:
        claim_names.append(item.metadata.name)
    claim_names.sort()

    assert len(claim_names) > 0, f"Failed to get PVC names for workload {workload_name}"
    return claim_names


def write_pod_random_data(pod_name, size_in_mb, file_name,
                          data_directory="/data", ):

    wait_for_pod_status(pod_name, "Running")

    retry_count, retry_interval = get_retry_count_and_interval()

    for attempt in range(retry_count):
        try:
            data_path = f"{data_directory}/{file_name}"
            api = client.CoreV1Api()
            write_data_cmd = [
                '/bin/sh',
                '-c',
                f"dd if=/dev/urandom of={data_path} bs=1M count={size_in_mb} status=none;\
                sync;\
                md5sum {data_path} | awk '{{print $1}}' | tr -d ' \n'"
            ]
            resp = stream(
                api.connect_get_namespaced_pod_exec, pod_name, 'default',
                command=write_data_cmd, stderr=True, stdin=False, stdout=True,
                tty=False)

            if "Input/output error" in resp or "Read-only file system" in resp:
                raise RuntimeError(f"Attempt {attempt+1}: Command failed in pod {pod_name}. Output: {resp}")

            return resp
        except Exception as e:
            logging(f"Writing random data to pod {pod_name} failed with error {e}")
            time.sleep(retry_interval)


def write_pod_large_data(pod_name, size_in_gb, file_name,
                          data_directory="/data", ):

    wait_for_pod_status(pod_name, "Running")

    retry_count, retry_interval = get_retry_count_and_interval()

    for _ in range(retry_count):
        try:
            data_path = f"{data_directory}/{file_name}"
            api = client.CoreV1Api()
            write_data_cmd = [
                '/bin/sh',
                '-c',
                f"fallocate -l {size_in_gb}G {data_path};\
                sync;\
                md5sum {data_path} | awk '{{print $1}}' | tr -d ' \n'"
            ]
            return stream(
                api.connect_get_namespaced_pod_exec, pod_name, 'default',
                command=write_data_cmd, stderr=True, stdin=False, stdout=True,
                tty=False)
        except Exception as e:
            logging(f"Writing random data to pod {pod_name} failed with error {e}")
            time.sleep(retry_interval)


def keep_writing_pod_data(pod_name, size_in_mb=256, path="/data/overwritten-data"):

    wait_for_pod_status(pod_name, "Running")

    retry_count, retry_interval = get_retry_count_and_interval()

    for _ in range(retry_count):
        try:
            api = client.CoreV1Api()
            write_cmd = [
                '/bin/sh',
                '-c',
                f"while true; do dd if=/dev/urandom of={path} bs=1M count={size_in_mb} status=none; done > /dev/null 2> /dev/null &"
            ]

            logging(f"Creating process to keep writing data to pod {pod_name}")
            res = stream(
                api.connect_get_namespaced_pod_exec, pod_name, 'default',
                command=write_cmd, stderr=True, stdin=False, stdout=True,
                tty=False)
            assert res == "", f"Failed to create process to keep writing data to pod {pod_name}"
            return
        except Exception as e:
            logging(f"Writing data to pod {pod_name} failed with error: {e}")
            time.sleep(retry_interval)

def run_commands_in_pod(pod_name, commands):
    exit_code_prefix = "EXIT_CODE:"
    api = client.CoreV1Api()
    cmd = [
        '/bin/sh',
        '-c',
        f"cd /data && {commands}; echo {exit_code_prefix}$?"
    ]

    output = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=cmd, stderr=True, stdin=False, stdout=True,
        tty=False)

    if exit_code_prefix not in output:
        raise RuntimeError(f"Failed to run commands {commands} in pod {pod_name}: {output}")
    else:
        logging(f"Ran commands {commands} in pod {pod_name} with result: {output}")

    exit_line = output.strip().splitlines()[-1]
    exit_code = int(exit_line.replace(exit_code_prefix, "").strip())
    if exit_code != 0:
        raise RuntimeError(f"Failed to run commands {commands} in pod {pod_name}: {output}")

def get_workload_pod_data_checksum(workload_name, file_name, data_directory="/data"):

    pod_name = get_workload_pod_names(workload_name)[0]

    file_path = f"{data_directory}/{file_name}"
    api = client.CoreV1Api()
    cmd_get_file_checksum = [
        '/bin/sh',
        '-c',
        f"md5sum {file_path} | awk '{{print $1}}' | tr -d ' \n'"
    ]
    actual_checksum = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=cmd_get_file_checksum, stderr=True, stdin=False, stdout=True,
        tty=False)
    return actual_checksum

def check_workload_pod_data_checksum(expected_checksum, workload_name, file_name, data_directory="/data"):

    retry_count, retry_interval = get_retry_count_and_interval()

    for _ in range(retry_count):
        try:
            pod_name = get_workload_pod_names(workload_name)[0]
            wait_for_pod_status(pod_name, "Running")

            file_path = f"{data_directory}/{file_name}"
            api = client.CoreV1Api()
            cmd_get_file_checksum = [
                '/bin/sh',
                '-c',
                f"md5sum {file_path} | awk '{{print $1}}' | tr -d ' \n'"
            ]
            actual_checksum = stream(
                api.connect_get_namespaced_pod_exec, pod_name, 'default',
                command=cmd_get_file_checksum, stderr=True, stdin=False, stdout=True,
                tty=False)

            logging(f"Checked {pod_name} file {file_name} checksum: \
                Got {file_path} checksum = {actual_checksum} Expected checksum = {expected_checksum}")

            if actual_checksum != expected_checksum:
                message = f"Checked {pod_name} file {file_name} checksum failed. \
                    Got {file_path} checksum = {actual_checksum} Expected checksum = {expected_checksum}"
                logging(message)
                time.sleep(retry_count)
                assert False, message
            return
        except Exception as e:
            logging(f"Checking pod {pod_name} data checksum failed with error: {e}")
            time.sleep(retry_interval)
    assert False, f"Checking pod {pod_name} data checksum failed"


def check_workload_pod_data_exists(workload_name, file_name, data_directory="/data"):

    logging(f"Checking if file {file_name} exists in workload {workload_name}")

    pod_name = get_workload_pod_names(workload_name)[0]
    wait_for_pod_status(pod_name, "Running")

    try:
        file_path = f"{data_directory}/{file_name}"
        api = client.CoreV1Api()
        cmd = [
            '/bin/sh',
            '-c',
            f"ls {file_path}"
        ]
        output = stream(
            api.connect_get_namespaced_pod_exec, pod_name, 'default',
            command=cmd, stderr=True, stdin=False, stdout=True,
            tty=False)

        if "No such file or directory" not in output:
            logging(f"Checked file {file_name} exists in pod {pod_name}: {output}")
            return True
        else:
            logging(f"Checked file {file_name} doesn't exist in pod {pod_name}: {output}")
            return False
    except Exception as e:
        logging(f"Checking if file {file_name} exists in pod {pod_name} failed: {e}")
        return False


def wait_for_workload_pods_running(workload_name, namespace="default"):
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        pods = get_workload_pods(workload_name, namespace=namespace)
        if len(pods) > 0:
            running_pods = []
            for pod in pods:
                if pod.status.phase == "Running":
                    running_pods.append(pod.metadata.name)
            if len(running_pods) == len(pods):
                return

        logging(f"Waiting for {workload_name} pods {running_pods} running, retry ({i}) ...")
        time.sleep(retry_interval)

    assert False, f"Timeout waiting for {workload_name} pods running"


def wait_for_workload_pods_container_creating(workload_name, namespace="default"):
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        pods = get_workload_pods(workload_name, namespace=namespace)
        if len(pods) > 0:
            for pod in pods:
                if pod.status.phase == "Pending":
                    return

        logging(f"Waiting for {workload_name} pods {[pod.metadata.name for pod in pods]} container creating, retry ({i}) ...")
        time.sleep(retry_interval)

    assert False, f"Timeout waiting for {workload_name} pods container creating"


async def wait_for_workload_pods_stable(workload_name, namespace="default"):
    stable_pods = {}
    wait_for_stable_retry = {}
    wait_for_stable_pod = []

    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        pods = get_workload_pods(workload_name, namespace=namespace)
        if len(pods) > 0:
            for pod in pods:
                pod_name = pod.metadata.name
                if pod.status.phase == "Running":
                    if pod_name not in stable_pods or \
                            stable_pods[pod_name].status.start_time != pod.status.start_time:
                        stable_pods[pod_name] = pod
                        wait_for_stable_retry[pod_name] = 0
                    else:
                        wait_for_stable_retry[pod_name] += 1

            wait_for_stable_pod = []
            for pod in pods:
                if pod.status.phase != "Running":
                    wait_for_stable_pod.append(pod.metadata.name)
                    continue

                pod_name = pod.metadata.name
                if wait_for_stable_retry[pod_name] < WAIT_FOR_POD_STABLE_MAX_RETRY:
                    wait_for_stable_pod.append(pod_name)

            if len(wait_for_stable_pod) == 0:
                return

        logging(f"Waiting for {workload_name} pods {wait_for_stable_pod} stable, retry ({i}) ...")
        await asyncio.sleep(retry_interval)

    assert False, f"Timeout waiting for {workload_name} pods {wait_for_stable_pod} stable)"


def wait_for_workload_pod_kept_in_state(workload_name, expect_state, namespace="default"):
    def count_pod_in_specifc_state_duration(count_pod_in_state_duration, pods, expect_state):
        for pod in pods:
            pod_name = pod.metadata.name
            if pod_name not in count_pod_in_state_duration:
                count_pod_in_state_duration[pod_name] = 0
            elif (expect_state == "ContainerCreating" and pod.status.phase == "Pending") or \
                ((expect_state == "Terminating" and hasattr(pod.metadata, "deletion_timestamp") and pod.status.phase == "Running")) or \
                (expect_state == "Running" and pod.status.phase == "Running"):
                count_pod_in_state_duration[pod_name] += 1
            else:
                count_pod_in_state_duration[pod_name] = 0

    retry_count, retry_interval = get_retry_count_and_interval()
    count_pod_in_state_duration = {}

    for i in range(retry_count):
        pods = get_workload_pods(workload_name, namespace=namespace)
        if len(pods) > 0:
            count_pod_in_specifc_state_duration(count_pod_in_state_duration, pods, expect_state)
            for pod in pods:
                logging(f'Waiting for workload {workload_name} pod kept in {expect_state}')
                if count_pod_in_state_duration[pod.metadata.name] > WAIT_FOR_POD_KEPT_IN_STATE_TIME:
                    logging(f'Found pod {pod.metadata.name} kept in {expect_state}')
                    return pod
        time.sleep(retry_interval)

    assert False, f"Timeout waiting for {workload_name} pod in state: {expect_state})"


def get_pod_node(pod):
    return pod.spec.node_name


def is_workload_pods_has_annotations(workload_name, annotation_key, namespace="default", label_selector=""):
    pods = get_workload_pods(workload_name, namespace=namespace, label_selector=label_selector)
    for pod in pods:
        if not (pod.metadata.annotations and annotation_key in pod.metadata.annotations):
            return False
    return True


def is_workload_pods_has_cni_interface(workload_name, interface_name, namespace="default", label_selector=""):
    """Return True if all pods for the workload have a network entry with the given interface in
    the 'k8s.v1.cni.cncf.io/network-status' annotation.

    The annotation value is expected to be a JSON array (string). If parsing fails or the
    annotation is missing / no matching interface is found for any pod, return False.
    """
    CNI_NETWORK_STATUS_ANNOTATION = 'k8s.v1.cni.cncf.io/network-status'
    pods = get_workload_pods(workload_name, namespace=namespace, label_selector=label_selector)
    for pod in pods:
        annotations = getattr(pod.metadata, 'annotations', None)
        if not annotations or CNI_NETWORK_STATUS_ANNOTATION not in annotations:
            return False

        net_status_raw = annotations.get(CNI_NETWORK_STATUS_ANNOTATION)
        try:
            networks = json.loads(net_status_raw)
        except Exception as e:
            logging(f"Failed to parse network-status for pod {pod.metadata.name}: {e}")
            return False

        found = False
        for net in networks:
            if isinstance(net, dict) and net.get('interface') == interface_name:
                found = True
                logging(f"Found CNI interface {interface_name} for pod {pod.metadata.name}")
                break

        if not found:
            return False

    return True
