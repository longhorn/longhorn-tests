from strategy import LonghornOperationStrategy

from persistent_volume_claim.base import Base
from persistent_volume_claim.crd import CRD

from utility.utility import logging


class PersistentVolumeClaim(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.pvc = CRD()

    def get(self, claim_name):
        return self.pvc.get(claim_name)

    def expand(self, claim_name, size_in_byte):
        pvc = self.pvc.get(claim_name)
        current_size = int(pvc.spec.resources.requests['storage'])

        target_size = current_size + size_in_byte
        logging(f"Expanding PVC {claim_name} from {current_size} to {target_size}")
        return self.pvc.expand(claim_name, target_size)
