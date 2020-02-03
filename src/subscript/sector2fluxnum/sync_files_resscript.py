#!/usr/bin/env python
"""
Utility script to sync files in the resscript repo with ert-statoil repo
"""
import sys
import os
import shutil


old_import_string = "resscript.fluxnum"
new_import_string = "ert_statoil.flux"

source_path_module = "/project/arm/Polymer/Heidrun/Upscaling_project/scripts/resscript/modules/resscript/fluxnum/"
dest_path_module = "/project/arm/Polymer/Heidrun/Upscaling_project/scripts/ert-statoil/lib/python/ert_statoil/flux/"
dest_path_bin = (
    "/project/arm/Polymer/Heidrun/Upscaling_project/scripts/ert-statoil/bin/"
)

source_path_script = [
    "/project/arm/Polymer/Heidrun/Upscaling_project/scripts/resscript/scripts/gen_FLUX_fipnum_region/",
    "/project/arm/Polymer/Heidrun/Upscaling_project/scripts/resscript/scripts/gen_FLUX_fipnum_region_GRF/",
]


module_file_list = [
    "completions.py",
    "fluxfile_obj.py",
    "flux_util.py",
    "well_obj.py",
    "datafile_obj.py",
    "flux_obj.py",
]

script_file_list = ["gen_FLUX_fipnum_region.py", "gen_FLUX_fipnum_region_GRF.py"]


for file_name in module_file_list:
    file_path = source_path_module + file_name
    new_file_path = dest_path_module + file_name
    shutil.copy2(file_path, new_file_path)

file_path = source_path_script[0] + script_file_list[0]
new_file_path = dest_path_bin + script_file_list[0]
shutil.copy2(file_path, new_file_path)

f = open(new_file_path, "r")
newlines = []
for line in f.readlines():
    newlines.append(line.replace(old_import_string, new_import_string))
f.close()

f = open(new_file_path, "w")
for line in newlines:
    f.write(line)
f.close()

file_path = source_path_script[1] + script_file_list[1]
new_file_path = dest_path_bin + script_file_list[1]
shutil.copy2(file_path, new_file_path)

f = open(new_file_path, "r")
newlines = []
for line in f.readlines():
    newlines.append(line.replace(old_import_string, new_import_string))
f.close()

f = open(new_file_path, "w")
for line in newlines:
    f.write(line)
f.close()
