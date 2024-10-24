from longhorn_deploy.base import Base
from longhorn_deploy.longhorn_kubectl import LonghornKubectl
from longhorn_deploy.longhorn_helm_chart import LonghornHelmChart
import os

class LonghornDeploy(Base):

    _method = os.getenv("LONGHORN_INSTALL_METHOD", "manifest")

    def __init__(self):

        if self._method == "manifest":
            self.longhorn = LonghornKubectl()
        elif self._method == "helm":
            self.longhorn = LonghornHelmChart()

    def uninstall(self, is_stable_version=False):
        return self.longhorn.uninstall(is_stable_version)

    def check_longhorn_crd_removed(self):
        return self.longhorn.check_longhorn_crd_removed()

    def install(self, is_stable_version=False):
        return self.longhorn.install(is_stable_version)
