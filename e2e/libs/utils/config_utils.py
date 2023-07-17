import configparser
import logging

CONFIG_FILE_PATH = 'settings.ini'

class Config(object):

    _config = {}

    def __init__(self) -> None:
        self.initialize_variables()

    @classmethod
    def get(cls, config_name):
        if config_name not in cls._config.keys():
            return None
        return cls._config[config_name]

    @classmethod
    def initialize_variables(cls):
        logging.info("initiate environment variables")

        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH, encoding='utf-8')
        section_name = 'DEFAULT'
        if 'CUSTOM' in config.sections():
            section_name = 'CUSTOM'

        cls._config = {
            "CLOUD_PROVIDER": config[section_name]["CLOUD_PROVIDER"],
            "K8S_DISTRO": config[section_name]["K8S_DISTRO"],
            "LONGHORN_CLIENT_URL": config[section_name]["LONGHORN_CLIENT_URL"],
        }

        logging.info("initiated variables:")
        for var in cls._config:
            logging.info(f"{var}={cls._config[var]}")
