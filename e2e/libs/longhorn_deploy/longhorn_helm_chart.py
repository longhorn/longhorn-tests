from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE

import subprocess
import os

class LonghornHelmChart(Base):

    def uninstall(self, is_stable_version=False):
        control_plane_nodes = Node.list_node_names_by_role(self, role="control-plane")
        control_plane_node = control_plane_nodes[0]

        cmd = f'export KUBECONFIG={os.getenv("KUBECONFIG")} && helm uninstall longhorn -n {LONGHORN_NAMESPACE}'
        res = NodeExec(control_plane_node).issue_cmd(cmd)
        assert res, "apply helm uninstall command failed"

        k8s.delete_namespace(namespace=LONGHORN_NAMESPACE)
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