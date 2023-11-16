from persistentvolumeclaim import PersistentVolumeClaim

from utility.constant import ANNOT_EXPANDED_SIZE
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume.constant import MEBIBYTE


class persistentvolumeclaim_keywords:

    def __init__(self):
        self.claim = PersistentVolumeClaim()

    def cleanup_persistentvolumeclaims(self):
        claims = self.claim.list(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(claims.items)} persistentvolumeclaims')
        for claim in claims.items:
            self.delete_persistentvolumeclaim(claim.metadata.name)

    def create_persistentvolumeclaim(self, name, volume_type="RWO", option=""):
        logging(f'Creating persistentvolumeclaim {name}')
        return self.claim.create(name, volume_type, option)

    def delete_persistentvolumeclaim(self, name):
        logging(f'Deleting persistentvolumeclaim {name}')
        return self.claim.delete(name)

    def expand_persistentvolumeclaim_size_by_mib(self, claim_name, size_in_mib):
        size_in_byte = int(size_in_mib) * MEBIBYTE
        expanded_size = self.claim.expand(claim_name, size_in_byte)

        logging(f'Expanding persistentvolumeclaim {claim_name} by {size_in_mib} MiB')
        self.claim.set_annotation(claim_name, ANNOT_EXPANDED_SIZE, str(expanded_size))
