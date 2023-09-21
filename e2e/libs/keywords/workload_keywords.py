from workload.workload import *
import logging

class workload_keywords:

    def __init__(self):
        logging.warn("initialize workload_keywords class")

    def init_storageclasses(self):
        create_storageclass('longhorn-test')
        create_storageclass('strict-local')

    def cleanup_storageclasses(self):
        delete_storageclass('longhorn-test')
        delete_storageclass('strict-local')

    def create_deployment(self, volume_type="rwo", option=""):
        pvc_name = create_pvc(volume_type, option)
        deployment_name = create_deployment(volume_type, option)
        return deployment_name

    def create_statefulset(self, volume_type="rwo", option=""):
        statefulset_name = create_statefulset(volume_type, option)
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
