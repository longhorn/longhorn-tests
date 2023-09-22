from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
import time
import yaml
import logging

RETRY_COUNTS = 150
RETRY_INTERVAL = 1
POD_WAIT_INTERVAL = 1
POD_WAIT_TIMEOUT = 240
WAIT_FOR_POD_STABLE_MAX_RETRY = 90

def get_name_suffix(*args):
    suffix = ""
    for arg in args:
        if arg:
            suffix += f"-{arg}"
    return suffix

def create_storageclass(name):
    if name == 'strict-local':
        filepath = "./templates/workload/strict_local_storageclass.yaml"
    else:
        filepath = "./templates/workload/storageclass.yaml"

    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        api = client.StorageV1Api()
        try:
            api.create_storage_class(body=manifest_dict)
        except Exception as e:
            print(f"Exception when create storageclass: {e}")

def delete_storageclass(name):
    api = client.StorageV1Api()
    try:
        api.delete_storage_class(name, grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

def create_deployment(volume_type, option):
    filepath = f"./templates/workload/deployment.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct workload name
        manifest_dict['metadata']['name'] += suffix
        manifest_dict['metadata']['labels']['app'] += suffix
        manifest_dict['spec']['selector']['matchLabels']['app'] += suffix
        manifest_dict['spec']['template']['metadata']['labels']['app'] += suffix
        # correct claim name
        manifest_dict['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] += suffix
        api = client.AppsV1Api()
        try:
            deployment = api.create_namespaced_deployment(
                namespace=namespace,
                body=manifest_dict)
            print(deployment)

            deployment_name = deployment.metadata.name
            replicas = deployment.spec.replicas

            for i in range(RETRY_COUNTS):
                deployment = api.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace)
                # deployment is none if deployment is not yet created
                if deployment is not None and \
                    deployment.status.ready_replicas == replicas:
                    break
                time.sleep(RETRY_INTERVAL)

            assert deployment.status.ready_replicas == replicas

        except Exception as e:
            print(f"Exception when create deployment: {e}")
    return deployment_name

def delete_deployment(name, namespace='default'):
    api = client.AppsV1Api()

    try:
        api.delete_namespaced_deployment(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    for i in range(RETRY_COUNTS):
        resp = api.list_namespaced_deployment(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(RETRY_INTERVAL)
    assert deleted

def create_statefulset(volume_type, option):
    filepath = "./templates/workload/statefulset.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct workload name
        manifest_dict['metadata']['name'] += suffix
        manifest_dict['spec']['selector']['matchLabels']['app'] += suffix
        manifest_dict['spec']['serviceName'] += suffix
        manifest_dict['spec']['template']['metadata']['labels']['app'] += suffix
        # correct storageclass name
        if option:
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['storageClassName'] += f"-{option}"
        # correct access mode`
        if volume_type == 'rwx':
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['accessModes'][0] = 'ReadWriteMany'
        api = client.AppsV1Api()
        try:
            statefulset = api.create_namespaced_stateful_set(
                body=manifest_dict,
                namespace=namespace)

            statefulset_name = statefulset.metadata.name
            replicas = statefulset.spec.replicas

            for i in range(RETRY_COUNTS):
                statefulset = api.read_namespaced_stateful_set(
                    name=statefulset_name,
                    namespace=namespace)
                # statefulset is none if statefulset is not yet created
                if statefulset is not None and \
                    statefulset.status.ready_replicas == replicas:
                    break
                time.sleep(RETRY_INTERVAL)

            assert statefulset.status.ready_replicas == replicas

        except Exception as e:
            print(f"Exception when create statefulset: {e}")
    return statefulset_name

def delete_statefulset(name, namespace='default'):
    api = client.AppsV1Api()

    try:
        api.delete_namespaced_stateful_set(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    for i in range(RETRY_COUNTS):
        resp = api.list_namespaced_stateful_set(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(RETRY_INTERVAL)
    assert deleted

def create_pvc(volume_type, option):
    filepath = "./templates/workload/pvc.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct pvc name
        manifest_dict['metadata']['name'] += suffix
        # correct storageclass name
        if option:
            manifest_dict['spec']['storageClassName'] += f"-{option}"
        # correct access mode`
        if volume_type == 'rwx':
            manifest_dict['spec']['accessModes'][0] = 'ReadWriteMany'
        api = client.CoreV1Api()
        try:
            pvc = api.create_namespaced_persistent_volume_claim(
                body=manifest_dict,
                namespace=namespace)
        except Exception as e:
            print(f"Exception when create pvc: {e}")
    return pvc.metadata.name

def delete_pvc(name, namespace='default'):
    api = client.CoreV1Api()
    try:
        api.delete_namespaced_persistent_volume_claim(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    for i in range(RETRY_COUNTS):
        resp = api.list_namespaced_persistent_volume_claim(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(RETRY_INTERVAL)
    assert deleted

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
    api = client.CoreV1Api()
    pod = get_workload_pods(workload_name)[0]
    print(f"pod = {pod}")
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
    logging.warn("before keep_writing_pod_data")
    res = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_cmd, stderr=True, stdin=False, stdout=True,
        tty=False)
    logging.warn("keep_writing_pod_data return")
    return res

def check_pod_data(pod_name, checksum, path="/data/random-data"):
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
    print(f"get {path} checksum = {_checksum},\
                expected checksum = {checksum}")
    assert _checksum == checksum

def wait_for_workload_pod_stable(workload_name):
    stable_pod = None
    wait_for_stable_retry = 0
    for _ in range(POD_WAIT_TIMEOUT):
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
        time.sleep(POD_WAIT_INTERVAL)
    assert False