"""
Test Object Endpoint
---

This module excercises the object endpoint controller, which is part of the
longhorn manager and controls the deployment of S3 endpoints according to
ObjectEndpoint CRDs.
"""
import random
import string
import time
import pytest

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

from common import get_core_api_client
from common import get_apps_api_client
from common import get_custom_object_api_client
from common import create_storage_class, delete_storage_class
from common import LONGHORN_NAMESPACE

LONGHORN_API_GROUP = "longhorn.io"
LONGHORN_API_VERSION = "v1beta2"

OBJECT_ENDPOINT_LABEL = "Object Endpoint"
OBJECT_ENDPOINT_NAME = "object-endpoint"
OBJECT_ENDPOINT_SIZE = "2Gi"
OBJECT_ENDPOINT_STORAGE_CLASS_NAME = "sc-test-object-endpoint"

DEFAULT_OBJECT_ENDPOINT_NAME = "test-object-endpoint"
DEFAULT_OBJECT_ENDPOINT_ACCESS_KEY = "foobar"
DEFAULT_OBJECT_ENDPOINT_SECRET_KEY = "barfoo"

WAIT_INTERVAL = 1  # one second
WAIT_TIMEOUT = 120  # two minutes


@pytest.fixture
def storage_class():
    """
    Storage Class pytest fixture
    This fixture yields a storage class in the cluster and the manifest to the
    callers location. When the calling test is finished (with or without
    failure) the storage class is removed from the cluster
    The fixture has a partly randomly generated name to avoid tests influencing
    each other due to name clashes.
    """
    uid = gen_id(6)
    manifest = {
        'apiVersion': 'storage.k8s.io/v1',
        'kind': 'StorageClass',
        'metadata': {
            'name': f"{OBJECT_ENDPOINT_STORAGE_CLASS_NAME}-{uid}",
        },
        'provisioner': 'driver.longhorn.io',
        'allowVolumeExpansion': True,
        'reclaimPolicy': 'Delete',
        'parameters': {
            'numberOfReplicas': '3',
            'staleReplicaTimeout': '30',
        },
    }
    create_storage_class(manifest)
    yield manifest
    delete_storage_class(manifest['metadata']['name'])


@pytest.fixture
def object_endpoint(storage_class):  # pylint: disable=W0621
    """
    Object Endpoint pytest fixture
    This fixture yields an object endpoint in the cluster and the manifest to
    the callers location. When the calling test is finished (with or without
    failure) the object endpoint is removed from the cluster.
    It is not an error if the object endpoint is removed explicitly during the
    calling test.
    The fixture has a partly randomly generated name to avoid tests influencing
    each other due to name clashes.
    """
    uid = gen_id(6)
    manifest = {
        'apiVersion': 'longhorn.io/v1beta2',
        'kind': 'ObjectEndpoint',
        'metadata': {
            'name': f"{DEFAULT_OBJECT_ENDPOINT_NAME}-{uid}",
        },
        'spec': {
            'storageClassName': storage_class['metadata']['name'],
            'size': OBJECT_ENDPOINT_SIZE,
            'credentials': {
                'accessKey': DEFAULT_OBJECT_ENDPOINT_ACCESS_KEY,
                'secretKey': DEFAULT_OBJECT_ENDPOINT_SECRET_KEY,
            },
        }
    }
    create_object_endpoint(manifest)
    yield manifest
    delete_object_endpoint(manifest)
    wait_object_endpoint_removed(manifest)


@pytest.mark.object_endpoint
def test_create_object_endpoint(object_endpoint):  # pylint: disable=W0621
    """
    Scenario: test the creation of an object storage endpoint

    Given:
    - StorageClass
    - Size
    - Name
    - Access Key, Secret Key

    When an ObjectEndpoint resource is created:
    - Create a Deployment, PVC, Secret and Service
    - The PVC is of the given storage class and size

    Wait for the ObjectEndpoint to transition into "Running" state

    When the ObjectEndpoint is in "Runnin" state:
    - The Deployment must be fully "Ready"
    - The PVC must be bound and attached
    - The Service must answer to HTTP requests according to S3 semantics
    """
    wait_object_endpoint_running(object_endpoint)

    assert_object_endpoint_running(object_endpoint)
    assert_deployment_ready(object_endpoint)
    assert_service_ready(object_endpoint)
    assert_secret_ready(object_endpoint)
    assert_persistent_volume_claim_ready(object_endpoint)
    assert_persistent_volume_ready(object_endpoint)
    assert_longhorn_volume_ready(object_endpoint)


@pytest.mark.object_endpoint
def test_delete_object_endpoint(object_endpoint):  # pylint: disable=W0621
    """
    Scenario: test the deletion of an object storage endpoint

    Given:
    - An ObjectEndpoint and its associated resources (Deployment, PVC, Secret,
      Service)

    When the object endpoint is deleted:
    - Its resources are deleted as well
    """
    wait_object_endpoint_running(object_endpoint)
    delete_object_endpoint(object_endpoint)
    wait_object_endpoint_removed(object_endpoint)

    assert_deployment_removed(object_endpoint)
    assert_service_removed(object_endpoint)
    assert_secret_removed(object_endpoint)
    assert_persistent_volume_claim_removed(object_endpoint)
    assert_persistent_volume_removed(object_endpoint)
    assert_longhorn_volume_removed(object_endpoint)

# - - -
# Below here are utilities and helper functions for testing the object endpoint
# controller.
#
# pylint: disable=missing-function-docstring


