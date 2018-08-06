import pytest

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from common import get_longhorn_api_client

ENABLE_RECURRING_JOB_OPT = "--enable-recurring-job-test"
ENABLE_FLEXVOLUME_OPT = "--enable-flexvolume-test"
ENABLE_CSI_OPT = "--enable-csi-test"


def pytest_addoption(parser):
    parser.addoption(ENABLE_RECURRING_JOB_OPT, action="store_true",
                     default=False,
                     help="enable recurring job test or not")
    parser.addoption(ENABLE_FLEXVOLUME_OPT, action="store_true",
                     default=False,
                     help="enable Flexvolume test or not")


def pytest_collection_modifyitems(config, items):
    if not config.getoption(ENABLE_RECURRING_JOB_OPT):
        skip_upgrade = pytest.mark.skip(reason="need " +
                                        ENABLE_RECURRING_JOB_OPT +
                                        " option to run")
        for item in items:
            if "recurring_job" in item.keywords:
                item.add_marker(skip_upgrade)

    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.CoreV1Api()

    try:
        api.read_namespaced_pod(
            name='csi-provisioner-0', namespace='longhorn-system')
        skip_upgrade = pytest.mark.skip(reason="environment is not using " +
                                               "flexvolume")

        for item in items:
            if "flexvolume" in item.keywords:
                item.add_marker(skip_upgrade)
    except ApiException as e:
        if (e.status == 404):
            skip_upgrade = pytest.mark.skip(reason="environment is not " +
                                                   "using csi")

            for item in items:
                if "csi" in item.keywords:
                    item.add_marker(skip_upgrade)

    all_nodes_support_mount_propagation = True
    for node in get_longhorn_api_client().list_node():
        all_nodes_support_mount_propagation &= node.mountPropagation

    if not all_nodes_support_mount_propagation:
        skip_upgrade = pytest.mark.skip(reason="environment does not " +
                                               "support base image")

        for item in items:
            if "baseimage" in item.keywords:
                item.add_marker(skip_upgrade)
