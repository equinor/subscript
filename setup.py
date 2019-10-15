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
    install_requires=[],
    setup_requires=["setuptools >=28", "setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "csvMergeEnsembles = subscript.csvMergeEnsembles:main",
            "csvStack = subscript.csvStack:main",
            "eclcompress = subscript.eclcompress:main",
            "params2csv = subscript.params2csv:main",
            "presentvalue = subscript.presentvalue:main",
            "merge_schedule = subscript.merge_schedule:main",
            "sunsch = subscript.sunsch:main",
        ]
    },
    use_scm_version={"write_to": "subscript/version.py"},
    test_suite="subscript/tests",
)
