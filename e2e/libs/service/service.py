import json

from utility.utility import subprocess_exec_cmd
import utility.constant as constant


def list_services(label_selector=None, namespace=constant.LONGHORN_NAMESPACE):
    cmd = f"kubectl -n {namespace} get svc"
    if label_selector:
        cmd += f" -l {label_selector}"
    cmd += " -o json"
    output = json.loads(subprocess_exec_cmd(cmd))
    return output.get('items', [])
