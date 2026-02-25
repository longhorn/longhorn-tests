from datetime import datetime
import time
import json

from workload.pod import delete_pod, get_pod
from utility.utility import subprocess_exec_cmd
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
