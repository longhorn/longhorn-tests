"""
Test Object Store Controller
---

This module excercises the object store controller, which is part of the
longhorn manager and controls the deployment of S3 stores and their endpoints
according to ObjectStore CRDs.
"""
import random
import string
import time
import base64

import boto3
import pytest

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException

from common import get_core_api_client
from common import get_apps_api_client
from common import get_custom_object_api_client
from common import LONGHORN_NAMESPACE

LONGHORN_API_GROUP = "longhorn.io"
LONGHORN_API_VERSION = "v1beta2"
LONGHORN_API_KIND = "ObjectStore"
LONGHORN_API_KIND_PLURAL = "objectstores"

OBJECT_STORE_LABEL = "Object Store"
OBJECT_STORE_NAME = "object-store"
OBJECT_STORE_SIZE = "2Gi"

DEFAULT_OBJECT_STORE_NAME = "test-object-store"
DEFAULT_OBJECT_STORE_ACCESS_KEY = "foobar"
DEFAULT_OBJECT_STORE_SECRET_KEY = "barfoo"

DEFAULT_SECRET_NAME = "test-credentials"

WAIT_INTERVAL = 1  # one second
WAIT_TIMEOUT = 120  # two minutes


@pytest.fixture
def secret():
    """
    Secret pytest fixtue
    This fixture is just a K8s secret that contains the access key and secret
    key for seeding the s3gw.
    """
    uid = gen_id(6)
    manifest = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {
            'name': f"{DEFAULT_SECRET_NAME}-{uid}",
            'namespace': LONGHORN_NAMESPACE,
        },
        'type': 'Opaque',
        'data': {
            'RGW_DEFAULT_USER_ACCESS_KEY': base64.b64encode(
                DEFAULT_OBJECT_STORE_ACCESS_KEY.encode('utf-8')
            ).decode("utf-8"),
            'RGW_DEFAULT_USER_SECRET_KEY': base64.b64encode(
                DEFAULT_OBJECT_STORE_SECRET_KEY.encode('utf-8')
            ).decode("utf-8"),
        }
    }
    create_secret(manifest)
    yield manifest
    delete_secret(manifest)


@pytest.fixture
def object_store(secret):  # pylint: disable=W0621
    """
    Object Store pytest fixture
    This fixture yields an object store in the cluster and the manifest to
    the callers location. When the calling test is finished (with or without
    failure) the object store is removed from the cluster.
    It is not an error if the object store is removed explicitly during the
    calling test.
    The fixture has a partly randomly generated name to avoid tests influencing
    each other due to name clashes.
    """
    uid = gen_id(6)
    manifest = {
        'apiVersion': f"{LONGHORN_API_GROUP}/{LONGHORN_API_VERSION}",
        'kind': LONGHORN_API_KIND,
        'metadata': {
            'name': f"{DEFAULT_OBJECT_STORE_NAME}-{uid}",
            'namespace': LONGHORN_NAMESPACE,
        },
        'spec': {
            'storage': {
                'size': OBJECT_STORE_SIZE,
            },
            'credentials': {
                'name': secret['metadata']['name'],
                'namespace': secret['metadata']['namespace'],
            },
        }
    }
    create_object_store(manifest)
    yield manifest
    delete_object_store(manifest)
    wait_object_store_removed(manifest)


@pytest.mark.object_store
def test_create_object_store(object_store):  # pylint: disable=W0621
    """
    Scenario: test the creation of an object store

    Given:
    - Size
    - Name
    - Secret

    When an ObjectStore resource is created:
    - Create a Deployment, Service, PVC, PV and Longhorn volume

    Wait for the ObjectStore to transition into "running" state

    When the ObjectStore is in "running" state:
    - The Longhorn volume must be in "attached" state
    - The PV must be bound
    - The PVC must be bound
    - The service must have a port
    - The deployment must have exactly one expected, desired, actual and
      available replica
    - The object store must be in "running" state
    - The object store must have and addres containing its own name in
      its `.status.endpoints` property
    - The address from the object store's `.status.endpoints` must answer to
      S3 requests.
    """
    wait_object_store_running(object_store)

    assert_longhorn_volume_ready(object_store)
    assert_persistent_volume_ready(object_store)
    assert_persistent_volume_claim_ready(object_store)
    assert_service_ready(object_store)
    assert_deployment_ready(object_store)
    assert_object_store_running(object_store)
    assert_object_store_has_endpoints(object_store)
    assert_object_store_smoke_s3(object_store)


@pytest.mark.object_store
def test_delete_object_store(object_store):  # pylint: disable=W0621
    """
    Scenario: test the deletion of an object store

    Given:
    - An ObjectStore in "running" state and its associated resources
      (Deployment, PVC, Secret, Service, PV and Longhorn volume)

    When the object store is deleted:
    - The Deployment is removed
    - The Service is removed
    - The Secret is removed
    - The PersistenVolumeClaim is removed
    - The PersistenVolume is removed
    - The Longhorn volume is removed
    """
    wait_object_store_running(object_store)
    delete_object_store(object_store)
    wait_object_store_removed(object_store)

    assert_deployment_removed(object_store)
    assert_service_removed(object_store)
    assert_persistent_volume_claim_removed(object_store)
    assert_persistent_volume_removed(object_store)
    assert_longhorn_volume_removed(object_store)

# - - -
# Below here are utilities and helper functions for testing the object store
# controller.
#
# pylint: disable=missing-function-docstring


def assert_object_store_running(manifest):
    store = get_object_store(manifest)
    assert store is not None
    assert "status" in store
    assert store['status']['state'] == "running"


