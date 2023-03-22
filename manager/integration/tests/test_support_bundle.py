import pytest
import os
import zipfile

from tempfile import TemporaryDirectory

from node import taint_nodes_exclude_self  # NOQA

from common import apps_api  # NOQA
from common import client  # NOQA
from common import core_api  # NOQA

from common import check_all_support_bundle_managers_deleted
from common import create_support_bundle
from common import delete_and_wait_deployment
from common import download_support_bundle
from common import get_all_support_bundle_manager_deployments
from common import set_k8s_node_label
from common import update_setting
from common import wait_for_support_bundle_cleanup
from common import wait_for_support_bundle_state

from common import SETTING_NODE_SELECTOR
from common import SETTING_SUPPORT_BUNDLE_FAILED_LIMIT
from common import SETTING_TAINT_TOLERATION


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_should_delete_after_download(client):  # NOQA
    """
    Scenario: test support bundle should delete after download

    Issue: https://github.com/longhorn/longhorn/issues/2759

    Given support bundle created
    And support bundle is in ReadyToDownload state

    When download support bundle
    Then support bundle is downloaded
    And support bundle should be deleted
    And support bundle manager should be deleted

    """
    resp = create_support_bundle(client)
    node_id = resp['id']
    name = resp['name']

    wait_for_support_bundle_state("ReadyForDownload", node_id, name, client)

    download_support_bundle(node_id, name, client)

    wait_for_support_bundle_cleanup(client)
    check_all_support_bundle_managers_deleted()


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_should_error_when_failed(client, apps_api):  # NOQA
    """
    Scenario: test support bundle should error when failed

    Issue: https://github.com/longhorn/longhorn/issues/2759

    Given support-bundle-failed-history-limit setting is 1
    And support bundle created
    And support bundle is in Generating state

    When delete support bundle manager deployment
    Then support bundle should be in state Error

    """
    update_setting(client, SETTING_SUPPORT_BUNDLE_FAILED_LIMIT, "1")

    create_failed_support_bundles(client, apps_api)


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_failed_limit(client, apps_api):  # NOQA
    """
    Scenario: test support bundle failed limit

    Issue: https://github.com/longhorn/longhorn/issues/2759

    Given support-bundle-failed-history-limit setting is 2
    And 2 failed support bundle created

    When create support bundle
    Then should fail to create

    """
    update_setting(client, SETTING_SUPPORT_BUNDLE_FAILED_LIMIT, "3")
    create_failed_support_bundles(client, apps_api, number=2)

    try:
        create_failed_support_bundles(client, apps_api, number=1)
        assert False, \
            f'expect to fail exceeding {SETTING_SUPPORT_BUNDLE_FAILED_LIMIT}'
    except Exception:
        pass


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_purge(client, apps_api):  # NOQA
    """
    Scenario: test support bundle

    Issue: https://github.com/longhorn/longhorn/issues/2759

    Given support-bundle-failed-history-limit setting is 2
    And 2 failed support bundle created

    When set support-bundle-failed-history-limit setting to 0
    Then failed support bundles should be deleted
    And support bundle managers should be deleted

    When create a failed support bundle
    Then failed support bundle should be deleted
    And support bundle manager should be deleted

    """
    update_setting(client, SETTING_SUPPORT_BUNDLE_FAILED_LIMIT, "2")
    create_failed_support_bundles(client, apps_api, number=2)

    support_bundles = client.list_support_bundle()
    assert len(support_bundles) == 2

    update_setting(client, SETTING_SUPPORT_BUNDLE_FAILED_LIMIT, "0")
    wait_for_support_bundle_cleanup(client)
    check_all_support_bundle_managers_deleted()

    # Will try to catch the Error state here because it is an intermediate
    # state
    try:
        create_failed_support_bundles(client, apps_api, number=1)
    except AssertionError:
        pass

    wait_for_support_bundle_cleanup(client)
    check_all_support_bundle_managers_deleted()


