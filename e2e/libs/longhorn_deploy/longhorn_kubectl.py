from longhorn_deploy.base import Base
from node import Node
from node_exec import NodeExec
from k8s import k8s
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import LONGHORN_UNINSTALL_JOB_LABEL

import os

class LonghornKubectl(Base):

    def uninstall(self, is_stable_version=False):
        env_var = "LONGHORN_STABLE_VERSION" if is_stable_version else "LONGHORN_REPO_BRANCH"
        longhorn_branch = os.getenv(env_var)
        if not longhorn_branch:
           raise ValueError(f"Required environment variable {env_var} is not set")

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

    def install(self, is_stable_version=False):
        self.install_longhorn(is_stable_version)
