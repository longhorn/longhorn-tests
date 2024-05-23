import time
import asyncio
from kubernetes import client
from kubernetes.stream import stream

from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from workload.pod import is_pod_terminated_by_kubelet
from workload.constant import WAIT_FOR_POD_STABLE_MAX_RETRY
from workload.constant import WAIT_FOR_POD_KEPT_IN_STATE_TIME


def get_workload_pod_names(workload_name):
    pod_list = get_workload_pods(workload_name)
    pod_names = []
    for pod in pod_list:
        pod_names.append(pod.metadata.name)
    return pod_names


def get_workload_pods(workload_name, namespace="default"):
    api = client.CoreV1Api()
    label_selector = f"app={workload_name}"
    resp = api.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector)

    if not resp.items:
        logging(f"No pods found for workload {workload_name} in namespace {namespace}")
        return []

    filtered_pods = []
    for pod in resp.items:
        # https://github.com/longhorn/longhorn/issues/8550#issuecomment-2109276522
        if is_pod_terminated_by_kubelet(pod):
            logging(f"Skipping pod {pod.metadata.name} because it is terminated by kubelet")
            continue

        filtered_pods.append(pod)

    return filtered_pods


def get_workload_volume_name(workload_name):
    api = client.CoreV1Api()
    pvc_name = get_workload_pvc_name(workload_name)
    pvc = api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return pvc.spec.volume_name


def get_workload_pvc_name(workload_name):
    api = client.CoreV1Api()
    pod = get_workload_pods(workload_name)[0]
    logging(f"Got pod {pod.metadata.name} for workload {workload_name}")
    for volume in pod.spec.volumes:
        if volume.name == 'pod-data':
            pvc_name = volume.persistent_volume_claim.claim_name
            break
    assert pvc_name
    return pvc_name


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

    #TODO
    # assertion fails when the workload is a deployment
    # because the pvc doesn't have app=workload_name label
    assert len(claim_names) > 0, f"Failed to get PVC names for workload {workload_name}"
    return claim_names


def write_pod_random_data(pod_name, size_in_mb, file_name,
                          data_directory="/data", ):
    data_path = f"{data_directory}/{file_name}"
    api = client.CoreV1Api()
    write_data_cmd = [
        '/bin/sh',
        '-c',
        f"dd if=/dev/urandom of={data_path} bs=1M count={size_in_mb} status=none;\
          sync;\
          md5sum {data_path} | awk \'{{print $1}}\'"
    ]
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_data_cmd, stderr=True, stdin=False, stdout=True,
        tty=False)


def keep_writing_pod_data(pod_name, size_in_mb=256, path="/data/overwritten-data"):
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


def check_pod_data_checksum(expected_checksum, pod_name, file_name, data_directory="/data"):
    file_path = f"{data_directory}/{file_name}"
    api = client.CoreV1Api()
    cmd_get_file_checksum = [
        '/bin/sh',
        '-c',
        f"md5sum {file_path} | awk \'{{print $1}}\'"
    ]
    actual_checksum = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=cmd_get_file_checksum, stderr=True, stdin=False, stdout=True,
        tty=False)

    if actual_checksum != expected_checksum:
        message = f"Got {file_path} checksum = {actual_checksum} \
            Expected checksum = {expected_checksum}"
        logging(message)
        time.sleep(self.retry_count)
        assert False, message


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
