import pytest  # noqa: F401
from .. import cli


def test_main():
    _ = cli.main([])
