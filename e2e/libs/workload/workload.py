import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

from utility.utility import get_name_suffix
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from workload.constant import WAIT_FOR_POD_STABLE_MAX_RETRY


def create_storageclass(name):
    if name == 'longhorn-test-strict-local':
        filepath = "./templates/workload/strict_local_storageclass.yaml"
    else:
        filepath = "./templates/workload/storageclass.yaml"

    with open(filepath, 'r') as f:
        manifest_dict = yaml.safe_load(f)
        api = client.StorageV1Api()
        api.create_storage_class(body=manifest_dict)


def delete_storageclass(name):
    api = client.StorageV1Api()
    try:
        api.delete_storage_class(name, grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404


def get_workload_pod_names(workload_name):
    api = client.CoreV1Api()
    label_selector = f"app={workload_name}"
    pod_list = api.list_namespaced_pod(
        namespace="default",
        label_selector=label_selector)
    pod_names = []
    for pod in pod_list.items:
        pod_names.append(pod.metadata.name)
    return pod_names


def get_workload_pods(workload_name):
    api = client.CoreV1Api()
    label_selector = f"app={workload_name}"
    resp = api.list_namespaced_pod(
        namespace="default",
        label_selector=label_selector)
    return resp.items


def get_workload_volume_name(workload_name):
    api = client.CoreV1Api()
    pvc_name = get_workload_pvc_name(workload_name)
    pvc = api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return pvc.spec.volume_name


def get_workload_pvc_name(workload_name):
    pod = get_workload_pods(workload_name)[0]
    logging(f"Got pod {pod.metadata.name} for workload {workload_name}")
    for volume in pod.spec.volumes:
        if volume.name == 'pod-data':
            pvc_name = volume.persistent_volume_claim.claim_name
            break
    assert pvc_name
    return pvc_name


def write_pod_random_data(pod_name, size_in_mb, path="/data/random-data"):
    api = client.CoreV1Api()
    write_cmd = [
        '/bin/sh',
        '-c',
        f"dd if=/dev/urandom of={path} bs=1M count={size_in_mb} status=none;\
          md5sum {path} | awk \'{{print $1}}\'"
    ]
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_cmd, stderr=True, stdin=False, stdout=True,
        tty=False)


def keep_writing_pod_data(pod_name, size_in_mb=256, path="/data/overwritten-data"):
    api = client.CoreV1Api()
    write_cmd = [
        '/bin/sh',
        '-c',
        f"while true; do dd if=/dev/urandom of={path} bs=1M count={size_in_mb} status=none; done > /dev/null 2> /dev/null &"
    ]
    logging(f"Keep writing pod {pod_name}")
    res = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_cmd, stderr=True, stdin=False, stdout=True,
        tty=False)
    logging(f"Created process to keep writing pod {pod_name}")
    return res


def check_pod_data_checksum(pod_name, checksum, path="/data/random-data"):
    logging(f"Checking pod {pod_name} data checksum")
    api = client.CoreV1Api()
    cmd = [
        '/bin/sh',
        '-c',
        f"md5sum {path} | awk \'{{print $1}}\'"
    ]
    _checksum = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=cmd, stderr=True, stdin=False, stdout=True,
        tty=False)
    assert _checksum == checksum, \
        f"Got {path} checksum = {_checksum}\n" \
        f"Expected checksum = {checksum}"


def wait_for_workload_pod_stable(workload_name):
    stable_pod = None
    wait_for_stable_retry = 0
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        logging(f"Waiting for {workload_name} pod stable ({i}) ...")
        pods = get_workload_pods(workload_name)
        for pod in pods:
            if pod.status.phase == "Running":
                if stable_pod is None or \
                        stable_pod.status.start_time != pod.status.start_time:
                    stable_pod = pod
                    wait_for_stable_retry = 0
                    break
                else:
                    wait_for_stable_retry += 1
                    if wait_for_stable_retry == WAIT_FOR_POD_STABLE_MAX_RETRY:
                        return stable_pod
        time.sleep(retry_interval)
    assert False
