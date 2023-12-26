from kubernetes import client

from persistent_volume_claim.base import Base

from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class CRD(Base):

    def __init__(self):
        self.core_v1_api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get(self, claim_name, claim_namespace="default"):
        return self.core_v1_api.read_namespaced_persistent_volume_claim(
            name=claim_name,
            namespace=claim_namespace,
        )

    def expand(self, claim_name, size, namespace="default"):
        try:
            self.core_v1_api.patch_namespaced_persistent_volume_claim(
                name=claim_name,
                namespace=namespace,
                body={
                        'spec': {
                            'resources': {
                                'requests': {
                                    'storage':  str(size)
                                }
                            }
                        }
                }
            )
            return size
        except client.exceptions.ApiException as e:
            logging(f"Exception when expanding PVC: {e}")

        return size
