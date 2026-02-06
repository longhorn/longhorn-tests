from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume import Volume

from workload.deployment import create_deployment
from workload.deployment import delete_deployment
from workload.deployment import list_deployments
from workload.deployment import scale_deployment


class deployment_keywords:

    def __init__(self):
        self.volume = Volume()

    def cleanup_deployments(self):
        deployments = list_deployments(
            label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
        )

        logging(f'Cleaning up {len(deployments.items)} deployments')
        for deployment in deployments.items:
            self.delete_deployment(deployment.metadata.name)

    def create_deployment(self, name, claim_name, replicaset=1, enable_pvc_io_and_liveness_probe=False, block_volume=False, args=None):
        logging(f'Creating deployment {name}')
        create_deployment(name, claim_name, replicaset=replicaset, enable_pvc_io_and_liveness_probe=enable_pvc_io_and_liveness_probe, block_volume=block_volume, args=args)

    def delete_deployment(self, name):
        logging(f'Deleting deployment {name}')
        delete_deployment(name)

    def scale_deployment(self, deployment_name, replica_count):
        logging(f'Scaling deployment {deployment_name} to {replica_count}')
        return scale_deployment(deployment_name, replica_count)
