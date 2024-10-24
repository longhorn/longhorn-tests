from longhorn_deploy import LonghornDeploy
class longhorn_deploy_keywords:

    def __init__(self):
        self.longhorn = LonghornDeploy()

    def uninstall_longhorn_system(self, is_stable_version=False):
        self.longhorn.uninstall(is_stable_version)

    def check_longhorn_crd_removed(self):
        self.longhorn.check_longhorn_crd_removed()

    def install_longhorn_system(self, is_stable_version=False):
        self.longhorn.install(is_stable_version)
