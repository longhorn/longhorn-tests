import pytest
import subprocess

from common import SETTING_DELETING_CONFIRMATION_FLAG
from common import get_longhorn_api_client # NOQA


@pytest.fixture
def uninstall_manifest(request):
    return request.config.getoption("--uninstall-lh-manifest-url")


@pytest.fixture
def deploy_manifest(request):
    return request.config.getoption("--deploy-lh-manifest-url")


@pytest.mark.uninstall   # NOQA
def test_uninstall(uninstall_manifest, deploy_manifest): # NOQA

    client = get_longhorn_api_client()

    try:
        delete_confirmtion_flag = \
            client.by_id_setting(SETTING_DELETING_CONFIRMATION_FLAG)
    except Exception:
        print("Longhorn does not have setting {}".format(
            SETTING_DELETING_CONFIRMATION_FLAG))
        delete_confirmtion_flag = None

    if delete_confirmtion_flag is not None:
        setting = client.update(delete_confirmtion_flag, value="true")
        assert setting.name == SETTING_DELETING_CONFIRMATION_FLAG
        assert setting.value == "true"

    assert uninstall_longhorn(uninstall_manifest,
                              deploy_manifest)


def uninstall_longhorn(uninstall_manifest,
                       deploy_manifest,
                       ):

    command = "../scripts/uninstall-longhorn.sh"
    process = subprocess.Popen([command,
                                uninstall_manifest,
                                deploy_manifest
                                ],
                               shell=False)
    process.wait()
    if process.returncode == 0:
        longhorn_uninstall = True

    else:
        longhorn_uninstall = False

    return longhorn_uninstall
