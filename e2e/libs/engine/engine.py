from engine.base import Base
from engine.crd import CRD
from strategy import LonghornOperationStrategy


class Engine(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.engine = CRD()

    def get_engine(self, volume_name, node_name):
        return self.engine.get_engine(volume_name, node_name)

    # delete engines, if input parameters are empty then will delete all
    def delete_engine(self, volume_name="", node_name=""):
        return self.engine.delete_engine(volume_name, node_name)

    def get_engine_state(self, volume_name, node_name):
        logging(f"Getting the volume {volume_name} engine on the node {node_name} state")

        resp = self.get_engine(volume_name, node_name)
        if resp == "" or resp is None:
            raise Exception(f"failed to get the volume {volume_name} engine")

        engines = resp["items"]
        if len(engines) == 0:
            logging.warning(f"cannot get the volume {volume_name} engines")
            return

        engines_states = {}
        for engine in engines:
            engine_name = engine["metadata"]["name"]
            engine_state = engine['status']['currentState']
            engines_states[engine_name] = engine_state
        return engines_states
