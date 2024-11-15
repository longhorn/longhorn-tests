from engine import Engine


class engine_keywords:

    def __init__(self):
        self.engine = Engine()

    def get_engine_instance_manager_name(self, volume_name):
        return self.engine.get_engine_instance_manager_name(volume_name)

    def validate_engine_setting(self, volume_name, setting_name, value):
        return self.engine.validate_engine_setting(volume_name, setting_name, value)
