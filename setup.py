#!/usr/bin/env python3
"""Setup for subscript packages"""
from glob import glob
from os.path import splitext, basename

import setuptools
from setuptools import find_packages


SSCRIPTS = [
    "bjobsusers = subscript.bjobsusers.bjobsusers:main",
    "casegen_upcars = subscript.casegen_upcars.casegen_upcars:main",
    "convert_grid_format = subscript.convert_grid_format.convert_grid_format:main",
    "csv2ofmvol = subscript.csv2ofmvol.csv2ofmvol:main",
    "csvMergeEnsembles = subscript.csv_merge.csv_merge:main_deprecated",
    "csvStack = subscript.csv_stack.csv_stack:main",
    "csv_merge = subscript.csv_merge.csv_merge:main",
    "csv_stack = subscript.csv_stack.csv_stack:main",
    "eclcompress = subscript.eclcompress.eclcompress:main",
    "ecldiff2roff = subscript.ecldiff2roff.ecldiff2roff:main",
    "fmuobs = subscript.fmuobs.fmuobs:main",
    "gen_satfunc = subscript.gen_satfunc.gen_satfunc:main",
    "interp_relperm = subscript.interp_relperm.interp_relperm:main",
    "merge_schedule = subscript.merge_schedule.merge_schedule:main",
    "merge_rft_ertobs = subscript.merge_rft_ertobs.merge_rft_ertobs:main",
    "ofmvol2csv = subscript.ofmvol2csv.ofmvol2csv:main",
    "pack_sim = subscript.pack_sim.pack_sim:main",
    "params2csv = subscript.params2csv.params2csv:main",
    "presentvalue = subscript.presentvalue.presentvalue:main",
    "prtvol2csv = subscript.prtvol2csv.prtvol2csv:main",
    "pvt2csv = subscript.pvt2csv.pvt2csv:main",
    "restartthinner = subscript.restartthinner.restartthinner:main",
    "runrms = subscript.runrms.runrms:main",
    "summaryplot = subscript.summaryplot.summaryplot:main",
    "sw_model_utilities = subscript.sw_model_utilities.sw_model_utilities:main",
    "sunsch = subscript.sunsch.sunsch:main",
    "vfp2csv = subscript.vfp2csv.vfp2csv:main",
]

ERTPLUGINS = [
    "subscript_jobs = subscript.hook_implementations.jobs",
    "CsvMerge = subscript.csv_merge.csv_merge",
    "FmuObs = subscript.fmuobs.fmuobs",
]

LEGACYSCRIPTS = [
    "duf",
    "eclmanual",
    "ertwatch",
    "fmu_copy_revision",
    "list_rms_usage",
    "make_3dgrid_regions",
    "nosim",
    "roxenvbash",
    "runeclipse",
]

REQUIREMENTS = [
    "configsuite",
    "ecl",
    "ecl2df",
    "equinor-libres",
    "ert",
    "matplotlib",
    "numpy",
    "pandas",
    "pyscal",
    "pyyaml",
    "scipy",
    "segyio>1.8.0, <1.9.2",  # 1.9.3 fails on Py3.8
    "xlrd",
    "xtgeo",
]

SETUP_REQUIREMENTS = [
    "setuptools >=28",
    "setuptools_scm",
    "pytest-runner",
    "check-manifest",
]

TEST_REQUIREMENTS = [
    "black>=20.8b0",
    "check-manifest",
    "flake8",
    "pytest",
    "rstcheck",
]
DOCS_REQUIREMENTS = [
    "sphinx",
    "sphinx-argparse",
    "sphinx_rtd_theme",
    "autoapi",
]
EXTRAS_REQUIRE = {"tests": TEST_REQUIREMENTS, "docs": DOCS_REQUIREMENTS}

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
    install_requires=REQUIREMENTS,
    setup_requires=SETUP_REQUIREMENTS,
    entry_points={
        "console_scripts": SSCRIPTS,
        "ert": ERTPLUGINS,
    },
    scripts=["src/subscript/legacy/" + scriptname for scriptname in LEGACYSCRIPTS],
    use_scm_version={"write_to": "src/subscript/version.py"},
    test_suite="tests",
    extras_require=EXTRAS_REQUIRE,
)
