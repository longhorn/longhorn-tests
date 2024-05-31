from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume import Volume

from workload.deployment import create_deployment
from workload.deployment import delete_deployment
from workload.deployment import list_deployments


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

    def create_deployment(self, name, claim_name, replicaset=1):
        logging(f'Creating deployment {name}')
        create_deployment(name, claim_name, replicaset=replicaset)

    def delete_deployment(self, name):
        logging(f'Deleting deployment {name}')
        delete_deployment(name)
