from abc import ABC, abstractmethod
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL
from utility.constant import LONGHORN_INSTALL_SCRIPT_PATH
from utility.constant import LONGHORN_INSTALL_TIMEOUT
import subprocess
import os
import time
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

class Base(ABC):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    @abstractmethod
    def install(self):
        return NotImplemented

    @abstractmethod
    def uninstall(self, is_stable_version=False):
        return NotImplemented

    def check_longhorn_crd_removed(self):
        all_crd = k8s.get_all_custom_resources()
        for crd in all_crd.items:
            assert "longhorn.io" not in crd.metadata.name

    def check_longhorn_uninstall_pod_log(self):
        logs = k8s.get_pod_logs(LONGHORN_NAMESPACE, LONGHORN_UNINSTALL_JOB_LABEL)
        assert "level=error" not in logs, f"find string 'level=error' in uninstall log {logs}"
        assert "level=fatal" not in logs, f"find string 'level=fatal' in uninstall log {logs}"

    def create_longhorn_namespace(self):
        command = "./pipelines/utilities/create_longhorn_namespace.sh"
        process = subprocess.Popen([command, "create_longhorn_namespace"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Creating longhorn namespace failed")
            time.sleep(self.retry_count)
            assert False, "Creating longhorn namespace failed"

    def install_backupstores(self):
        command = "./pipelines/utilities/install_backupstores.sh"
        process = subprocess.Popen([command, "install_backupstores"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Installing backupstores failed")
            time.sleep(self.retry_count)
            assert False, "Installing backupstores failed"

    def create_registry_secret(self):
        command = "./pipelines/utilities/create_registry_secret.sh"
        process = subprocess.Popen([command, "create_registry_secret"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Creating registry secret failed")
            time.sleep(self.retry_count)
            assert False, "Creating registry secret failed"

    def setup_longhorn_ui_nodeport(self):
        command = "./pipelines/utilities/longhorn_ui.sh"
        process = subprocess.Popen([command, "setup_longhorn_ui_nodeport"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Setting up Longhorn UI nodeport failed")
            time.sleep(self.retry_count)
            assert False, "Setting up Longhorn UI nodeport failed"
