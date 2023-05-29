import pytest

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration

from common import get_longhorn_api_client, \
    NODE_CONDITION_MOUNTPROPAGATION, CONDITION_STATUS_TRUE
from common import wait_for_node_mountpropagation_condition
from common import check_longhorn, check_csi_expansion
from common import generate_support_bundle

SKIP_BACKING_IMAGE_OPT = "--skip-backing-image-test"
SKIP_RECURRING_JOB_OPT = "--skip-recurring-job-test"
SKIP_INFRA_OPT = "--skip-infra-test"
INCLUDE_STRESS_OPT = "--include-stress-test"
INCLUDE_UPGRADE_OPT = "--include-upgrade-test"
INCLUDE_CA_OPT = "--include-cluster-autoscaler-test"
INCLUDE_UNINSTALL_OPT = "--include-uninstall-test"

UPGRADE_LH_REPO_URL = "--upgrade-lh-repo-url"
UPGRADE_LH_REPO_BRANCH = "--upgrade-lh-repo-branch"
UPGRADE_LH_MANAGER_IMAGE = "--upgrade-lh-manager-image"
UPGRADE_LH_ENGINE_IMAGE = "--upgrade-lh-engine-image"
UPGRADE_LH_INSTANCE_MANAGER_IMAGE = "--upgrade-lh-instance-manager-image"
UPGRADE_LH_SHARE_MANAGER_IMAGE = "--upgrade-lh-share-manager-image"
UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE = \
    "--upgrade-lh-backing-image-manager-image"
UNINSTALL_LH_MANIFEST_URL = "--uninstall-lh-manifest-url"
DEPLOY_LH_MANIFEST_URL = "--deploy-lh-manifest-url"


def pytest_addoption(parser):
    parser.addoption(SKIP_BACKING_IMAGE_OPT, action="store_true",
                     default=False, help="skip backing image tests")

    parser.addoption(SKIP_RECURRING_JOB_OPT, action="store_true",
                     default=False,
                     help="skip recurring job test or not")

    parser.addoption(SKIP_INFRA_OPT, action="store_true",
                     default=False,
                     help="skip infra tests (default: False)")

    parser.addoption(INCLUDE_STRESS_OPT, action="store_true",
                     default=False,
                     help="include stress tests (default: False)")

    parser.addoption(INCLUDE_UPGRADE_OPT, action="store_true",
                     default=False,
                     help="include upgrade tests (default: False)")

    parser.addoption(INCLUDE_CA_OPT, action="store_true",
                     default=False,
                     help="include cluster autoscaler tests (default: False)")

    parser.addoption(INCLUDE_UNINSTALL_OPT, action="store_true",
                     default=False,
                     help="include uninstall test (default: False)")

    longhorn_repo_url =\
        "https://github.com/longhorn/longhorn.git"
    parser.addoption(UPGRADE_LH_REPO_URL, action="store",
                     default=longhorn_repo_url,
                     help='''set longhorn repo url, this will be used
                     to generate longhorn yaml manifest for test_upgrade
                     (default:
                     https://github.com/longhorn/longhorn.git)''')

    parser.addoption(UPGRADE_LH_REPO_BRANCH, action="store",
                     default="master",
                     help='''set longhorn repo branch, this will be used
                     to generate longhorn yaml manifest for test_upgrade
                     (default: master)''')

    parser.addoption(UPGRADE_LH_MANAGER_IMAGE, action="store",
                     default="longhornio/longhorn-manager:master-head",
                     help='''set custom longhorn-manger image, this image will
                     be used in test_upgrade
                     (default: longhornio/longhorn-manager:master-head)''')

    parser.addoption(UPGRADE_LH_ENGINE_IMAGE, action="store",
                     default="longhornio/longhorn-engine:master-head",
                     help='''set custom longhorn-engine image, this image will
                     be used in test_upgrade
                     (default: longhornio/longhorn-engine:master-head)''')

    parser.addoption(UPGRADE_LH_INSTANCE_MANAGER_IMAGE, action="store",
                     default="longhornio/longhorn-instance-manager:master-head", # NOQA
                     help='''set custom longhorn-instance-manager image, this
                     image will be used in test_upgrade
                     (default: longhornio/longhorn-instance-manager:master-head)
                     ''') # NOQA

    parser.addoption(UPGRADE_LH_SHARE_MANAGER_IMAGE, action="store",
                     default="longhornio/longhorn-share-manager:master-head",
                     help='''set custom longhorn-share-manager image, this image
                     will be used in test_upgrade
                     (default: longhornio/longhorn-share-manager:master-head)''') # NOQA

    parser.addoption(UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE, action="store",
                     default="longhornio/backing-image-manager:master-head",
                     help='''set custom backing-image-manager image, this image
                     will be used in test_upgrade
                     (default: longhornio/backing-image-manager:master-head)''') # NOQA

    parser.addoption(UNINSTALL_LH_MANIFEST_URL, action="store",
                     default="https://raw.githubusercontent.com/longhorn/"
                             "longhorn/master/uninstall/uninstall.yaml",
                     help='''Manifest file to uninstall Longhorn
                     will be used in test_uninstall
                     (default: https://raw.githubusercontent.com/longhorn/longhorn/master/uninstall/uninstall.yaml)''') # NOQA

    parser.addoption(DEPLOY_LH_MANIFEST_URL, action="store",
                     default="https://raw.githubusercontent.com/longhorn/"
                             "longhorn/master/deploy/longhorn.yaml",
                     help='''Manifest of deploy Longhorn
                     will be used in test_uninstall
                     (default: https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml)''') # NOQA


