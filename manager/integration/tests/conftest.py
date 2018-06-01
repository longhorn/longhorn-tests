import pytest


ENGINE_UPGRADE_IMAGE_OPT = "--engine-upgrade-image"
ENABLE_RECURRING_JOB_OPT = "--enable-recurring-job-test"


def pytest_addoption(parser):
    parser.addoption(ENGINE_UPGRADE_IMAGE_OPT, action="store", default="",
                     help="specify the image of engine upgrade test")
    parser.addoption(ENABLE_RECURRING_JOB_OPT, action="store_true",
                     default=False,
                     help="enable recurring job test or not")


@pytest.fixture
def engine_upgrade_image(request):
    return request.config.getoption(ENGINE_UPGRADE_IMAGE_OPT)


def pytest_collection_modifyitems(config, items):
    if not config.getoption(ENGINE_UPGRADE_IMAGE_OPT):
        skip_upgrade = pytest.mark.skip(reason="need " +
                                        ENGINE_UPGRADE_IMAGE_OPT +
                                        " option to run")
        for item in items:
            if "engine_upgrade" in item.keywords:
                item.add_marker(skip_upgrade)

    if not config.getoption(ENABLE_RECURRING_JOB_OPT):
        skip_upgrade = pytest.mark.skip(reason="need " +
                                        ENABLE_RECURRING_JOB_OPT +
                                        " option to run")
        for item in items:
            if "recurring_job" in item.keywords:
                item.add_marker(skip_upgrade)
