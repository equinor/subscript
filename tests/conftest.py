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


def pytest_collection_modifyitems(config, items):
    """Allow adding @pytest.mark.plot to a test function to
    skip it unless --plot is supplied on the pytest command line"""
    if config.getoption("--plot"):
        # Do not skip tests when --plot is supplied on pytest command line
        return
    skip_plot = pytest.mark.skip(reason="need --plot option to run")
    for item in items:
        if "plot" in item.keywords:
            item.add_marker(skip_plot)


@pytest.fixture
def plot(request):
    """Provide a fixture that tests can use to evaluate whether
    --plot was present on the command line"""
    return request.config.getoption("--plot")
