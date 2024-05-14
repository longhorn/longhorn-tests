import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


def create(name, replica_count="", migratable="", data_locality="", from_backup=""):
    filepath = "./templates/workload/storageclass.yaml"

    with open(filepath, 'r') as f:
        manifest_dict = yaml.safe_load(f)
        manifest_dict['metadata']['name'] = name
        
        if replica_count != "":
             manifest_dict['parameters']['numberOfReplicas'] = replica_count
        if migratable != "":
            manifest_dict['parameters']['migratable'] = migratable
        if data_locality != "":
            manifest_dict['parameters']['dataLocality'] = data_locality
        if from_backup != "":
            manifest_dict['parameters']['fromBackup'] = from_backup
        
        api = client.StorageV1Api()
        api.create_storage_class(body=manifest_dict)


def delete(name):
    api = client.StorageV1Api()
    try:
        api.delete_storage_class(name, grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404


def delete_all():
    api = client.StorageV1Api()
    storage_classes = api.list_storage_class()

    for item in storage_classes.items:
        if "longhorn-test" in item.metadata.name:
            delete(item.metadata.name)
