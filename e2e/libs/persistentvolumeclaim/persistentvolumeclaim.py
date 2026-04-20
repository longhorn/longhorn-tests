import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import ANNOT_EXPANDED_SIZE
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import convert_size_to_bytes
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class PersistentVolumeClaim():

    def __init__(self):
        self.core_v1_api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, volume_type, sc_name, storage_size="3GiB", dataSourceName=None, dataSourceKind=None, volumeMode="Filesystem", wait_for_bound=True, volume_name=None):
        storage_size_bytes = convert_size_to_bytes(storage_size)

        filepath = "./templates/workload/pvc.yaml"
        with open(filepath, 'r') as f:
            namespace = 'default'
            manifest_dict = yaml.safe_load(f)

            # correct pvc name
            manifest_dict['metadata']['name'] = name

            # add label
            manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE

            # correct storageclass name
            manifest_dict['spec']['storageClassName'] = sc_name

            # correct storage request
            manifest_dict['spec']['resources']['requests']['storage'] = storage_size_bytes

            # correct access mode`
            if volume_type == 'RWX':
                manifest_dict['spec']['accessModes'][0] = 'ReadWriteMany'
            elif volume_type == 'RWOP':
                manifest_dict['spec']['accessModes'][0] = 'ReadWriteOncePod'

            if dataSourceName and dataSourceKind:
                manifest_dict['spec']['dataSource'] = {
                    'name': dataSourceName,
                    'kind': dataSourceKind
                }
                if dataSourceKind == 'VolumeSnapshot':
                    manifest_dict['spec']['dataSource']['apiGroup'] = 'snapshot.storage.k8s.io'

            if volumeMode:
                manifest_dict['spec']['volumeMode'] = volumeMode

            if volume_name:
                manifest_dict['spec']['volumeName'] = volume_name

            logging(f"yaml = {manifest_dict}")

            self.core_v1_api.create_namespaced_persistent_volume_claim(
                body=manifest_dict,
                namespace=namespace)
            if wait_for_bound:
                self.wait_for_pvc_phase(name, "Bound")

    def delete(self, name, namespace='default'):
        try:
            self.core_v1_api.delete_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
                grace_period_seconds=0)
        except ApiException as e:
            assert e.status == 404, f"Unexpected error deleting PVC {name}: {e}"

        deleted = False
        for _ in range(self.retry_count):
            if not self.is_exist(name, namespace):
                deleted = True
                break
            time.sleep(self.retry_interval)
        assert deleted, f"Failed to delete PVC {name} in namespace {namespace}"

    def is_exist(self, name, namespace='default'):
        exist = False
        resp = self.core_v1_api.list_namespaced_persistent_volume_claim(namespace=namespace)
        for item in resp.items:
            if item.metadata.name == name:
                exist = True
                break
        return exist

    def get(self, claim_name, claim_namespace="default"):
        return self.core_v1_api.read_namespaced_persistent_volume_claim(
            name=claim_name,
            namespace=claim_namespace
        )

    def get_volume_name(self, claim_name):
        pvc = self.core_v1_api.read_namespaced_persistent_volume_claim(name=claim_name, namespace='default')
        return pvc.spec.volume_name

    def list(self, claim_namespace="default", label_selector=None):
        return self.core_v1_api.list_namespaced_persistent_volume_claim(
            namespace=claim_namespace,
            label_selector=label_selector
        ).items

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

    def expand(self, claim_name, size_in_byte, namespace="default", skip_retry=False):
        retry_count = 1 if skip_retry else self.retry_count
        for i in range(retry_count):
            logging(f"Trying to expand PVC {claim_name} to size {size_in_byte} ... ({i})")
            try:
                self.core_v1_api.patch_namespaced_persistent_volume_claim(
                    name=claim_name,
                    namespace=namespace,
                    body={
                        'spec': {
                            'resources': {
                                'requests': {
                                    'storage': str(size_in_byte)
                                }
                            }
                        }
                    }
                )
                self.set_annotation(claim_name, ANNOT_EXPANDED_SIZE, str(size_in_byte))
                return size_in_byte
            except Exception as e:
                logging(f"Exception when expanding PVC: {e}")
            time.sleep(self.retry_interval)

        assert False, f"Failed to expand {claim_name} size to {size_in_byte}"

    def expand_with_additional_bytes(self, claim_name, size_in_byte, skip_retry=False):
        pvc = self.get(claim_name)
        current_size = int(pvc.spec.resources.requests['storage'])

        target_size = current_size + size_in_byte
        expanded_size = self.expand(claim_name, target_size, skip_retry=skip_retry)
        self.set_annotation(claim_name, ANNOT_EXPANDED_SIZE, str(expanded_size))

    def wait_for_pvc_phase(self, pvc_name, phase):
        for i in range(self.retry_count):
            try:
                pvc = self.core_v1_api.read_namespaced_persistent_volume_claim(
                    name=pvc_name, namespace='default')
                logging(f"Waiting for pvc {pvc_name} phase to be {phase}, currently it's {pvc.status.phase} ... ({i})")
                if pvc.status.phase == phase:
                    return
            except Exception as e:
                logging(f"Waiting for pvc {pvc_name} phase to be {phase} error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for pvc {pvc_name} phase to be {phase}: {pvc}"

    def get_pvc_storageclass_name(self, pvc_name):
        logging(f"Reading for pvc {pvc_name} storageclass name")
        pvc = self.core_v1_api.read_namespaced_persistent_volume_claim(
                    name=pvc_name, namespace='default')
        logging(f"Pvc {pvc_name} is using storageclass {pvc.spec.storage_class_name }")

        return pvc.spec.storage_class_name
