import logging
import time

from node import Nodes

retry_count = 200
retry_interval = 5

class pod_keywords:

    def wait_all_pods_evicted(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))

        for i in range(retry_count):
            pods = []
            pods = Nodes.get_pods_with_node_name(node_name)
            evict_done = True
            for pod in pods:
                # check non DaemonSet Pods are evicted or terminating (deletionTimestamp != None)
                pod_type = pod.metadata.owner_references[0].kind
                pod_delete_timestamp = pod.metadata.deletion_timestamp

                if pod_type != 'DaemonSet' and pod_delete_timestamp == None:
                    evict_done = False
                    break

            if evict_done:
                break

            time.sleep(retry_interval)

        assert evict_done, 'failed to evicted Pods'
