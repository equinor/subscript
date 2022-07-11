from os import path

import pytest

import subscript


@pytest.fixture
def path_to_subscript():
    """path to installed subscript module."""
    return path.dirname(subscript.__file__)


def pytest_addoption(parser):
    """Add options that will be available when running `pytest` on the command line
    in this directory"""
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
    parser.addoption(
        "--flow-simulator",
        action="store",
        default=None,
        help="The path to flow simulator,"
        " defaults to not running tests depending on flow",
    )
    parser.addoption(
        "--eclipse-simulator",
        action="store",
        default=None,
        help="The path to eclipse simulator,"
        " defaults to not running tests depending on eclipse",
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


@pytest.fixture
def flow_simulator(request):
    flow_path = request.config.getoption("--flow-simulator")
    if flow_path is None:
        pytest.skip("No flow executable given, see --flow-simulator")
    return flow_path


@pytest.fixture
def eclipse_simulator(request):
    eclipse_path = request.config.getoption("--eclipse-simulator")
    if eclipse_path is None:
        pytest.skip("No eclipse executable given, see --eclipse-simulator")
    return eclipse_path


@pytest.fixture(params=["eclipse", "flow"])
def simulator(request):
    simulator = request.param
    simulator_path = request.config.getoption(f"--{simulator}-simulator")
    if simulator_path is None:
        pytest.skip(f"No {simulator} executable given, see --{simulator}-simulator")
    return simulator_path
