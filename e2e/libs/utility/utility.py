from . import globalVars
from kubernetes import config, client
from kubernetes.client import configuration
from longhorn import from_env
from pick import pick

import requests
import warnings
import datetime
import string
import random
import os
import paramiko
import time
import logging

MAX_SUPPORT_BINDLE_NUMBER = 20
RETRY_EXEC_COUNTS = 30
RETRY_INTERVAL_LONG = 2

class Utility:

    @classmethod
    def generate_volume_name(cls):
        return "vol-" + \
            ''.join(random.choice(string.ascii_lowercase + string.digits)
                    for _ in range(6))

    @classmethod
    def init_k8s_api_client(cls):
        logging.info('initiate the K8s api clients')

        # to make it easier to develop and debug
        # run test in local environment instead of in-cluster
        # our existing test is running in in-cluster environment
        # it makes us always need to build new docker image to test our code
        contexts, active_context = config.list_kube_config_contexts(globalVars.variables["KUBECONFIG_PATH"])
        if not contexts:
            raise Exception("cannot find any context in kube-config file.")

        contexts = [context['name'] for context in contexts]
        active_index = contexts.index(active_context['name'])
        option, _ = pick(contexts, title="Pick the context to load",
                        default_index=active_index)

        kubecfg = config.load_kube_config(context=option)  # for local environment
        globalVars.K8S_API_CLIENT = client.CoreV1Api(api_client = kubecfg)
        globalVars.K8S_CR_API_CLIENT = client.CustomObjectsApi(api_client = kubecfg)
        globalVars.K8S_APP_API_CLIENT = client.AppsV1Api(api_client = kubecfg)

        logging.debug("Active host is %s" % configuration.Configuration().host)

    @classmethod
    def get_k8s_core_api_client(cls):
        logging.info("getting K8S core API client")
        cls().init_k8s_api_client()
        return client.CoreV1Api()

    @classmethod
    def get_longhorn_client(cls):
        logging.info("getting Longhorn client")
        # manually expose longhorn client node port
        # otherwise the test is needed to be run in in-cluster environment
        # to access longhorn manager cluster ip
        longhorn_client_url = globalVars.variables["LONGHORN_CLIENT_URL"]
        longhorn_client = from_env(url=f"{longhorn_client_url}/v1/schemas")
        return longhorn_client

    @classmethod
    def get_support_bundle_url(cls):
        client = Utility.get_longhorn_client()
        return client._url.replace('schemas', 'supportbundles')

    @classmethod
    def generate_support_bundle(cls, case_name):  # NOQA
        """
            Generate support bundle into folder ./support_bundle/case_name.zip

            Won't generate support bundle if current support bundle count
            greate than MAX_SUPPORT_BINDLE_NUMBER.
            Args:
                case_name: support bundle will named case_name.zip
        """
        os.makedirs("support_bundle", exist_ok=True)
        file_cnt = len(os.listdir("support_bundle"))

        if file_cnt >= MAX_SUPPORT_BINDLE_NUMBER:
            warnings.warn("Ignoring the bundle download because of \
                                avoiding overwhelming the disk usage.")
            return

        url = cls.get_support_bundle_url()
        data = {'description': case_name, 'issueURL': case_name}
        try:
            logging.debug(f'support bundle url: {url}, data: {data}')
            res_raw = requests.post(url, json=data)
            res_raw.raise_for_status()
            res = res_raw.json()
            logging.debug(f'support bundle res: {res}')
        except Exception as e:
            warnings.warn(f"Error while generating support bundle: {e}")
            return
        id = res['data'][0]['id']
        name = res['data'][0]['name']

        support_bundle_url = '{}/{}/{}'.format(url, id, name)
        for i in range(RETRY_EXEC_COUNTS):
            res = requests.get(support_bundle_url).json()

            if res['progressPercentage'] == 100:
                break
            else:
                time.sleep(RETRY_INTERVAL_LONG)

        if res['progressPercentage'] != 100:
            warnings.warn("Timeout to wait support bundle ready, skip download")
            return

        # Download support bundle
        download_url = '{}/download'.format(support_bundle_url)
        try:
            r = requests.get(download_url, allow_redirects=True, timeout=300)
            r.raise_for_status()
            with open('./support_bundle/{0}.zip'.format(case_name), 'wb') as f:
                f.write(r.content)
        except Exception as e:
            warnings.warn("Error occured while downloading support bundle {}.zip\n\
                The error was {}".format(case_name, e))

    @classmethod
    def ssh_and_exec_cmd(cls, host, cmd):
        logging.info(f"ssh into {host} and execute commands {cmd}")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        cls().ssh_connect_with_retry(ssh, host, 0)
        chan = ssh.get_transport().open_session()
        chan.exec_command(cmd)

        isExecCommand = True
        while isExecCommand:
            if chan.recv_ready():
                logging.debug(f'response of command: ', chan.recv(4096).decode('ascii'))

            if chan.exit_status_ready():
                if chan.recv_stderr_ready() and chan.recv_exit_status() != 0:
                    raise Exception('fail to execute command:', chan.recv_stderr(4096).decode('ascii'))

                isExecCommand = False
                logging.debug(f'success of command execution: {chan.recv_exit_status()}')
                ssh.close()

    def ssh_connect_with_retry(cls, ssh, ip_address, retries):
        while retries > 0:
            try:
                logging.info(f"connecting to {ip_address} with SSH")

                config = paramiko.SSHConfig()
                try:
                    config.parse(open(os.path.expanduser(globalVars.variables["SSH_CONFIG_PATH"])))
                except IOError:
                    # No file found, so empty configuration
                    pass

                host_conf = config.lookup(ip_address)
                cfg = {}
                if host_conf:
                    if 'user' in host_conf:
                        cfg['username'] = host_conf['user']
                    if 'identityfile' in host_conf:
                        cfg['key_filename'] = host_conf['identityfile']
                    if 'hostname' in host_conf:
                        cfg['hostname'] = host_conf['hostname']

                ssh.connect(**cfg)
                return True
            except Exception as e:
                retries -= 1
                logging.warning(f"exception occurs: {e}. Retrying and the number of retries remaining: {retries}")
                time.sleep(float(globalVars.variables["RETRY_INTERVAL"]))
                continue
