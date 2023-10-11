import importlib
import os
import pkgutil
from typing import Any, Optional

from ert.shared.plugins.plugin_manager import hook_implementation
from ert.shared.plugins.plugin_response import plugin_response

# pylint: disable=no-value-for-parameter


def _get_jobs_from_directory(directory):
    """Do a filesystem lookup in a directory to check
    for available ERT forward models"""
    resource_directory = (
        os.path.dirname(pkgutil.get_loader("subscript").get_filename())
        + "/"
        + directory
    )

    all_files = [
        os.path.join(resource_directory, f)
        for f in os.listdir(resource_directory)
        if os.path.isfile(os.path.join(resource_directory, f))
    ]
    return {os.path.basename(path): path for path in all_files}


@hook_implementation
@plugin_response(plugin_name="subscript")
def installable_jobs():
    """Get the jobs/forward models exposed by subscript"""
    return _get_jobs_from_directory("config_jobs")


@hook_implementation
@plugin_response(plugin_name="subscript")
def installable_workflow_jobs():
    """Get the workflow jobs exposed by subscript"""
    return {}


def _get_module_variable_if_exists(
    module_name: str, variable_name: str, default: str = ""
) -> Any:
    """Grab variables from subscript modules, e.g. for use in docs"""
    try:
        script_module = importlib.import_module(module_name)
    except ImportError:
        return default

    return getattr(script_module, variable_name, default)


@hook_implementation
@plugin_response(plugin_name="subscript")
def job_documentation(job_name: str) -> Optional[dict]:
    """Build documentation for a specific job.

    Return:
        dict:  keys: description, category, examples.
    """
    subscript_jobs = set(installable_jobs().data.keys())
    if job_name not in subscript_jobs:
        return None

    module_name = "subscript.{job_name}.{job_name}".format(job_name=job_name.lower())

    description = _get_module_variable_if_exists(
        module_name=module_name, variable_name="DESCRIPTION"
    )
    examples = _get_module_variable_if_exists(
        module_name=module_name, variable_name="EXAMPLES"
    )
    category = _get_module_variable_if_exists(
        module_name=module_name, variable_name="CATEGORY", default="other"
    )

    return {
        "description": description,
        "examples": examples,
        "category": category,
    }
