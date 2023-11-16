from kubelet.kubelet import restart_kubelet

from utility.utility import logging


class kubelet_keywords:

    def restart_kubelet(self, node_name, downtime_in_sec):
        logging(f'Restarting kubelet on node {node_name} with downtime {downtime_in_sec} seconds')
        restart_kubelet(node_name, int(downtime_in_sec))
