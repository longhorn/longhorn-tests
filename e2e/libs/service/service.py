from kubernetes import client

import utility.constant as constant


def list_services(label_selector, namespace=constant.LONGHORN_NAMESPACE):
    core_api = client.CoreV1Api()
    return core_api.list_namespaced_service(
        namespace=namespace,
        label_selector=label_selector
    )


def is_services_headless(namespace=constant.LONGHORN_NAMESPACE, label_selector=None):
    services = list_services(label_selector, namespace=namespace)
    for service in services.items:
        if service.spec.cluster_ip == "None":
            return True
    return False
