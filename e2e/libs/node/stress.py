from utility.utility import logging

from workload.pod import delete_pod
from workload.workload import get_workload_pods

LABEL_STRESS_HELPER = "longhorn-stress-helper"

class Stress:
    def cleanup(self):
        for pod in get_workload_pods(LABEL_STRESS_HELPER):
            logging(f"Cleaning up stress pod {pod.metadata.name}")
            delete_pod(pod.metadata.name, pod.metadata.namespace)
