from kubernetes.client.rest import ApiException

from node.utility import get_node_cpu_cores

from node.constant import NODE_STRESS_CPU_LOAD_PERCENTAGE
from node.constant import NODE_STRESS_MEM_LOAD_PERCENTAGE
from node.constant import NODE_STRESS_MEM_VM_WORKERS
from node.constant import NODE_STRESS_TIMEOUT_SECOND
from node.constant import STRESS_HELPER_LABEL
from node.constant import STRESS_HELPER_POD_NAME_PREFIX
from node.constant import NODE_STRESS_FS_HDD_NUM
from node.constant import NODE_STRESS_FS_LOAD_PERCENTAGE
from node.constant import NODE_STRESS_FS_OPTIONS

from utility.utility import logging

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import get_pod
from workload.pod import new_pod_manifest
from workload.workload import get_workload_pods

from workload.constant import IMAGE_LITMUX


class Stress:
    def cleanup(self):
        for pod in get_workload_pods(STRESS_HELPER_LABEL):
            logging(f"Cleaning up stress pod {pod.metadata.name}")
            delete_pod(pod.metadata.name, pod.metadata.namespace)

    def cpu(self, node_names):
        for node_name in node_names:
            pod_name = f"{STRESS_HELPER_POD_NAME_PREFIX}{node_name}"

            # If the helper pod creation is called inside of a test case loop,
            # we need to check if the pod already running.
            try:
                pod = get_pod(pod_name)
                if pod and pod.status.phase != "Running":
                    logging(f"Deleting stress pod {pod_name} in phase {pod.status.phase}")
                    delete_pod(pod_name)
                elif pod:
                    logging(f"Stress pod {pod_name} already running")
                    continue
            except ApiException as e:
                assert e.status == 404

            manifest = new_pod_manifest(
                pod_name=pod_name,
                image=IMAGE_LITMUX,
                command=["stress-ng"],
                args=['--cpu', str(get_node_cpu_cores(node_name)),
                      '--cpu-load', str(NODE_STRESS_CPU_LOAD_PERCENTAGE),
                      '--timeout', str(NODE_STRESS_TIMEOUT_SECOND)],
                node_name=node_name,
                labels={'app': STRESS_HELPER_LABEL}
            )

            pod_name = manifest['metadata']['name']
            logging(f"Creating cpu stress pod {pod_name} on {node_name}")
            create_pod(manifest, is_wait_for_pod_running=True)

    def memory(self, node_names):
        for node_name in node_names:
            pod_name = f"{STRESS_HELPER_POD_NAME_PREFIX}{node_name}"

            # If the helper pod creation is called inside of a test case loop,
            # we need to check if the pod already running.
            try:
                pod = get_pod(pod_name)
                if pod and pod.status.phase != "Running":
                    logging(f"Deleting stress pod {pod_name} in phase {pod.status.phase}")
                    delete_pod(pod_name)
                elif pod:
                    logging(f"Stress pod {pod_name} already running")
                    continue
            except ApiException as e:
                assert e.status == 404

            manifest = new_pod_manifest(
                pod_name=pod_name,
                image=IMAGE_LITMUX,
                command=["stress-ng"],
                args=['--vm', str(NODE_STRESS_MEM_VM_WORKERS),
					  '--vm-bytes', f"{NODE_STRESS_MEM_LOAD_PERCENTAGE}%",
					  '--timeout', str(NODE_STRESS_TIMEOUT_SECOND)],
                node_name=node_name,
                labels={'app': STRESS_HELPER_LABEL}
            )

            pod_name = manifest['metadata']['name']
            logging(f"Creating memory stress pod {pod_name} on {node_name}")
            create_pod(manifest, is_wait_for_pod_running=True)

    def fs(self, node_names):
        for node_name in node_names:
            pod_name = f"{STRESS_HELPER_POD_NAME_PREFIX}{node_name}"

            # If the helper pod creation is called inside of a test case loop,
            # we need to check if the pod already running.
            try:
                pod = get_pod(pod_name)
                if pod and pod.status.phase != "Running":
                    logging(f"Deleting stress pod {pod_name} in phase {pod.status.phase}")
                    delete_pod(pod_name)
                elif pod:
                    logging(f"Stress pod {pod_name} already running")
                    continue
            except ApiException as e:
                assert e.status == 404

            manifest = new_pod_manifest(
                pod_name=pod_name,
                image=IMAGE_LITMUX,
                command=["stress-ng"],
                args=['--hdd', str(NODE_STRESS_FS_HDD_NUM),
					  '--hdd-bytes', f"{NODE_STRESS_FS_LOAD_PERCENTAGE}%",
                      '--hdd-opts', f"{NODE_STRESS_FS_OPTIONS}",
					  '--timeout', str(NODE_STRESS_TIMEOUT_SECOND)],
                node_name=node_name,
                labels={'app': STRESS_HELPER_LABEL}

            )

            pod_name = manifest['metadata']['name']
            logging(f"Creating memory stress pod {pod_name} on {node_name}")
            create_pod(manifest, is_wait_for_pod_running=True)
