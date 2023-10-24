from kubernetes import client


def delete_pod(name, namespace='default'):
    core_api = client.CoreV1Api()
    core_api.delete_namespaced_pod(name=name, namespace=namespace)
