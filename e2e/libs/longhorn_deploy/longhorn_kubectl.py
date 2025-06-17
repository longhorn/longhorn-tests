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

<<<<<<< HEAD
    def install(self, is_stable_version=False):
        self.install_longhorn(is_stable_version)
=======
    def install(self, install_stable_version):
        if install_stable_version:
            install_function = "install_longhorn_stable"
        else:
            install_function = "install_longhorn_custom"
        command = "./pipelines/utilities/longhorn_manifest.sh"
        process = subprocess.Popen([command, install_function],
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
>>>>>>> 1ab6132 (test(robot): Automate manual test case Test System Upgrade with New Instance Manager)
