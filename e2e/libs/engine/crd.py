from kubernetes import client

from engine.base import Base
from utility.utility import logging
import utility.constant as constant


class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def get_engines(self, volume_name, node_name=None):
        if not node_name:
            logging(f"Getting all engines of {volume_name}")
        else:
            logging(f"Getting engine of volume {volume_name} on node {node_name}")

        label_selector = []
        if volume_name:
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name:
            label_selector.append(f"longhornnode={node_name}")

        api_response = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="engines",
            label_selector=",".join(label_selector)
        )

        if api_response == "" or api_response is None:
            raise Exception(f"failed to get volume {volume_name} engine")

        engines = api_response["items"]
        if len(engines) == 0:
            logging(f"Cannot get volume {volume_name} engines")

        return engines

    def delete_engine(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging("deleting all engines")
        else:
            logging(f"delete the volume {volume_name} on node {node_name} engine")

        for engine in self.get_engine(volume_name, node_name):
            engine_name = engine['metadata']['name']
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="engines",
                name=engine_name
            )
        logging("finished delete engines")

    def validate_engine_setting(self, volume_name, setting_name, value):
        engines = self.get_engines(volume_name)
        for engine in engines:
            assert str(engine["spec"][setting_name]) == value, \
            f"Expected volume {volume_name} engine setting {setting_name} is {value}, but it's {str(engine['spec'][setting_name])}"

    def get_engine_name(self, volume_name):
        logging(f"Getting volume {volume_name} engine name")
        engines = self.get_engines(volume_name)
        assert len(engines) == 1, f"Expect volume {volume_name} only has one engine, but there are {engines}"
        engine_name = engines[0]["metadata"]["name"]
        logging(f"Got volume {volume_name} engine name {engine_name}")
        return engine_name
