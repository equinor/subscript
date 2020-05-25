import os
from pkg_resources import resource_filename

from ert_shared.plugins.plugin_manager import hook_implementation
from ert_shared.plugins.plugin_response import plugin_response


def _get_jobs_from_directory(directory):
    resource_directory = resource_filename("subscript", directory)

    all_files = [
        os.path.join(resource_directory, f)
        for f in os.listdir(resource_directory)
        if os.path.isfile(os.path.join(resource_directory, f))
    ]
    return {os.path.basename(path): path for path in all_files}


@hook_implementation
@plugin_response(plugin_name="subscript")
def installable_jobs():
    return {}


@hook_implementation
@plugin_response(plugin_name="subscript")
def installable_workflow_jobs():
    return {}
