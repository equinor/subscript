
FMU_COPY_REVISION
=================


.. argparse::
   :module: subscript.fmu_copy_revision.fmu_copy_revision
   :func: get_parser
   :prog: fmu_copy_revision


Copying Profiles
----------------

By default some file types and directories will be skipped. Here are some profiles:

#. Copy everything
#. Copy everything, except:

   * Directories with name ``backup``
   * Directories with name ``users``
   * Directories with name ``attic``
   * Directories and files with names or extension ``.git`` or ``.svn``
   * Files ending with ~
   * Empty folders (except those listed above) will be kept

#. Copy everything, except:

   * All folders and files mentioned in option 2
   * The following folders under ``ert/`` (if they exist):

      * ``output``
      * ``ert/*/storage``, including ``ert/storage`` (for backward compatibility)

   * The following folders or files under ``rms/`` (if they exist):

      * ``input/seismic``, ``model/*.log``

   * The following files under ``rms/`` (if they exist):

      * All files under ``output`` folders (folders will be kept!)

   * The following files and folders under ``spotfire/``:

      * ``input/*.csv``, ``input/*/.csv``, ``model/*.dxp``, ``model/*/*.dxp``

   * The following folders under ``share/``:

      * ``results``
      * ``templates``

   * Empty folders (at destination) except those listed above will kept

#. As profile 3, but also all empty folder (at destination) will removed. This the DEFAULT profile!
#. As profile 3, but keeps more data:

    * Folders and files ``rms/output`` will be kept
    * Folders and files ``share/results`` and share/templates will be kept.

#. Only copy the ``<coviz>`` folder (if present), which shall be under ``<revision>/share/coviz``:

    * Symbolic links will be kept, if possible

#. Make your own filter rules in a named file.

