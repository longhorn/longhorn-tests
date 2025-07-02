from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume import Volume

from workload.deployment import create_deployment
from workload.deployment import delete_deployment
from workload.deployment import list_deployments
from workload.deployment import scale_deployment
from workload.deployment import schedule_deployment
from workload.deployment import set_deployment_node_affinity


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

    def create_deployment(self, name, claim_name, node_name=None, replicaset=1):
        logging(f'Creating deployment {name} with node_name = {node_name}')
        create_deployment(name, claim_name, node_name, replicaset)

    def delete_deployment(self, name):
        logging(f'Deleting deployment {name}')
        delete_deployment(name)

    def scale_deployment(self, deployment_name, replica_count):
        logging(f'Scaling deployment {deployment_name} to {replica_count}')
        return scale_deployment(deployment_name, replica_count)

    def schedule_deployment(self, deployment_name, node_name):
        return schedule_deployment(deployment_name, node_name)

    def set_deployment_node_affinity(self, deployment_name, node_name):
        return set_deployment_node_affinity(deployment_name, node_name)
