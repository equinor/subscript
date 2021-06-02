from os import path

import pytest

import subscript


@pytest.fixture
def path_to_subscript():
    """path to installed subscript module."""
    return path.dirname(subscript.__file__)


def pytest_addoption(parser):
    parser.addoption(
        "--plot",
        action="store_true",
        default=False,
        help="run tests that display plots to the screen",
    )
    parser.addoption(
        "--ri_dev",
        action="store_true",
        default=False,
        help="run tests that display plots to the screen",
    )


def pytest_collection_modifyitems(config, items):
    """Add skip markers to marked test functions skip it unless
    options are supplied on the pytest command line"""
    for item in items:
        if "plot" in item.keywords and not config.getoption("--plot"):
            item.add_marker(pytest.mark.skip(reason="need --plot option to run"))
        if "ri_dev" in item.keywords and not config.getoption("--ri_dev"):
            item.add_marker(pytest.mark.skip(reason="need --ri_dev option to run"))


@pytest.fixture
def plot(request):
    """Provide a fixture that tests can use to evaluate whether
    --plot was present on the command line"""
    return request.config.getoption("--plot")
