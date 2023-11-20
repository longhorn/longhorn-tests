from workload.deployment import create_deployment
from workload.deployment import delete_deployment
from workload.persistentvolumeclaim import create_persistentvolumeclaim
from workload.persistentvolumeclaim import delete_persistentvolumeclaim
from workload.workload import get_workload_pvc_name


class deployment_keywords:

    def __init__(self):
        pass

    def cleanup_deployments(self, deployment_names):
        for name in deployment_names:
            pvc_name = get_workload_pvc_name(name)
            delete_deployment(name)
            delete_persistentvolumeclaim(pvc_name)

    def create_deployment(self, volume_type="rwo", option=""):
        create_persistentvolumeclaim(volume_type, option)
        deployment_name = create_deployment(volume_type, option)
        return deployment_name
