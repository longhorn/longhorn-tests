from persistentvolumeclaim import PersistentVolumeClaim
from volume import Volume

from utility.constant import ANNOT_EXPANDED_SIZE
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume.constant import MEBIBYTE


class persistentvolumeclaim_keywords:

    def __init__(self):
        self.claim = PersistentVolumeClaim()
        self.volume = Volume()

    def cleanup_persistentvolumeclaims(self):
        claims = self.claim.list(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(claims)} persistentvolumeclaims')
        for claim in claims:
            self.delete_persistentvolumeclaim(claim.metadata.name)
            self.volume.wait_for_volume_deleted(claim.spec.volume_name)

    def create_persistentvolumeclaim(self, name, volume_type="RWO", sc_name="longhorn", storage_size="3GiB"):
        logging(f'Creating {volume_type} persistentvolumeclaim {name} with {sc_name} storageclass')
        return self.claim.create(name, volume_type, sc_name, storage_size)

    def delete_persistentvolumeclaim(self, name):
        logging(f'Deleting persistentvolumeclaim {name}')
        return self.claim.delete(name)

    def expand_persistentvolumeclaim_size_by_mib(self, claim_name, size_in_mib):
        size_in_byte = int(size_in_mib) * MEBIBYTE
        expanded_size = self.claim.expand(claim_name, size_in_byte)

        logging(f'Expanding persistentvolumeclaim {claim_name} by {size_in_mib} MiB')
        self.claim.set_annotation(claim_name, ANNOT_EXPANDED_SIZE, str(expanded_size))

    def get_claim_requested_size(self, claim_name):
        claim = self.claim.get(claim_name)
        return claim.spec.resources.requests['storage']
