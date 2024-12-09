import time

from kubernetes import client

from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class CRD():

    def __init__(self):
        self.core_v1_api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get(self, claim_name, claim_namespace="default"):
        return self.core_v1_api.read_namespaced_persistent_volume_claim(
            name=claim_name,
            namespace=claim_namespace,
        )

    def list(self, claim_namespace="default", label_selector=None):
        return self.core_v1_api.list_namespaced_persistent_volume_claim(
            namespace=claim_namespace,
            label_selector=label_selector
        )

    def set_label(self, claim_name, label_key, label_value, claim_namespace="default"):
        for i in range(self.retry_count):
            logging(f"Trying to set pvc {claim_name} label {label_key} = {label_value} ... ({i})")
            try:
                claim = self.get(claim_name, claim_namespace)

                labels = claim.metadata.labels
                if labels is None:
                    labels = {}

                if label_key in labels and labels[label_key] == label_value:
                    return

                labels[label_key] = label_value
                claim.metadata.labels = labels
                self.core_v1_api.patch_namespaced_persistent_volume_claim(
                    name=claim_name,
                    namespace=claim_namespace,
                    body=claim
                )
            except Exception as e:
                logging(f"Setting pvc {claim_name} label failed: {e}")
            time.sleep(self.retry_interval)

        assert False, f"Failed to set label {label_key} to {label_value} for PVC {claim_name}"

    def set_annotation(self, claim_name, annotation_key, annotation_value, claim_namespace="default"):
        for i in range(self.retry_count):
            logging(f"Trying to set pvc {claim_name} annotation {annotation_key} = {annotation_value} ... ({i})")
            try:
                claim = self.get(claim_name, claim_namespace)

                annotations = claim.metadata.annotations
                if annotations is None:
                    annotations = {}

                if annotation_key in annotations and annotations[annotation_key] == annotation_value:
                    return

                annotations[annotation_key] = annotation_value
                claim.metadata.annotations = annotations
                self.core_v1_api.patch_namespaced_persistent_volume_claim(
                    name=claim_name,
                    namespace=claim_namespace,
                    body=claim
                )
            except Exception as e:
                logging(f"Setting pvc {claim_name} annotation failed: {e}")
            time.sleep(self.retry_interval)

        assert False, f"Failed to set annotation {annotation_key} to {annotation_value} for PVC {claim_name}"

    def get_annotation_value(self, claim_name, annotation_key, claim_namespace="default"):
        claim = self.get(claim_name, claim_namespace)
        return claim.metadata.annotations[annotation_key]

    def get_volume_name(self, claim_name, claim_namespace="default"):
        claim = self.get(claim_name, claim_namespace)
        return claim.spec.volume_name

    def expand(self, claim_name, size, namespace="default", skip_retry=False):
        retry_count = 1 if skip_retry else self.retry_count
        for i in range(retry_count):
            logging(f"Trying to expand PVC {claim_name} to size {size} ... ({i})")
            try:
                self.core_v1_api.patch_namespaced_persistent_volume_claim(
                    name=claim_name,
                    namespace=namespace,
                    body={
                        'spec': {
                            'resources': {
                                'requests': {
                                    'storage': str(size)
                                }
                            }
                        }
                    }
                )
                return size
            except Exception as e:
                logging(f"Exception when expanding PVC: {e}")
            time.sleep(self.retry_interval)

        assert False, f"Failed to expand {claim_name} size to {size}"
