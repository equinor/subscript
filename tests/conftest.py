from os import path

import pytest

import subscript


@pytest.fixture
def path_to_subscript():
    """ path to installed subscript module."""
    return path.dirname(subscript.__file__)
