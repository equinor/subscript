#!/usr/bin/env python3
"""Setup for subscript packages"""
from glob import glob
from os.path import splitext, basename

import setuptools
from setuptools import find_packages


SSCRIPTS = [
    "bjobsusers = subscript.bjobsusers.bjobsusers:main",
    "convert_grid_format = subscript.convert_grid_format.convert_grid_format:main",
    "csvMergeEnsembles = subscript.csv_merge.csv_merge:main_deprecated",
    "csv_merge = subscript.csv_merge.csv_merge:main",
    "csvStack = subscript.csv_stack.csv_stack:main",
    "csv_stack = subscript.csv_stack.csv_stack:main",
    "csv2ofmvol = subscript.csv2ofmvol.csv2ofmvol:main",
    "eclcompress = subscript.eclcompress.eclcompress:main",
    "gen_satfunc = subscript.gen_satfunc.get_satfunc:main",
    "pack_sim = subscript.pack_sim.pack_sim:main",
    "restartthinner = subscript.restartthinner.restartthinner:main",
    "params2csv = subscript.params2csv.params2csv:main",
    "presentvalue = subscript.presentvalue.presentvalue:main",
    "prtvol2csv = subscript.prtvol2csv.prtvol2csv:main",
    "pvt2csv = subscript.pvt2csv.pvt2csv:main",
    "merge_schedule = subscript.merge_schedule.merge_schedule:main",
    "sunsch = subscript.sunsch.sunsch:main",
    "summaryplot = subscript.summaryplot.summaryplot:main",
    "sw_model_utilities = subscript.sw_model_utilities.sw_model_utilities:main",
    "interp_relperm = subscript.interp_relperm.interp_relperm:main",
]

LEGACYSCRIPTS = [
    "fmu_copy_revision",
    "duf",
    "ertwatch",
    "nosim",
    "runeclipse",
    "list_rms_usage",
]

setuptools.setup(
    name="subscript",
    description="Next-gen resscript",
    author="Equinor",
    author_email="pgdr@equinor.com",
    url="https://github.com/equinor/subscript",
    project_urls={
        "Documentation": "https://subscript.readthedocs.io/",
        "Issue Tracker": "https://github.com/equinor/subscript/issues",
    },
    keywords=[],
    license="Not open source (violating TR1621)",
    platforms="any",
    include_package_data=True,
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    install_requires=[],
    setup_requires=["setuptools >=28", "setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    entry_points={"console_scripts": SSCRIPTS},
    scripts=["src/subscript/legacy/" + scriptname for scriptname in LEGACYSCRIPTS],
    use_scm_version={"write_to": "src/subscript/version.py"},
    test_suite="tests",
)
