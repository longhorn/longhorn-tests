from workload.deployment import create_deployment
from workload.deployment import delete_deployment
from workload.persistentvolumeclaim import create_persistentvolumeclaim
from workload.persistentvolumeclaim import delete_persistentvolumeclaim
from workload.workload import check_pod_data_checksum
from workload.workload import create_storageclass
from workload.workload import delete_storageclass
from workload.workload import get_workload_pod_names
from workload.workload import get_workload_pvc_name
from workload.workload import get_workload_volume_name
from workload.workload import keep_writing_pod_data
from workload.workload import write_pod_random_data
from workload.workload import wait_for_workload_pod_stable


class workload_keywords:

    def __init__(self):
        pass

    def init_storageclasses(self):
        create_storageclass('longhorn-test')
        create_storageclass('longhorn-test-strict-local')

    def cleanup_storageclasses(self):
        delete_storageclass('longhorn-test')
        delete_storageclass('longhorn-test-strict-local')

    def create_deployment(self, volume_type="rwo", option=""):
        create_persistentvolumeclaim(volume_type, option)
        deployment_name = create_deployment(volume_type, option)
        return deployment_name

    def get_workload_pod_name(self, workload_name):
        return get_workload_pod_names(workload_name)[0]

    def get_workload_pvc_name(self, workload_name):
        return get_workload_pvc_name(workload_name)

    def get_workload_volume_name(self, workload_name):
        return get_workload_volume_name(workload_name)

    def keep_writing_pod_data(self, pod_name):
        return keep_writing_pod_data(pod_name)

    def write_pod_random_data(self, pod, size_in_mb):
        return write_pod_random_data(pod, size_in_mb)

    def check_pod_data_checksum(self, pod_name, checksum):
        check_pod_data_checksum(pod_name, checksum)

    def cleanup_deployments(self, deployment_names):
        for name in deployment_names:
            pvc_name = get_workload_pvc_name(name)
            delete_deployment(name)
            delete_persistentvolumeclaim(pvc_name)

    def wait_for_workload_pod_stable(self, workload_name):
        return wait_for_workload_pod_stable(workload_name)
