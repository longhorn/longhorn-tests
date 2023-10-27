from persistent_volume_claim import PersistentVolumeClaim

from utility.utility import logging

from volume.constant import MEBIBYTE


class persistent_volume_claim_keywords:

    def __init__(self):
        self.pvc = PersistentVolumeClaim()


    def expand_pvc_size_by_mib(self, claim_name, size_in_mib):
        logging(f'Expanding PVC {claim_name} by {size_in_mib} MiB')
        size_in_byte = int(size_in_mib) * MEBIBYTE
        return self.pvc.expand(claim_name, size_in_byte)
