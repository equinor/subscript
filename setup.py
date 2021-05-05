#!/usr/bin/env python3

"""Setup for subscript packages"""
from glob import glob
from os.path import splitext, basename

import setuptools


SSCRIPTS = [
    "bjobsusers = subscript.bjobsusers.bjobsusers:main",
    "casegen_upcars = subscript.casegen_upcars.casegen_upcars:main",
    "check_swatinit = subscript.check_swatinit.check_swatinit:main",
    "convert_grid_format = subscript.convert_grid_format.convert_grid_format:main",
    "csv2ofmvol = subscript.csv2ofmvol.csv2ofmvol:main",
    "csvStack = subscript.csv_stack.csv_stack:deprecated_main",
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
    "restartthinner = subscript.restartthinner.restartthinner:main",
    "ri_wellmod = subscript.ri_wellmod.ri_wellmod:main",
    "runrms = subscript.runrms.runrms:main",
    "summaryplot = subscript.summaryplot.summaryplot:main",
    "sw_model_utilities = subscript.sw_model_utilities.sw_model_utilities:main",
    "sunsch = subscript.sunsch.sunsch:main",
    "vfp2csv = subscript.vfp2csv.vfp2csv:main",
    "welltest_dpds = subscript.welltest_dpds.welltest_dpds:main",
]

ERTPLUGINS = [
    "subscript_jobs = subscript.hook_implementations.jobs",
    "CsvMerge = subscript.csv_merge.csv_merge",
    "CsvStack = subscript.csv_stack.csv_stack",
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
    "opm==2020.10.2",
    "pandas",
    "protobuf",
    "pyscal",
    "pyyaml",
    "rips",
    "scipy",
    "seaborn",
    "segyio",
    "xlrd",
    "xtgeo",
]

SETUP_REQUIREMENTS = [
    "setuptools >=28",
    "setuptools_scm",
    "pytest-runner",
    "check-manifest",
]

with open("test_requirements.txt") as f:
    test_requirements = f.read().splitlines()
with open("docs_requirements.txt") as f:
    docs_requirements = f.read().splitlines()

EXTRAS_REQUIRE = {"tests": test_requirements, "docs": docs_requirements}

setuptools.setup(
    name="subscript",
    description="Next-gen resscript",
    author="Equinor",
    author_email="havb@equinor.com",
    url="https://github.com/equinor/subscript",
    project_urls={
        "Documentation": "https://equinor.github.io/subscript",
        "Issue Tracker": "https://github.com/equinor/subscript/issues",
    },
    keywords=[],
    license="GPLv3",
    platforms="any",
    include_package_data=True,
    packages=setuptools.find_packages("src"),
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