def create_failed_support_bundles(client, apps_api, number=1):  # NOQA
    for _ in range(0, number):
        resp = create_support_bundle(client)
        node_id = resp["id"]
        name = resp["name"]
        wait_for_support_bundle_state("Generating", node_id, name, client)

        deployments = get_all_support_bundle_manager_deployments(apps_api)
        delete_and_wait_deployment(
            apps_api, deployments[0].metadata.name,
            namespace=deployments[0].metadata.namespace
        )
        wait_for_support_bundle_state("Error", node_id, name, client)


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_agent_with_node_selector(client, core_api, request):  # NOQA
    """
    Scenario: support bundle agent should respect node selector

    Issue: https://github.com/longhorn/longhorn/issues/5614

    Given there are some nodes labeled
    And "system-managed-components-node-selector" is set with node label

    When a support bundle is generated

    Then should be able to download the support bundle successfully
    And support bundle should include only the labeled nodes in node collection

    """
    nodes = client.list_node()
    labeled_nodes = [nodes[1], nodes[2]]
    for node in labeled_nodes:
        set_k8s_node_label(core_api, node.name, "foo", "bar")

    def finalizer():
        for node in labeled_nodes:
            set_k8s_node_label(core_api, node.name, "foo", None)
        update_setting(client, SETTING_NODE_SELECTOR, None)
    request.addfinalizer(finalizer)

    update_setting(client, SETTING_NODE_SELECTOR, "foo:bar")

    resp = create_support_bundle(client)
    node_id = resp['id']
    name = resp['name']

    wait_for_support_bundle_state("ReadyForDownload", node_id, name, client)

    # The temporary directory will be automatically deleted outside of the
    # "with" context manager.
    with TemporaryDirectory(prefix="supportbundle-") as temp_dir:
        download_path = f'{temp_dir}/{0}.zip'.format(name)
        download_support_bundle(node_id, name, client,
                                target_path=download_path)

        with zipfile.ZipFile(download_path, 'r') as zip:
            node_names = [f"{node.name}" for node in labeled_nodes]
            check_bundled_nodes_matches(node_names, zip, temp_dir)

    wait_for_support_bundle_cleanup(client)
    check_all_support_bundle_managers_deleted()


def check_bundled_nodes_matches(node_names, zip, temp_dir):
    expect_node_zips = [f"{node}.zip" for node in node_names]
    bundle_name = os.path.dirname(zip.namelist()[0])
    bundle_node_dir = f'{bundle_name}/nodes'
    bundle_nodes = [
        f for f in zip.namelist() if f.startswith(bundle_node_dir)
    ]

    for node in bundle_nodes:
        zip.extract(node, f'{temp_dir}')

    node_zips = os.listdir(f'{temp_dir}/{bundle_name}/nodes')
    assert set(node_zips) == set(expect_node_zips), \
        f'Nodes zipped in bundle do not match. \n' \
        f'Expect = {expect_node_zips}\n' \
        f'Got = {node_zips}\n'


@pytest.mark.support_bundle   # NOQA
def test_support_bundle_agent_with_taint_toleration(client, core_api, taint_nodes_exclude_self):  # NOQA
    """
    Scenario: support bundle agent should respect taint toleration

    Issue: https://github.com/longhorn/longhorn/issues/5614

    Given there are some tainted nodes in the cluster
    And Longhorn tolerates the tainted nodes with setting "taint-toleration"

    When a support bundle is generated

    Then should be able to download the support bundle successfully
    And support bundle should include all tainted nodes in node collection

    """
    # The taint-toleration is set up to match the "taint_nodes_exclude_self"
    # fixture.
    update_setting(client, SETTING_TAINT_TOLERATION,
                   "foo/bar=test:NoSchedule; foo:NoSchedule")

    resp = create_support_bundle(client)
    node_id = resp['id']
    name = resp['name']

    wait_for_support_bundle_state("ReadyForDownload", node_id, name, client)

    # The temporary directory will be automatically deleted outside of the
    # "with" context manager.
    with TemporaryDirectory(prefix="supportbundle-") as temp_dir:
        download_path = f'{temp_dir}/{0}.zip'.format(name)
        download_support_bundle(node_id, name, client,
                                target_path=download_path)

        with zipfile.ZipFile(download_path, 'r') as zip:
            nodes = core_api.list_node()
            node_names = [f"{node.metadata.name}" for node in nodes.items]
            check_bundled_nodes_matches(node_names, zip, temp_dir)

    wait_for_support_bundle_cleanup(client)
    check_all_support_bundle_managers_deleted()
