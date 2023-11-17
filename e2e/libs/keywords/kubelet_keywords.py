from kubelet.kubelet import restart_kubelet


class kubelet_keywords:

    def restart_kubelet(self, node_name, stop_time_in_sec):
        restart_kubelet(node_name, int(stop_time_in_sec))
