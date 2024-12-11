from engine.base import Base
from engine.crd import CRD

from strategy import LonghornOperationStrategy

from utility.utility import logging


class Engine(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.engine = CRD()

    def get_engines(self, volume_name, node_name=None):
        return self.engine.get_engines(volume_name, node_name)

    def get_engine(self, volume_name):
        engines = self.get_engines(volume_name)
        assert len(engines) == 1, \
            f"Expected exactly one engine but found {len(engines)}"

        return engines[0]
        
    def get_engine_instance_manager_name(self, volume_name):
        engine = self.get_engine(volume_name)
        return engine['status']['instanceManagerName']

    # delete engines, if input parameters are empty then will delete all
    def delete_engine(self, volume_name="", node_name=""):
        return self.engine.delete_engine(volume_name, node_name)

    def get_engine_state(self, volume_name, node_name):
        logging(f"Getting the volume {volume_name} engine on the node {node_name} state")

        engines_states = {}
        for engine in self.engine.get_engine(volume_name, node_name):
            engine_name = engine["metadata"]["name"]
            engine_state = engine['status']['currentState']
            engines_states[engine_name] = engine_state
        return engines_states

    def get_engine_name(self, volume_name):
        return self.engine.get_engine_name(volume_name)

    def validate_engine_setting(self, volume_name, setting_name, value):
        return self.engine.validate_engine_setting(volume_name, setting_name, value)
