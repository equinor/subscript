#!/usr/bin/env python3

from setuptools import setup

LEGACY_SCRIPTS = [
    "duf",
    "eclmanual",
    "ertwatch",
    "list_rms_usage",
    "nosim",
    "runeclipse",
]
# pyproject.toml deprecates this scripts functionality entirely for
# entry_points (which is simply called "scripts" within it)
setup(scripts=[f"src/subscript/legacy/{script}" for script in LEGACY_SCRIPTS])
