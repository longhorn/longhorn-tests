from utility.utility import logging
from common_keywords import common_keywords

class engine_keywords:

    def __init__(self):
        self.engine = common_keywords.engine_instance

    def get_engine_state(self, volume_name, node_name):
        logging(f"Getting the volume {volume_name} engine on the node {node_name} state")

        resp = self.engine.get_engine(volume_name, node_name)
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