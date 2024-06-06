from kubernetes import client


def list_services(label_selector, namespace="longhorn-system"):
    core_api = client.CoreV1Api()
    return core_api.list_namespaced_service(
        namespace=namespace,
        label_selector=label_selector
    )


def is_services_headless(namespace="longhorn-system", label_selector=None):
    services = list_services(label_selector, namespace=namespace)
    for service in services.items:
        if service.spec.cluster_ip == "None":
            return True
    return False
