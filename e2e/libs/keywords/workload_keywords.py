from workload.workload import *
import logging

class workload_keywords:

    def __init__(self):
        logging.warn("initialize workload_keywords class")

    def create_deployment(self, volume_type="rwo"):
        pvc_filepath = f"./templates/workload/{volume_type}_pvc.yaml"
        deployment_filepath = f"./templates/workload/deployment_with_{volume_type}_volume.yaml"
        pvc_name = create_pvc(pvc_filepath)
        deployment_name = create_deployment(deployment_filepath)
        return deployment_name

    def create_statefulset(self, volume_type="rwo"):
        statefulset_filepath = f"./templates/workload/statefulset_with_{volume_type}_volume.yaml"
        statefulset_name = create_statefulset(statefulset_filepath)
        return statefulset_name

    def get_workload_pod_name(self, workload_name):
        return get_workload_pod_names(workload_name)[0]

    def get_workload_volume_name(self, workload_name):
        return get_workload_volume_name(workload_name)

    def keep_writing_pod_data(self, pod_name):
        return keep_writing_pod_data(pod_name)

    def write_pod_random_data(self, pod, size_in_mb):
        return write_pod_random_data(pod, size_in_mb)

    def check_pod_data(self, pod_name, checksum):
        print(f"check pod {pod_name} data with checksum {checksum}")
        check_pod_data(pod_name, checksum)

    def cleanup_deployments(self, deployment_names):
        for name in deployment_names:
            pvc_name = get_workload_pvc_name(name)
            delete_deployment(name)
            delete_pvc(pvc_name)

    def cleanup_statefulsets(self, statefulset_names):
        for name in statefulset_names:
            pvc_name = get_workload_pvc_name(name)
            delete_statefulset(name)
            delete_pvc(pvc_name)

    def wait_for_workload_pod_stable(self, workload_name):
        return wait_for_workload_pod_stable(workload_name)
