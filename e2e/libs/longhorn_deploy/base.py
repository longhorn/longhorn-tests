from abc import ABC, abstractmethod
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL
from utility.constant import LONGHORN_INSTALL_SCRIPT_PATH
from utility.constant import LONGHORN_INSTALL_TIMEOUT
import subprocess
import os
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

class Base(ABC):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    @abstractmethod
    def install(self):
        return NotImplemented

    @abstractmethod
    def uninstall(self, longhorn_branch=None):
        return NotImplemented

    def check_longhorn_crd_removed(self):
        all_crd = k8s.get_all_custom_resources()
        for crd in all_crd.items:
            assert "longhorn.io" not in crd.metadata.name

    def check_longhorn_uninstall_pod_log(self):
        logs = k8s.get_pod_logs(LONGHORN_NAMESPACE, LONGHORN_UNINSTALL_JOB_LABEL)
        assert "error" not in logs
        assert "level=fatal" not in logs

    def install_longhorn(self):
        current_path=os.getcwd()
        full_path = os.path.join(current_path, LONGHORN_INSTALL_SCRIPT_PATH)

        try:
            output = subprocess.check_output(['bash', full_path], timeout=LONGHORN_INSTALL_TIMEOUT)
            logging(output)
        except subprocess.CalledProcessError as e:
            logging(f"Error: {e.stderr}")
        except subprocess.TimeoutExpired as e:
            logging(f"Command timed out after {e.timeout} seconds")
