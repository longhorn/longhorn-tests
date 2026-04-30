from datetime import datetime
import time
import json

from workload.pod import delete_pod, get_pod
from utility.utility import subprocess_exec_cmd
from utility.utility import get_cr as get_namespaced_cr
import utility.constant as constant


class ShareManager:

    def __init__(self):
        pass

    def get(self, name):
        return get_pod(name, constant.LONGHORN_NAMESPACE)

    def list(self):
        cmd = f"kubectl -n {constant.LONGHORN_NAMESPACE} get pod -l longhorn.io/component=share-manager -o json"
        output = json.loads(subprocess_exec_cmd(cmd, verbose=False))
        return output.get('items', [])

    def delete(self, name):
        return delete_pod(name, constant.LONGHORN_NAMESPACE)

    def get_cr(self, volume_name):
        return get_namespaced_cr(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="sharemanagers",
            name=volume_name
        )

    def get_spec(self, volume_name):
        return self.get_cr(volume_name)["spec"]

    def get_status(self, volume_name):
        return self.get_cr(volume_name)["status"]

    def get_spec_image(self, volume_name):
        return self.get_spec(volume_name)["image"]

    def get_status_current_image(self, volume_name):
        return self.get_status(volume_name).get("currentImage", "")

    def get_pod_container_image(self, volume_name):
        pod_name = f"share-manager-{volume_name}"
        pod = self.get(pod_name)
        if pod is None:
            return None
        return pod.spec.containers[0].image
