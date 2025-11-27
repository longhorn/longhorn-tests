import time
import json

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd
import utility.constant as constant

class BackupBackingImage:

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, backing_image_name, backup_backing_image_name):
        backup_backing_image_cr_yaml = f"""
apiVersion: longhorn.io/v1beta2
kind: BackupBackingImage
metadata:
  name: {backup_backing_image_name}
  namespace: {constant.LONGHORN_NAMESPACE}
spec:
  backingImage: {backing_image_name}
  backupTargetName: default
  userCreated: true
"""
        cmd = f"kubectl apply -f -"
        subprocess_exec_cmd(cmd, input=backup_backing_image_cr_yaml)
        self.wait_for_backup_backing_image_ready(backup_backing_image_name)

    def get_by_name(self, backup_backing_image_name):
        cmd = f"kubectl get backupbackingimage {backup_backing_image_name} -n {constant.LONGHORN_NAMESPACE} -ojson"
        try:
            return json.loads(subprocess_exec_cmd(cmd))
        except Exception as e:
            logging(f"Failed to get backup backing image {backup_backing_image_name}: {e}")
            return None

    def get_by_backing_image_name(self, backing_image_name):
        cmd = f"kubectl get backupbackingimages -n {constant.LONGHORN_NAMESPACE} -o json | jq '.items | map(select(.spec.backingImage == \"{backing_image_name}\")) | first'"
        try:
            return json.loads(subprocess_exec_cmd(cmd))
        except Exception as e:
            logging(f"Failed to get backup backing image by backing image {backing_image_name}: {e}")
            return None

    def wait_for_backup_backing_image_ready(self, backup_backing_image_name):
        for i in range(self.retry_count):
            logging(f"Waiting for backup backing image {backup_backing_image_name} ready ... ({i})")
            backup_bi = self.get_by_name(backup_backing_image_name)
            if backup_bi and backup_bi['status']['state'] == "Completed":
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for backup backing image {backup_backing_image_name} ready"

    def wait_for_backup_backing_image_for_backing_image_ready(self, backing_image_name):
        for i in range(self.retry_count):
            logging(f"Waiting for backup backing image for backing image {backing_image_name} ready ... ({i})")
            backup_bi = self.get_by_backing_image_name(backing_image_name)
            if backup_bi and backup_bi['status']['state'] == "Completed":
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for backup backing image for backing image {backing_image_name} ready"

    def cleanup_backup_backing_images(self):
        logging(f"Cleaning up backup backing images")
        cmd = f"kubectl delete backupbackingimage --all -n {constant.LONGHORN_NAMESPACE}"
        subprocess_exec_cmd(cmd)
