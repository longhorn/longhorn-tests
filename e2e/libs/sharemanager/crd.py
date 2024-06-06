from kubernetes import client

from sharemanager.base import Base


class CRD(Base):

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def list(self, label_selector=None):
        return self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="sharemanagers",
            label_selector=label_selector
        )
