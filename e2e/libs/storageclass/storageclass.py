import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging


class StorageClass():

    def __init__(self):
        self.api = client.StorageV1Api()

    def create(self, name, numberOfReplicas, migratable, dataLocality, fromBackup, nfsOptions, dataEngine):

        filepath = "./templates/workload/storageclass.yaml"

        with open(filepath, 'r') as f:
            manifest_dict = yaml.safe_load(f)
            manifest_dict['metadata']['name'] = name

            manifest_dict['parameters']['numberOfReplicas'] = numberOfReplicas
            manifest_dict['parameters']['migratable'] = migratable
            manifest_dict['parameters']['dataLocality'] = dataLocality
            manifest_dict['parameters']['fromBackup'] = fromBackup
            manifest_dict['parameters']['nfsOptions'] = nfsOptions
            manifest_dict['parameters']['dataEngine'] = dataEngine

            self.api.create_storage_class(body=manifest_dict)

    def delete(self, name):
        try:
            logging(f"Deleting storageclass {name}")
            self.api.delete_storage_class(name, grace_period_seconds=0)
        except ApiException as e:
            assert e.status == 404

    def cleanup(self):
        storage_classes = self.api.list_storage_class(label_selector="test.longhorn.io=e2e")
        for item in storage_classes.items:
            self.delete(item.metadata.name)
