from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE

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

    def install(self, is_stable_version=False):
        self.install_longhorn(is_stable_version)
