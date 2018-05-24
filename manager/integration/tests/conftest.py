import pytest


ENGINE_UPGRADE_IMAGE_OPT = "--engine-upgrade-image"


def pytest_addoption(parser):
    parser.addoption(ENGINE_UPGRADE_IMAGE_OPT, action="store", default="",
                     help="specify the image of engine upgrade test")


@pytest.fixture
def engine_upgrade_image(request):
    return request.config.getoption(ENGINE_UPGRADE_IMAGE_OPT)


def pytest_collection_modifyitems(config, items):
    if config.getoption(ENGINE_UPGRADE_IMAGE_OPT):
        # --upgrade-image was specified, don't skip
        return
    skip_upgrade = pytest.mark.skip(reason="need " +
                                    ENGINE_UPGRADE_IMAGE_OPT +
                                    " option to run")
    for item in items:
        if "engine_upgrade" in item.keywords:
            item.add_marker(skip_upgrade)
