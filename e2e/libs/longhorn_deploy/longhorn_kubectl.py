from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
import utility.constant as constant
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL
from utility.utility import logging

import subprocess
import os
import time

class LonghornKubectl(Base):

    def uninstall(self, is_stable_version):
        env_var = "LONGHORN_STABLE_VERSION" if is_stable_version else "LONGHORN_REPO_BRANCH"
        longhorn_branch = os.getenv(env_var)
        if not longhorn_branch:
           raise ValueError(f"Required environment variable {env_var} is not set")

        logging(f"Running longhorn uninstall job")
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, "uninstall_longhorn", longhorn_branch],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall longhorn failed"

        self.check_longhorn_uninstall_pod_log()

        logging(f"Deleting longhorn CRDs")
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, "delete_longhorn_crds", longhorn_branch],
                                   shell=False)
        process.wait()

        logging(f"Deleting longhorn uninstall job")
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, "delete_uninstall_job", longhorn_branch],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Deleting longhorn uninstall job failed")
            time.sleep(self.retry_count)
            assert False, "Deleting longhorn uninstall job failed"

        k8s.wait_namespace_terminated(namespace=constant.LONGHORN_NAMESPACE)

    def install(self, custom_cmd, install_stable_version):
        if install_stable_version:
            install_function = "install_longhorn_stable"
        else:
            install_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, install_function, custom_cmd],
                                   shell=False)
        process.wait()
        return True if process.returncode == 0 else False

    def upgrade(self, upgrade_to_transient_version, timeout):
        if upgrade_to_transient_version:
            upgrade_function = "install_longhorn_transient"
        else:
            upgrade_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
        try:
            process.wait(timeout=timeout)
            return True if process.returncode == 0 else False
        except subprocess.TimeoutExpired:
            logging(f"Upgrade timeout after {timeout}s. Killing process...")
            process.kill()
            process.wait()
            return False
