from longhorn_deploy.base import Base
from longhorn_deploy.longhorn_kubectl import LonghornKubectl
from longhorn_deploy.longhorn_helm_chart import LonghornHelmChart
import os
import time

class LonghornDeploy(Base):

    _method = os.getenv("LONGHORN_INSTALL_METHOD", "manifest")

    def __init__(self):

        if self._method == "manifest":
            self.longhorn = LonghornKubectl()
        elif self._method == "helm":
            self.longhorn = LonghornHelmChart()

    def uninstall(self, is_stable_version):
        # add some delay before uninstallation
        # for issue https://github.com/longhorn/longhorn/issues/10483
        time.sleep(60)
        return self.longhorn.uninstall(is_stable_version)

    def check_longhorn_crd_removed(self):
        return self.longhorn.check_longhorn_crd_removed()

    def install(self, install_stable_version):
        self.longhorn.create_longhorn_namespace()
        self.longhorn.install_backupstores()
        self.longhorn.create_registry_secret()
        installed = self.longhorn.install(install_stable_version)
        if not installed:
            logging(f"Installing Longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Installing Longhorn failed"
        self.longhorn.setup_longhorn_ui_nodeport()

    def upgrade(self, upgrade_to_transient_version):
        upgraded = self.longhorn.upgrade(upgrade_to_transient_version)
        if not upgraded:
            logging(f"Upgrading Longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Upgrading Longhorn failed"
        else:
            # add some delay between 2 upgrades
            time.sleep(60)