def assert_object_store_has_endpoints(manifest):

    def name_is_part_of_an_endpoint(name, endpoints):
        """
        Takes a name and a list of endpoint urls and returns true if the name
        occurs in any of the endpoint urls.
        """
        for url in endpoints:
            if name in url:
                return True
        return False

    store = get_object_store(manifest)
    assert store is not None
    assert "status" in store
    assert store['status']['endpoints'] is not None
    assert len(store['status']['endpoints']) > 0
    assert name_is_part_of_an_endpoint(store['metadata']['name'],
                                       store['status']['endpoints'])


def assert_object_store_smoke_s3(manifest):
    store = get_object_store(manifest)

    client = boto3.session.Session().client(
        service_name='s3',
        aws_access_key_id=DEFAULT_OBJECT_STORE_ACCESS_KEY,
        aws_secret_access_key=DEFAULT_OBJECT_STORE_SECRET_KEY,
        endpoint_url=f"http://{store['status']['endpoints'][0]}",
        use_ssl=False,
    )

    assert client.list_buckets() is not None


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

    assert desired_replicas == 1  # always 1 replica of s3gw per object store
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

    err_prefix = f"object store {name}"
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

    err_prefix = f"object store {name}"
    assert False, f"{err_prefix} left orphaned service {name}"


def assert_persistent_volume_claim_ready(manifest):
    api = get_core_api_client()
    store = manifest['metadata']['name']
    name = f"pvc-{store}"

    try:
        pvc = api.read_namespaced_persistent_volume_claim(name,
                                                          LONGHORN_NAMESPACE)
    except ApiException:
        assert False, "API Error while getting persistent volume claim"

    assert pvc.status.phase == "Bound"


def assert_persistent_volume_claim_removed(manifest):
    api = get_core_api_client()
    store = manifest['metadata']['name']
    name = f"pvc-{store}"

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_namespaced_persistent_volume_claim(name,
                                                        LONGHORN_NAMESPACE)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object store {name}"
    assert False, f"{err_prefix} left orphaned persistent volume claim {name}"


def assert_persistent_volume_ready(manifest):
    api = get_core_api_client()
    store = manifest['metadata']['name']
    name = f"pv-{store}"

    try:
        pv = api.read_persistent_volume(name)  # pylint: disable=invalid-name
    except ApiException:
        assert False, "API Error while getting persistent volume claim"

    assert pv.status.phase == "Bound"


def assert_persistent_volume_removed(manifest):
    api = get_core_api_client()
    store = manifest['metadata']['name']
    name = f"pv-{store}"

    for _ in range(WAIT_TIMEOUT):
        try:
            api.read_persistent_volume(name)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    err_prefix = f"object store {name}"
    assert False, f"{err_prefix} left orphaned persistent volume {name}"


def assert_longhorn_volume_ready(manifest):
    api = get_custom_object_api_client()
    store = manifest['metadata']['name']
    name = f"pv-{store}"

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
    store = manifest['metadata']['name']
    name = f"pv-{store}"

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

    err_prefix = f"object store {name}"
    assert False, f"{err_prefix} left orphaned longhorn volume {name}"


def wait_object_store_running(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        status = api.get_namespaced_custom_object_status(
            LONGHORN_API_GROUP,
            LONGHORN_API_VERSION,
            LONGHORN_NAMESPACE,
            LONGHORN_API_KIND_PLURAL,
            name)
        if status is not None and \
                "status" in status and \
                status['status']['state'] == "running":
            return

        time.sleep(WAIT_INTERVAL)

    assert False, "timed out waiting for object store"


def wait_object_store_removed(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']

    for _ in range(WAIT_TIMEOUT):
        try:
            api.get_namespaced_custom_object(LONGHORN_API_GROUP,
                                             LONGHORN_API_VERSION,
                                             LONGHORN_NAMESPACE,
                                             LONGHORN_API_KIND_PLURAL,
                                             name)
        except ApiException as exception:
            assert exception.status == 404, "API Error"
            return

        time.sleep(WAIT_INTERVAL)

    assert False, "timed out waiting for object store to be removed"


def create_object_store(manifest):
    api = get_custom_object_api_client()
    api.create_namespaced_custom_object(LONGHORN_API_GROUP,
                                        LONGHORN_API_VERSION,
                                        LONGHORN_NAMESPACE,
                                        LONGHORN_API_KIND_PLURAL,
                                        manifest)


def delete_object_store(manifest):
    api = get_custom_object_api_client()
    try:
        api.delete_namespaced_custom_object(LONGHORN_API_GROUP,
                                            LONGHORN_API_VERSION,
                                            LONGHORN_NAMESPACE,
                                            LONGHORN_API_KIND_PLURAL,
                                            name=manifest['metadata']['name'],
                                            body=k8sclient.V1DeleteOptions())
    except ApiException as exception:
        assert exception.status == 404


def get_object_store(manifest):
    api = get_custom_object_api_client()
    name = manifest['metadata']['name']
    return api.get_namespaced_custom_object(LONGHORN_API_GROUP,
                                            LONGHORN_API_VERSION,
                                            LONGHORN_NAMESPACE,
                                            LONGHORN_API_KIND_PLURAL,
                                            name)


def create_secret(manifest):
    api = get_core_api_client()
    api.create_namespaced_secret(LONGHORN_NAMESPACE, manifest)


def delete_secret(manifest):
    api = get_core_api_client()
    try:
        api.delete_namespaced_secret(manifest['metadata']['name'],
                                     LONGHORN_NAMESPACE)
    except ApiException as exception:
        assert exception.status == 404


def gen_id(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _
                   in range(length))
