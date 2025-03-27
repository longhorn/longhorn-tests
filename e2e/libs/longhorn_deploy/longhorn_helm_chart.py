from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.utility import logging

import subprocess
import os
import time

class LonghornHelmChart(Base):

    def uninstall(self, is_stable_version):
        command = "./pipelines/utilities/longhorn_helm_chart.sh"
        process = subprocess.Popen([command, "uninstall_longhorn"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall longhorn failed"
        k8s.wait_namespace_terminated(namespace=LONGHORN_NAMESPACE)

    def install(self, install_stable_version):
        if install_stable_version:
            install_function = "install_longhorn_stable"
        else:
            install_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_helm_chart.sh"
        process = subprocess.Popen([command, install_function],
                                   shell=False)
        process.wait()
        return True if process.returncode == 0 else False

    def upgrade(self, upgrade_to_transient_version):
        if upgrade_to_transient_version:
            upgrade_function = "install_longhorn_transient"
        else:
            upgrade_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_helm_chart.sh"
        process = subprocess.Popen([command, upgrade_function],
                                   shell=False)
        process.wait()
        return True if process.returncode == 0 else False