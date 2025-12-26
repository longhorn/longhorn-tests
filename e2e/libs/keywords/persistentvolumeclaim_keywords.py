from persistentvolumeclaim import PersistentVolumeClaim
from volume import Volume

from utility.constant import ANNOT_EXPANDED_SIZE
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging
from utility.utility import convert_size_to_bytes

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

    def create_persistentvolumeclaim(self, name, volume_type="RWO", sc_name="longhorn", storage_size="3GiB", dataSourceName=None, dataSourceKind=None):
        logging(f'Creating {volume_type} persistentvolumeclaim {name} with {sc_name} storageclass')
        return self.claim.create(name, volume_type, sc_name, storage_size, dataSourceName, dataSourceKind)

    def delete_persistentvolumeclaim(self, name):
        logging(f'Deleting persistentvolumeclaim {name}')
        return self.claim.delete(name)

    def expand_persistentvolumeclaim_size_to(self, claim_name, size):
        logging(f'Expanding persistentvolumeclaim {claim_name} to {size}')
        size_in_byte = convert_size_to_bytes(size)
        expanded_size = self.claim.expand(claim_name, size_in_byte)

        logging(f'Expanded persistentvolumeclaim {claim_name} to {expanded_size}')
        self.claim.set_annotation(claim_name, ANNOT_EXPANDED_SIZE, str(expanded_size))

    def get_claim_requested_size(self, claim_name):
        claim = self.claim.get(claim_name)
        return claim.spec.resources.requests['storage']

    def get_volume_name_from_persistentvolumeclaim(self, claim_name):
        return self.claim.get_volume_name(claim_name)

    def get_pvc_storageclass_name(self, claim_name):
        return self.claim.get_pvc_storageclass_name(claim_name)
