#!/usr/bin/env python3

import setuptools

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
    packages=["subscript"],
    platforms="any",
    include_package_data=True,
    install_requires=[],
    setup_requires=["setuptools >=28", "setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bjobsusers = subscript.bjobsusers:main",
            "csvMergeEnsembles = subscript.csvMergeEnsembles:main",
            "csvStack = subscript.csvStack:main",
            "csv2ofmvol = subscript.csv2ofmvol:main",
            "eclcompress = subscript.eclcompress:main",
            "gen_satfunc = subscript.gen_satfunc:main",
            "params2csv = subscript.params2csv:main",
            "presentvalue = subscript.presentvalue:main",
            "merge_schedule = subscript.merge_schedule:main",
            "sunsch = subscript.sunsch:main",
            "summaryplot = subscript.summaryplot:main",
        ]
    },
    use_scm_version={"write_to": "subscript/version.py"},
    test_suite="subscript/tests",
)
