import pytest

from common import apps_api  # NOQA
from common import client  # NOQA

from common import check_all_support_bundle_managers_deleted
from common import create_support_bundle
from common import delete_and_wait_deployment
from common import download_support_bundle
from common import get_all_support_bundle_manager_deployments
from common import update_setting
from common import wait_for_support_bundle_cleanup
from common import wait_for_support_bundle_state

from common import SETTING_SUPPORT_BUNDLE_FAILED_LIMIT


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
