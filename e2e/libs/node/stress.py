from node.utility import get_node_cpu_cores

from node.constant import LABEL_STRESS_HELPER
from node.constant import NODE_STRESS_CPU_LOAD_PERCENTAGE
from node.constant import NODE_STRESS_MEM_LOAD_PERCENTAGE
from node.constant import NODE_STRESS_MEM_VM_WORKERS
from node.constant import NODE_STRESS_TIMEOUT_SECOND

from utility.utility import logging

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.workload import get_workload_pods

from workload.constant import IMAGE_LITMUX


class Stress:
    def cleanup(self):
        for pod in get_workload_pods(LABEL_STRESS_HELPER):
            logging(f"Cleaning up stress pod {pod.metadata.name}")
            delete_pod(pod.metadata.name, pod.metadata.namespace)

    def cpu(self, node_names):
        for node_name in node_names:
            manifest = new_pod_manifest(
                image=IMAGE_LITMUX,
                command=["stress-ng"],
                args=['--cpu', str(get_node_cpu_cores(node_name)),
                      '--cpu-load', str(NODE_STRESS_CPU_LOAD_PERCENTAGE),
                      '--timeout', str(NODE_STRESS_TIMEOUT_SECOND)],
                node_name=node_name,
                labels={'app': LABEL_STRESS_HELPER}
            )

            pod_name = manifest['metadata']['name']
            logging(f"Creating cpu stress pod {pod_name} on {node_name}")
            create_pod(manifest, is_wait_for_pod_running=True)

    def memory(self, node_names):
        for node_name in node_names:
            manifest = new_pod_manifest(
                image=IMAGE_LITMUX,
                command=["stress-ng"],
                args=['--vm', str(NODE_STRESS_MEM_VM_WORKERS),
					  '--vm-bytes', f"{NODE_STRESS_MEM_LOAD_PERCENTAGE}%",
					  '--timeout', str(NODE_STRESS_TIMEOUT_SECOND)],
                node_name=node_name,
                labels={'app': LABEL_STRESS_HELPER}
            )

            pod_name = manifest['metadata']['name']
            logging(f"Creating memory stress pod {pod_name} on {node_name}")
            create_pod(manifest, is_wait_for_pod_running=True)
