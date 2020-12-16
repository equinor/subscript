"""Tests associated with generating docs

See also

* .travis.yml which runs rstcheck on all rst-files under docs/
* test_hook_implementations.py which runs rstcheck on inline rst docs generated for ERT.
"""

import os


def test_presence_init_py(path_to_subscript):
    """If __init__.py is missing in a directory (in src/subscript/*),
    everything seems to work fine when in py3 except that sphinx-build will not
    build API docs for it"""

    # Some directories do not need API docs generated, list them here:
    exceptions = [
        "config_jobs",
        "csv_merge_ensembles",  # deprecated name, docs are in csv_merge
        "eclgrid2roff",  # ERT docs placeholder
        "eclinit2roff",  # ERT docs placeholder
        "eclrst2roff",  # ERT docs placeholder.
        "legacy",  # Contains bash scripts.
        "__pycache__",
    ]

    os.chdir(path_to_subscript)
    subdirs = [
        filepath.path
        for filepath in os.scandir(".")
        if filepath.is_dir() and filepath.name.replace("./", "") not in exceptions
    ]

    for subdir in subdirs:
        assert os.path.exists(os.path.join(subdir, "__init__.py"))