def assert_object_endpoint_running(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']
    status = api.get_cluster_custom_object_status(LONGHORN_API_GROUP,
                                                  LONGHORN_API_VERSION,
                                                  "objectendpoints",
                                                  name)

    err_prefix = f"object endpoint {name}"
    assert status is not None, f"{err_prefix} has no status"
    assert "status" in status, f"{err_prefix} has no status"
    assert status['status']['state'] == "Running", f"{err_prefix} not running"


def assert_deployment_ready(manifest):
    api = get_apps_api_client()
    name = manifest['metadata']['name']
    try:
        deployment = api.read_namespaced_deployment(name, LONGHORN_NAMESPACE)
    except ApiException:
        assert False, "API Error while getting deployment"

    desired_replicas = deployment.spec.replicas
    actual_replicas = deployment.status.replicas
    available_replicas = deployment.status.available_replicas
    ready_replicas = deployment.status.ready_replicas
    unavailable_replicas = deployment.status.unavailable_replicas

    assert desired_replicas == 1  # always 1 replica of s3gw per endpoint
    assert actual_replicas == desired_replicas
    assert available_replicas == actual_replicas
    assert ready_replicas == available_replicas
    if unavailable_replicas is not None:
        assert unavailable_replicas == 0


def assert_deployment_removed(manifest):
    api = get_apps_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_namespaced_deployment(name,  LONGHORN_NAMESPACE)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned deployment {name} after timeout"


def assert_service_ready(manifest):
    api = get_core_api_client()
    name = manifest['metadata']['name']
    try:
        service = api.read_namespaced_service(name, LONGHORN_NAMESPACE)
    except ApiException:
        assert False, "API Error while getting service"

    assert len(service.spec.ports) > 0


def assert_service_removed(manifest):
    api = get_core_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_namespaced_service(name, LONGHORN_NAMESPACE)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned service {name}"


def assert_secret_ready(manifest):
    api = get_core_api_client()
    name = manifest['metadata']['name']
    try:
        secret = api.read_namespaced_secret(name, LONGHORN_NAMESPACE)
    except ApiException:
        assert False, "API Error while getting service"

    assert len(secret.data.keys()) > 0


def assert_secret_removed(manifest):
    api = get_core_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_namespaced_secret(name, LONGHORN_NAMESPACE)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned secret {name}"


def assert_persistent_volume_claim_ready(manifest):
    api = get_core_api_client()
    endpoint = manifest['metadata']['name']
    name = f"pvc-{endpoint}"

    try:
        pvc = api.read_namespaced_persistent_volume_claim(name,
                                                          LONGHORN_NAMESPACE)
    except ApiException:
        assert False, "API Error while getting persistent volume claim"

    assert pvc.status.phase == "Bound"


def assert_persistent_volume_claim_removed(manifest):
    api = get_core_api_client()
    endpoint = manifest['metadata']['name']
    name = f"pvc-{endpoint}"

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_namespaced_persistent_volume_claim(name,
                                                        LONGHORN_NAMESPACE)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned persistent volume claim {name}"


def assert_persistent_volume_ready(manifest):
    api = get_core_api_client()
    endpoint = manifest['metadata']['name']
    name = f"pv-{endpoint}"

    try:
        pv = api.read_persistent_volume(name)  # pylint: disable=invalid-name
    except ApiException:
        assert False, "API Error while getting persistent volume claim"

    assert pv.status.phase == "Bound"


def assert_persistent_volume_removed(manifest):
    api = get_core_api_client()
    endpoint = manifest['metadata']['name']
    name = f"pv-{endpoint}"

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_persistent_volume(name)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned persistent volume {name}"


def assert_longhorn_volume_ready(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    try:
        vol = api.get_namespaced_custom_object(LONGHORN_API_GROUP,
                                               LONGHORN_API_VERSION,
                                               LONGHORN_NAMESPACE,
                                               "volumes",
                                               name)
    except ApiException:
        assert False, "API Error while getting longhorn volume"

    assert vol['status']['state'] == "attached"


def assert_longhorn_volume_removed(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.get_namespaced_custom_object(LONGHORN_API_GROUP,
                                             LONGHORN_API_VERSION,
                                             LONGHORN_NAMESPACE,
                                             "volumes",
                                             name)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object endpoint {name}"
    assert False, f"{err_prefix} left orphaned longhorn volume {name}"


def wait_object_endpoint_running(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        status = api.get_cluster_custom_object_status(LONGHORN_API_GROUP,
                                                      LONGHORN_API_VERSION,
                                                      "objectendpoints",
                                                      name)
        if status is not None and \
                "status" in status and \
                status['status']['state'] == "Running":
            return

        time.sleep(WAIT_INTERVAL)

    assert False, "timed out waiting for object endpoint"


def wait_object_endpoint_removed(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.get_cluster_custom_object(LONGHORN_API_GROUP,
                                          LONGHORN_API_VERSION,
                                          "objectendpoints",
                                          name)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    assert False, "timed out waiting for object endpoint to be removed"


def create_object_endpoint(manifest):
    api = get_custom_object_api_client()
    api.create_cluster_custom_object(LONGHORN_API_GROUP,
                                     LONGHORN_API_VERSION,
                                     "objectendpoints",
                                     manifest)


def delete_object_endpoint(manifest):
    api = get_custom_object_api_client()
    try:
        api.delete_cluster_custom_object(LONGHORN_API_GROUP,
                                         LONGHORN_API_VERSION,
                                         "objectendpoints",
                                         name=manifest['metadata']['name'],
                                         body=k8sclient.V1DeleteOptions())
    except ApiException as exception:
        assert exception.status == 404


def gen_id(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _
                   in range(length))
