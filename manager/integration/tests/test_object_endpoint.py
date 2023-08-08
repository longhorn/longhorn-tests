import pytest

OBJECT_ENDPOINT_LABEL = "Object Endpoint"
OBJECT_ENDPOINT_NAME = "object-endpoint"

from common import Gi
from common import LONGHORN_NAMESPACE


@pytest.mark.object_endpoint  #NOQA
def test_create_object_endpoint():
    """
    Scenario: test the creation of an object storage endpoint

    Given:
    - StorageClass, size

    When an ObjectEndpoint resource is created:
    - Create a Deployment, PVC, Secret and Service
    - The PVC is of the given storage class and size
    """
    pass

@pytest.mark.object_endpoint  #NOQA
def test_delete_object_endpoint():
    """
    Scenario: test the deletion of an object storage endpoint

    Given:
    - An ObjectEndpoint and its associated resources (Deployment, PVC, Secret,
      Service)

    When the object endpoint is deleted:
    - Its resources are deleted as well
    """
    pass
