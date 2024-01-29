import subprocess

import pytest
from subscript.sw_model_utilities import sw_model_utilities as swtool

# This is an interactive program, so currently only a few functions are
# tested


def test_convert_normal2inverse():
    """Test conversion between normal and inverse JFUNC a, b vs A, B"""
    newa, newb = swtool.convert_normal2inverse(4, -2)

    assert newa == 2.0
    assert newb == -0.5


def test_autoconvert():
    """Test conversion between normal and inverse JFUNC a, b vs A, B"""
    num = swtool.autoformat(0.000000343432)

    assert str(num) == "3.4343e-07"


def test_choice_1():
    """Mock a user selecting choice 1"""
    result = subprocess.run(
        ["sw_model_utilities"], check=True, input=b"1\n1\n1\n", stdout=subprocess.PIPE
    )
    assert "Inverse values are: A=1.0" in result.stdout.decode()
    assert "B=1.0" in result.stdout.decode()


def test_choice_2():
    """Mock a user selecting choice 2"""
    result = subprocess.run(
        ["sw_model_utilities"], check=True, input=b"2\n1\n1\n", stdout=subprocess.PIPE
    )
    assert "Normal values are: a=1.0" in result.stdout.decode()
    assert "b=1.0" in result.stdout.decode()


def test_choice_3():
    """Mock a user selecting choice 3"""
    subprocess.run(
        ["sw_model_utilities", "--dryrun"],
        check=True,
        input=b"3\n1\n10\n0.1\n200\n0.1\nTest curve\n0.1\n-0.2\n",
        stdout=subprocess.PIPE,
    )


def test_choice_4():
    """Mock a user selecting choice 4"""
    subprocess.run(
        ["sw_model_utilities", "--dryrun"],
        check=True,
        input=b"4\n1\n10\n0.1\n200\n0.1\nTest curve\n0.1\n-0.2\n",
        stdout=subprocess.PIPE,
    )


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["sw_model_utilities", "-h"])
