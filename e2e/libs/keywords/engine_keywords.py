from engine import Engine
from utility.utility import logging

class engine_keywords:

    def __init__(self):
        self.engine = Engine()

    def get_engine_instance_manager_name(self, volume_name):
        return self.engine.get_engine_instance_manager_name(volume_name)
