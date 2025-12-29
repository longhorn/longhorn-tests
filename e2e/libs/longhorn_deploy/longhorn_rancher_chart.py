from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
import utility.constant as constant
from utility.utility import logging

import subprocess
import os
import time

class LonghornRancherChart(Base):

    def uninstall(self, is_stable_version):
        # destroy longhorn rancher2_app_v2 terraform resource
        command = "./pipelines/utilities/longhorn_rancher_chart.sh"
        process = subprocess.Popen([command, "uninstall_longhorn"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall longhorn failed"

        # (in terraform-provider-rancher2 8.1.0)
        # when installing longhorn with `terraform apply`
        # longhorn-crd is also automatically installed under the hood
        # but when uninstalling longhorn with `terraform destroy`
        # longhorn-crd is left behind and only longhorn itself is uninstalled
        # so we need to manually uninstall longhorn-crd
        process = subprocess.Popen([command, "uninstall_longhorn_crd"],
                                   shell=False)
        process.wait()
        if process.returncode != 0:
            logging(f"Uninstall longhorn crd failed")
            time.sleep(self.retry_count)
            assert False, "Uninstall longhorn crd failed"

        k8s.delete_namespace(namespace=constant.LONGHORN_NAMESPACE)
        k8s.wait_namespace_terminated(namespace=constant.LONGHORN_NAMESPACE)

    def install(self, custom_cmd, install_stable_version):
        if install_stable_version:
            install_function = "install_longhorn_stable"
        else:
            install_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_rancher_chart.sh"
        process = subprocess.Popen([command, install_function],
                                   shell=False)
        process.wait()
        return True if process.returncode == 0 else False

    def upgrade(self, upgrade_to_transient_version, timeout):
        if upgrade_to_transient_version:
            upgrade_function = "upgrade_longhorn_transient"
        else:
            upgrade_function = "upgrade_longhorn_custom"
        command = "./pipelines/utilities/longhorn_rancher_chart.sh"
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
