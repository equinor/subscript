
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
