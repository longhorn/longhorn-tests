from abc import ABC, abstractmethod
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL
from utility.constant import LONGHORN_INSTALL_SCRIPT_PATH
from utility.constant import LONGHORN_INSTALL_TIMEOUT
from utility.constant import LONGHORN_INSTALL_STABLE_SHELL_FUNCTION
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

    def install_longhorn(self, is_stable_version=False):
        current_path=os.getcwd()
        full_path = os.path.join(current_path, LONGHORN_INSTALL_SCRIPT_PATH)

        if is_stable_version is True:
            cmd = ['bash', full_path, LONGHORN_INSTALL_STABLE_SHELL_FUNCTION]
        else:
            cmd = ['bash', full_path]

        try:
            output = subprocess.check_output(cmd, timeout=LONGHORN_INSTALL_TIMEOUT)
            logging(output)
        except subprocess.CalledProcessError as e:
            logging(f"Command failed with exit code {e.returncode}")
            logging(f"stdout: {e.output}")
            logging(f"stderr: {e.stderr}")
            raise
        except subprocess.TimeoutExpired as e:
            logging(f"Command timed out after {e.timeout} seconds")
            logging(f"stdout: {e.output}")
            raise