def pytest_collection_modifyitems(config, items):
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    core_api = k8sclient.CoreV1Api()

    check_longhorn(core_api)

    if config.getoption(SKIP_BACKING_IMAGE_OPT):
        skip_backing_image = pytest.mark.skip(
            reason="remove " + SKIP_BACKING_IMAGE_OPT + " option to run")
        for item in items:
            if "backing_image" in item.keywords:
                item.add_marker(skip_backing_image)

    if config.getoption(SKIP_RECURRING_JOB_OPT):
        skip_upgrade = pytest.mark.skip(reason="remove " +
                                               SKIP_RECURRING_JOB_OPT +
                                               " option to run")
        for item in items:
            if "recurring_job" in item.keywords:
                item.add_marker(skip_upgrade)

    csi_expansion_enabled = check_csi_expansion(core_api)
    if not csi_expansion_enabled:
        skip_csi_expansion = pytest.mark.skip(reason="environment is not " +
                                                     "using csi expansion")
        for item in items:
            if "csi_expansion" in item.keywords:
                item.add_marker(skip_csi_expansion)

    all_nodes_support_mount_propagation = True
    for node in get_longhorn_api_client().list_node():
        node = wait_for_node_mountpropagation_condition(
            get_longhorn_api_client(), node.name)
        if "conditions" not in node.keys():
            all_nodes_support_mount_propagation = False
        else:
            conditions = node.conditions
            for key, condition in conditions.items():
                if key == NODE_CONDITION_MOUNTPROPAGATION and \
                        condition.status != CONDITION_STATUS_TRUE:
                    all_nodes_support_mount_propagation = False
                    break
        if not all_nodes_support_mount_propagation:
            break

    if not all_nodes_support_mount_propagation:
        skip_node = pytest.mark.skip(reason="environment does not " +
                                            "support mount disk")
        for item in items:
            if "mountdisk" in item.keywords:
                item.add_marker(skip_node)

    if config.getoption(SKIP_INFRA_OPT):
        skip_infra = pytest.mark.skip(reason="remove " +
                                      SKIP_INFRA_OPT +
                                      " option to run")

        for item in items:
            if "infra" in item.keywords:
                item.add_marker(skip_infra)

    if not config.getoption(INCLUDE_STRESS_OPT):
        skip_stress = pytest.mark.skip(reason="include " +
                                       INCLUDE_STRESS_OPT +
                                       " option to run")

        for item in items:
            if "stress" in item.keywords:
                item.add_marker(skip_stress)

    if not config.getoption(INCLUDE_UPGRADE_OPT):
        skip_upgrade = pytest.mark.skip(reason="include " +
                                        INCLUDE_UPGRADE_OPT +
                                        " option to run")

        for item in items:
            if "upgrade" in item.keywords:
                item.add_marker(skip_upgrade)

    if not config.getoption(INCLUDE_CA_OPT):
        skip_upgrade = pytest.mark.skip(reason="include " +
                                        INCLUDE_CA_OPT +
                                        " option to run")

        for item in items:
            if "cluster_autoscaler" in item.keywords:
                item.add_marker(skip_upgrade)

    if not config.getoption(INCLUDE_UNINSTALL_OPT):
        skip_uninstall = pytest.mark.skip(reason="include " +
                                          INCLUDE_UNINSTALL_OPT +
                                          " option to run")

        for item in items:
            if "uninstall" in item.keywords:
                item.add_marker(skip_uninstall)


def pytest_exception_interact(call, report):

    # Only work on TestReport, not on CollectReport
    if type(report).__name__ != "TestReport":
        return

    # Get case name
    case_name = str(report).split()[1]
    case_name = case_name.split('/')[1].replace('\'', '')

    generate_support_bundle(case_name)
