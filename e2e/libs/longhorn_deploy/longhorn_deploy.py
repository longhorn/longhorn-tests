from longhorn_deploy.base import Base
from longhorn_deploy.longhorn_kubectl import LonghornKubectl
from longhorn_deploy.longhorn_helm_chart import LonghornHelmChart
from longhorn_deploy.longhorn_rancher_chart import LonghornRancherChart
from longhorn_deploy.longhorn_flux import LonghornFlux
from longhorn_deploy.longhorn_fleet import LonghornFleet
from longhorn_deploy.longhorn_argocd import LonghornArgocd
from utility.utility import logging
import os
import time

class LonghornDeploy(Base):

    _method = os.getenv("LONGHORN_INSTALL_METHOD", "manifest")

    def __init__(self):

        super().__init__()
        if self._method == "manifest":
            self.longhorn = LonghornKubectl()
        elif self._method == "helm":
            self.longhorn = LonghornHelmChart()
        elif self._method == "rancher":
            self.longhorn = LonghornRancherChart()
        elif self._method == "flux":
            self.longhorn = LonghornFlux()
        elif self._method == "fleet":
            self.longhorn = LonghornFleet()
        elif self._method == "argocd":
            self.longhorn = LonghornArgocd()

    def uninstall(self, is_stable_version):
        logging(f"Uninstalling Longhorn")
        # add some delay before uninstallation
        # for issue https://github.com/longhorn/longhorn/issues/10483
        time.sleep(60)
        self.longhorn.uninstall(is_stable_version)
        logging(f"Uninstalled Longhorn")

    def check_longhorn_crd_removed(self):
        return self.longhorn.check_longhorn_crd_removed()

    def install(self, install_stable_version):
        logging(f"Installing Longhorn {'stable' if install_stable_version else 'the latest'} version")
        self.longhorn.create_longhorn_namespace()
        self.longhorn.install_backupstores()
        self.longhorn.create_registry_secret()
        installed = self.longhorn.install(install_stable_version)
        if not installed:
            logging(f"Installing Longhorn failed")
            time.sleep(self.retry_count)
            assert False, "Installing Longhorn failed"
        self.longhorn.setup_longhorn_ui_nodeport()
        logging(f"Installed Longhorn")

    def upgrade(self, upgrade_to_transient_version, timeout, wait_when_fail):
        logging(f"Upgrading Longhorn to {'transient' if upgrade_to_transient_version else 'the latest'} version")
        upgraded = self.longhorn.upgrade(upgrade_to_transient_version, timeout)
        if not upgraded:
            logging(f"Upgrading Longhorn failed")
            if wait_when_fail is True:
                time.sleep(self.retry_count)
            return False
        else:
            # add some delay between 2 upgrades
            time.sleep(60)
        logging(f"Upgraded Longhorn")
        return upgraded
