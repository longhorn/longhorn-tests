import configparser
import logging

from kubernetes import client

CONFIG_FILE_PATH = 'settings.ini'

def initialize_variables():
    logging.info("initiate environment variables")

    global variables
    global K8S_API_CLIENT
    global K8S_CR_API_CLIENT
    global K8S_APP_API_CLIENT

    K8S_API_CLIENT = client.CoreV1Api()
    K8S_CR_API_CLIENT = client.CustomObjectsApi()
    K8S_APP_API_CLIENT = client.AppsV1Api()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH, encoding='utf-8')
    section_name = "DEFAULT"
    if 'CUSTOM' in config.sections():
        section_name = "CUSTOM"

    variables = {
        "RETRY_INTERVAL": config[section_name]["RETRY_INTERVAL"],
        "SSH_CONFIG_PATH": config[section_name]["SSH_CONFIG_PATH"],
        "CLOUD_PROVIDER": config[section_name]["CLOUD_PROVIDER"],
        "K8S_DISTRO": config[section_name]["K8S_DISTRO"],
        "LONGHORN_CLIENT_URL": config[section_name]["LONGHORN_CLIENT_URL"],
        "KUBECONFIG_PATH": config[section_name]["KUBECONFIG_PATH"],
    }

    logging.info("initiated variables:")
    for var in variables:
        logging.info(f"{var}={variables[var]}")
