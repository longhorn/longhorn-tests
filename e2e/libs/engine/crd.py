import logging

from engine.base import Base
from utils.common_utils import k8s_cr_api

class CRD(Base):
    def __init__(self):
        self.cr_api = k8s_cr_api()

    def get_engine(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging.info("getting all engines")
        else:
            logging.info(
                f"getting the volume {volume_name} on node {node_name} engine")

        label_selector = []
        if volume_name != "":
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name != "":
            label_selector.append(f"longhornnode={node_name}")

        api_response = self.cr_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="engines",
            label_selector=",".join(label_selector)
        )
        return api_response

    def delete_engine(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging.info("deleting all engines")
        else:
            logging.info(
                f"delete the volume {volume_name} on node {node_name} engine")

        resp = self.get_engine(volume_name, node_name)
        assert resp != "", "failed to get engines"

        engines = resp['items']
        if len(engines) == 0:
            logging.warning("cannot find engines")
            return

        for engine in engines:
            engine_name = engine['metadata']['name']
            self.cr_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="engines",
                name=engine_name
            )
        logging.info("finished delete engines")
