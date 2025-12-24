from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
import utility.constant as constant
from utility.utility import logging

import subprocess
import os
import time

class LonghornArgocd(Base):

    def uninstall(self, is_stable_version):
        env_var = "LONGHORN_STABLE_VERSION" if is_stable_version else "LONGHORN_INSTALL_VERSION"
        longhorn_version = os.getenv(env_var)
        if not longhorn_version:
           raise ValueError(f"Required environment variable {env_var} is not set")

        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, "uninstall_longhorn", longhorn_version],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall longhorn failed"

        self.check_longhorn_uninstall_pod_log()

        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, "delete_longhorn_crds", longhorn_version],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Deleting longhorn CRDs failed")
            time.sleep(self.retry_count)
            assert False, "Deleting longhorn CRDs failed"

        k8s.wait_namespace_terminated(namespace=constant.LONGHORN_NAMESPACE)

        command = "./pipelines/utilities/argocd.sh"
        process = subprocess.Popen([command, "uninstall_longhorn_app"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall argocd longhorn app failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall argocd longhorn app failed"

    def install(self, custom_cmd, install_stable_version):
        if install_stable_version:
            install_function = "install_longhorn_stable"
        else:
            install_function = "install_longhorn_custom"
        command = "./pipelines/utilities/argocd.sh"
        process = subprocess.Popen([command, install_function],
                                   shell=False)
        process.wait()
        return True if process.returncode == 0 else False

    def upgrade(self, upgrade_to_transient_version, timeout):
        if upgrade_to_transient_version:
            upgrade_function = "upgrade_longhorn_transient"
        else:
            upgrade_function = "upgrade_longhorn_custom"
        command = "./pipelines/utilities/argocd.sh"
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
