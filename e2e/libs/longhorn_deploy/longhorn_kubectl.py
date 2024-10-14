from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL

import os

class LonghornKubectl(Base):

    def uninstall(self):
        longhorn_branch = os.getenv("LONGHORN_REPO_BRANCH")

        control_plane_nodes = Node.list_node_names_by_role(self, role="control-plane")
        control_plane_node = control_plane_nodes[0]

        cmd = f"kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/{longhorn_branch}/uninstall/uninstall.yaml"
        res = NodeExec(control_plane_node).issue_cmd(cmd)
        assert res, "apply uninstall yaml failed"
        k8s.wait_namespaced_job_complete(job_label=LONGHORN_UNINSTALL_JOB_LABEL, namespace=LONGHORN_NAMESPACE)
        self.check_longhorn_uninstall_pod_log()

        cmd = f"kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/{longhorn_branch}/deploy/longhorn.yaml"
        res = NodeExec(control_plane_node).issue_cmd(cmd)
        assert res, "delete remaining components failed"

        cmd= f"kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/{longhorn_branch}/uninstall/uninstall.yaml"
        res = NodeExec(control_plane_node).issue_cmd(cmd)
        assert res, "delete uninstallation components failed"
        k8s.wait_namespace_terminated(namespace=LONGHORN_NAMESPACE)

    def install(self):
        self.install_longhorn()