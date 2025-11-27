from longhorn_deploy import LonghornDeploy


class longhorn_deploy_keywords:

    def __init__(self):
        self.longhorn = LonghornDeploy()

    def uninstall_longhorn_system(self, is_stable_version=False):
        self.longhorn.uninstall(is_stable_version)

    def check_longhorn_crd_removed(self):
        self.longhorn.check_longhorn_crd_removed()

    def install_longhorn_system(self, custom_cmd="", install_stable_version=False, longhorn_namespace="longhorn-system"):
        self.longhorn.install(custom_cmd, install_stable_version, longhorn_namespace)

    def upgrade_longhorn(self, upgrade_to_transient_version=False, timeout=600, wait_when_fail=True):
        return self.longhorn.upgrade(upgrade_to_transient_version, timeout, wait_when_fail)
