"""Tests associated with generating docs

See also

* .travis.yml which runs rstcheck on all rst-files under docs/
* test_hook_implementations.py which runs rstcheck on inline rst docs generated for ERT.
"""

from pathlib import Path


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

    subdirs = [
        filepath
        for filepath in Path(path_to_subscript).glob("*")
        if filepath.is_dir()
        and filepath.name.replace("./", "") not in exceptions
        and list(Path(filepath).glob("*.py"))
    ]

    for subdir in subdirs:
        assert (subdir / "__init__.py").exists()
