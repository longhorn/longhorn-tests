import time

from workload.constant import IMAGE_UBUNTU
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest


def restart_kubelet(node_name, downtime_in_sec=10):
    manifest = new_pod_manifest(
        image=IMAGE_UBUNTU,
        command=["/bin/bash"],
        args=["-c", f"sleep 10 && systemctl stop k3s-agent && sleep {downtime_in_sec} && systemctl start k3s-agent"],
        node_name=node_name
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    time.sleep(downtime_in_sec)

    delete_pod(pod_name)
