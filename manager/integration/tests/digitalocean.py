import os
import requests
import signal
import time

from cloudprovider import cloudprovider


class digitalocean(cloudprovider):
    DO_API_TOKEN = os.getenv("ENV_DO_API_TOKEN")
    DO_API_URL_BASE = "https://api.digitalocean.com/v2/"
    DO_NODE_TAG = "longhorn-tests"
    DO_REQ_HEADERS = {'Content-Type': 'application/json',
                      'Authorization': 'Bearer {0}'.format(DO_API_TOKEN)}
    DO_API_TIMEOUT_SEC = 120

    def timeout_handler(self, signum, frame):
        raise Exception("Err: Digitalocean API timed out")

    def is_api_token_defined(self):
        if self.DO_API_TOKEN is None or self.DO_API_TOKEN == "":
            print("Err: ENV_DO_API_TOKEN is not defined")
            return False
        else:
            return True

    def node_id(self, node_name):
        assert self.is_api_token_defined()

        api_url = '{0}droplets'.format(self.DO_API_URL_BASE)

        payload = {'tag_name': self.DO_NODE_TAG}

        do_api_response = \
            requests.get(api_url, params=payload, headers=self.DO_REQ_HEADERS)

        do_nodes = do_api_response.json()

        for do_droplet in do_nodes['droplets']:
            if do_droplet['name'] == node_name:
                return do_droplet['id']

    def node_status(self, node_id):
        assert self.is_api_token_defined()

        api_url = '{0}droplets'.format(self.DO_API_URL_BASE)

        payload = {'tag_name': self.DO_NODE_TAG}

        do_api_response = requests.get(api_url,
                                       params=payload,
                                       headers=self.DO_REQ_HEADERS)

        do_nodes = do_api_response.json()

        for do_droplet in do_nodes['droplets']:
            if do_droplet['id'] == node_id:
                return do_droplet['status']

    def droplet_exec_action(self,
                            droplet_id,
                            action,
                            expected_status,
                            desired_status):
        assert self.is_api_token_defined()

        api_url = '{0}droplets/{1}/actions'.format(self.DO_API_URL_BASE,
                                                   droplet_id)

        payload = {'type': action}

        droplet_current_status = self.node_status(droplet_id)

        if droplet_current_status == expected_status:
            requests.post(api_url, headers=self.DO_REQ_HEADERS, json=payload)

            signal.signal(signal.SIGALRM, self.timeout_handler)
            signal.alarm(self.DO_API_TIMEOUT_SEC)

            try:
                while self.node_status(droplet_id) == expected_status:
                    time.sleep(1)
            except Exception as exc:
                print(exc)
                return False

            return True

        elif droplet_current_status == desired_status:
            return True

    def node_start(self, node_id):
        self.droplet_exec_action(droplet_id=node_id,
                                 action="power_on",
                                 expected_status="off",
                                 desired_status="active")

    def node_shutdown(self, node_id):
        self.droplet_exec_action(droplet_id=node_id,
                                 action="shutdown",
                                 expected_status="active",
                                 desired_status="off")
