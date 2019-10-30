#!/usr/bin/env python3
"""Setup for subscript packages"""
import setuptools


SSCRIPTS = [
    "bjobsusers = subscript.bjobsusers.bjobsusers:main",
    "csvMergeEnsembles = subscript.csv_merge_ensembles.csv_merge_ensembles:main",
    "csv_merge_ensembles = subscript.csv_merge_ensembles.csv_merge_ensembles:main",
    "csvStack = subscript.csv_stack.csv_stack:main",
    "csv_stack = subscript.csv_stack.csv_stack:main",
    "csv2ofmvol = subscript.csv2ofmvol.csv2ofmvol:main",
    "eclcompress = subscript.eclcompress.eclcompress:main",
    "gen_satfunc = subscript.gen_satfunc.get_satfunc:main",
    "params2csv = subscript.params2csv.params2csv:main",
    "presentvalue = subscript.presentvalue.presentvalue:main",
    "merge_schedule = subscript.merge_schedule.merge_schedule:main",
    "sunsch = subscript.sunsch.sunch:main",
    "summaryplot = subscript.summaryplot.summaryplot:main",
    "interp_relperm = subscript.interp_relperm.interp_relperm:main",
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
    # py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    platforms="any",
    install_requires=[],
    setup_requires=["setuptools >=28", "setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    entry_points={"console_scripts": SSCRIPTS},
    use_scm_version={"write_to": "src/subscript/version.py"},
    test_suite="tests",
)
