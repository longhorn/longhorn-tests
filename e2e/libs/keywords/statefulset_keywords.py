from workload.persistentvolumeclaim import delete_persistentvolumeclaim
from workload.statefulset import create_statefulset
from workload.statefulset import delete_statefulset
from workload.statefulset import get_statefulset
from workload.statefulset import scale_statefulset
from workload.statefulset import wait_for_statefulset_replicas_ready
from workload.workload import get_workload_pvc_name



class statefulset_keywords:

    def __init__(self):
        pass

    def cleanup_statefulsets(self, statefulset_names):
        for name in statefulset_names:
            pvc_name = get_workload_pvc_name(name)
            delete_statefulset(name)
            delete_persistentvolumeclaim(pvc_name)

    def create_statefulset(self, volume_type="rwo", option=""):
        statefulset_name = create_statefulset(volume_type, option)
        return statefulset_name

    def get_statefulset(self, statefulset_name):
        return get_statefulset(statefulset_name)

    def scale_statefulset(self, statefulset_name, replica_count):
        return scale_statefulset(statefulset_name, replica_count)

    def wait_for_statefulset_replicas_ready(self, statefulset_name, expected_ready_count):
        return wait_for_statefulset_replicas_ready(statefulset_name, expected_ready_count)
