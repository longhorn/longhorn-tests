import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging
import utility.constant as constant


class Secret():

    def __init__(self):
        self.api = client.CoreV1Api()

    def create(self, name=None):

        filepath = "./templates/secret.yaml"

        with open(filepath, 'r') as f:
            manifest_dict = yaml.safe_load(f)
            manifest_dict['metadata']['namespace'] = constant.LONGHORN_NAMESPACE
            if name:
                manifest_dict['metadata']['name'] = name
            logging(f"Creating secret {manifest_dict['metadata']['name']}")
            self.api.create_namespaced_secret(constant.LONGHORN_NAMESPACE, body=manifest_dict)

    def get_data(self, name="longhorn-crypto"):
        secret = self.api.read_namespaced_secret(name, constant.LONGHORN_NAMESPACE)
        return secret.data or {}

    def delete(self, name, namespace):
        try:
            logging(f"Deleting secret {name}")
            self.api.delete_namespaced_secret(namespace=namespace, name=name)
        except ApiException as e:
            assert e.status == 404

    def cleanup(self):
        secrets = self.api.list_secret_for_all_namespaces(label_selector="test.longhorn.io=e2e")
        for item in secrets.items:
            self.delete(item.metadata.name, item.metadata.namespace)
