import json
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging
import utility.constant as constant


class Secret():

    def __init__(self):
        self.api = client.CoreV1Api()

    def create(self):

        filepath = "./templates/secret.yaml"

        with open(filepath, 'r') as f:
            manifest_dict = yaml.safe_load(f)
            manifest_dict['metadata']['namespace'] = constant.LONGHORN_NAMESPACE
            logging(f"Creating secret {manifest_dict['metadata']['name']}")
            self.api.create_namespaced_secret(constant.LONGHORN_NAMESPACE, body=manifest_dict)

    def create_registry_secret(self, name):
        docker_config = {"auths": {"registry.example.invalid": {
            "username": "dummy", "password": "dummy", "auth": "ZHVtbXk6ZHVtbXk="}}}
        self.api.create_namespaced_secret(constant.LONGHORN_NAMESPACE, body={
            "apiVersion": "v1", "kind": "Secret",
            "metadata": {"name": name, "labels": {"test.longhorn.io": "e2e"}},
            "type": "kubernetes.io/dockerconfigjson",
            "stringData": {".dockerconfigjson": json.dumps(docker_config)},
        })

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
