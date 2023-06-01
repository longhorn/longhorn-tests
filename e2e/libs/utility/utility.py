from kubernetes import config, client
from longhorn import from_env
import string
import random
import os

class Utility:

    def generate_volume_name(cls):
        return "vol-" + \
            ''.join(random.choice(string.ascii_lowercase + string.digits)
                    for _ in range(6))

    def init_k8s_api_client(cls):
        print('init_k8s_api_client')
        # to make it easier to develop and debug
        # run test in local environment instead of in-cluster
        # our existing test is running in in-cluster environment
        # it makes us always need to build new docker image to test our code
        config.load_kube_config()  # for local environment
        # config.load_incluster_config()  # for in-cluster environment

    def get_longhorn_client(cls):
        print('get_longhorn_client')
        # manually expose longhorn client node port
        # otherwise the test is needed to be run in in-cluster environment
        # to access longhorn manager cluster ip
        longhorn_client_url = os.getenv('LONGHORN_CLIENT_URL')
        longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
        print(longhorn_client)
        return longhorn_client
