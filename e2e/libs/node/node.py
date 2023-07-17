import logging

from node.aws import EC2
from node.local_cluster import LocalCluster
from strategy import CloudProvider
from utils.common_utils import k8s_core_api

class Nodes:

    _core_api = None
    _instance = None
    all_nodes = []

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, name, public_ip="", cloud_provider='aws'):
        self._name = name
        self._public_ip = public_ip

        cloud_provider_list = [provider.value for provider in CloudProvider]
        if cloud_provider not in cloud_provider_list:
            logging.error(f"could not recognize the cloud provider: {cloud_provider}, default value AWS")
            self.__class__._instance = EC2(self.__class__.all_nodes)
        elif cloud_provider == CloudProvider.AWS.value:
            logging.info("cloude provider: AWS")
            self.__class__._instance = EC2(self.__class__.all_nodes)
        elif cloud_provider == CloudProvider.LOCAL_CLUSTER.value:
            logging.info("cloude provider: Local")
            self.__class__._instance = LocalCluster(self.__class__.all_nodes)

    @property
    def name(self):
        return self.name

    @property
    def public_ip(self):
        return self._public_ip

    @public_ip.setter
    def public_ip(self, value):
        self._public_ip = value

    @classmethod
    def get_name_by_index(cls, index):
        logging.info(f"getting node node by index {index}")
        if index < 0 or index > len(cls.all_nodes):
            raise Exception(f"invalid parameter: index={index}")

        node_name = cls.all_nodes[int(index)]['name']
        assert node_name != "", f"failed to get node name with index {index}"

        return node_name

    @classmethod
    def get_index_by_name(cls, node_name):
        logging.info(f"getting node index by name {node_name}")
        index = 0
        for node in cls.all_nodes:
            if node["name"] == node_name:
                return index
            index += 1

        raise Exception(f"failed to get index by node name {node_name}")

    @classmethod
    def get_node_state(cls, node_name):
        logging.info(f"getting node {node_name} state")
        node_status = k8s_core_api().read_node_status(node_name)
        for node_cond in node_status.status.conditions:
            if node_cond.type == "Ready" and \
                    node_cond.status == "True":
                return node_cond.type
        return "NotReady"

    @classmethod
    def refresh_node_list(cls):
        logging.info("refreshing node list")

        resp = k8s_core_api().list_node()
        assert resp != "", "failed to get cluster nodes"

        nodes = resp.items
        assert len(nodes) > 0, "failed to get cluster nodes: empty items"

        for item in nodes:
            worker_node = False
            if ('node-role.kubernetes.io/control-plane' not in item.metadata.labels and
                    'node-role.kubernetes.io/master' not in item.metadata.labels):
                worker_node = True
            elif ('node-role.kubernetes.io/worker' in item.metadata.labels and
                  item.metadata.labels['node-role.kubernetes.io/worker'] == 'true'):
                worker_node = True

            if worker_node:
                # https://kubernetes.io/docs/concepts/architecture/nodes/#addresses
                # Sort the node address field order by definition
                address_types = ['ExternalIP', 'InternalIP', 'Hostname']
                address_types_dict = dict([[i,address_types.index(i)] for i in address_types])
                item.status.addresses.sort(key=lambda x:address_types_dict[x.type])

                for address in item.status.addresses:
                    if address.type == "ExternalIP":
                        node_name = item.metadata.name
                        ip_address = address.address
                        break
                    elif address.type == "InternalIP":
                        node_name = item.metadata.name
                        ip_address = address.address
                        break

                # if node is exist then update the ip address or add new one
                exists = False
                for node in Nodes.all_nodes:
                    if node['name'] == node_name:
                        node['ip_address'] = ip_address
                        exists = True

                if not exists:
                    new_node = {'name': node_name, 'ip_address': ip_address}
                    cls.all_nodes.append(new_node)

        logging.info(f'cluster nodes:{Nodes.all_nodes}')

    @classmethod
    def get_pods_with_node_name(cls, node_name):
        all_pods = []
        all_pods = k8s_core_api().list_namespaced_pod(namespace='longhorn-system', field_selector='spec.nodeName=' + node_name)
        user_pods = [p for p in all_pods.items
                  if (p.metadata.namespace != 'kube-system')]
        return user_pods

    @classmethod
    def cleanup(cls):
        # Turn the power off node back
        logging.info('restore node state')
        assert cls._instance != None, 'failed to execute since empty instance'
        cls._instance.power_on_node_instance()

    @classmethod
    def power_off_node(cls, node_name):
        assert cls._instance != None, 'failed to execute since empty instance'
        cls._instance.power_off_node_instance(node_name)

    @classmethod
    def power_on_node(cls, node_name):
        assert cls._instance != None, 'failed to execute since empty instance'
        cls._instance.power_on_node_instance(node_name)

