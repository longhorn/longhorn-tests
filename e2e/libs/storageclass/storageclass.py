import yaml
import json

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging

class StorageClass():

    def __init__(self):
        self.api = client.StorageV1Api()

    def create(self, name, numberOfReplicas, migratable, dataLocality, fromBackup, nfsOptions, dataEngine, encrypted, secretName, secretNamespace):

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

            if encrypted == "true":
                manifest_dict['parameters']['encrypted'] = encrypted
                manifest_dict['parameters']['csi.storage.k8s.io/provisioner-secret-name'] = secretName
                manifest_dict['parameters']['csi.storage.k8s.io/provisioner-secret-namespace'] = secretNamespace
                manifest_dict['parameters']['csi.storage.k8s.io/node-publish-secret-name'] = secretName
                manifest_dict['parameters']['csi.storage.k8s.io/node-publish-secret-namespace'] = secretNamespace
                manifest_dict['parameters']['csi.storage.k8s.io/node-stage-secret-name'] = secretName
                manifest_dict['parameters']['csi.storage.k8s.io/node-stage-secret-namespace'] = secretNamespace
                manifest_dict['parameters']['csi.storage.k8s.io/node-expand-secret-name'] = secretName
                manifest_dict['parameters']['csi.storage.k8s.io/node-expand-secret-namespace'] = secretNamespace

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

    def set_storageclass_default_state(self, name, make_default=True):
        if make_default:
            logging(f"Set default annotation for storageclass {name}")
            value = "true"
        else:
            logging(f"Remove default annotation for storageclass {name}")
            value = None

        patch_body = {
            "metadata": {
                "annotations": {
                    "storageclass.kubernetes.io/is-default-class": value
                    }
                }
            }
        self.api.patch_storage_class(name=name, body=patch_body)
        self.assert_storageclass_is_default(name, is_default=make_default)

    def assert_storageclass_is_default(self, name, is_default):
        sc = self.api.read_storage_class(name)
        annotations = sc.metadata.annotations or {}
        actual = annotations.get("storageclass.kubernetes.io/is-default-class", "false")

        if is_default:
            assert actual == "true", f"StorageClass '{name}' is NOT default but expected to be."
        else:
            assert actual.lower() != "true", f"StorageClass '{name}' IS default but should not be."
