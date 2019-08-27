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
    install_requires=["click"],
    setup_requires=["setuptools >=28", "setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "subscript = subscript.cli:main",
            "presentvalue = subscript.presentvalue:main",
        ]
    },
    use_scm_version={"write_to": "subscript/version.py"},
)
