ECLCOMPRESS
===========

``eclcompress`` is a command line utility to compress Eclipse grid files using
the Eclipse syntax ``number*value`` so that the dataset::

  0  0  0  1  2  3  2  2  2  2

becomes::

  3*0 1 2 3 4*2

This compression technique is called
`run-length encoding <https://en.wikipedia.org/wiki/Run-length_encoding>`_.

If called with no arguments, a default list of files will be used, equivalent
to specifying a file list like::

  eclipse/include/grid/*
  eclipse/include/regions/*
  eclipse/include/props/*

The ``--verbose`` option is recommended to see what happens, and is default when
run via ERT.


Command line
------------

.. argparse::
   :module: subscript.eclcompress.eclcompress
   :func: get_parser
   :prog: eclcompress

ERT usage
---------

Eclcompress is available as a pre-installed forward model in ERT. In your ERT
config, include::

  FORWARD_MODEL ECLCOMPRESS

between RMS and Eclipse to effectuate compression. If you have a custom file-list,
add that using the FILES argument to the forward model:

.. code-block:: console

  FORWARD_MODEL ECLCOMPRESS(<FILES>=paths_to_compress.txt)

where ``paths_to_compress.txt`` contains a list of files or filepaths to
compress.

.. code-block:: text
  :caption: paths_to_compress.txt

  eclipse/include/grid/*
  eclipse/include/regions/*
  eclipse/include/props/*

Notes
-----

- Existing whitespace (spaces and end-of-lines and such) are not preserved,
  not around '/' characters either.
- Filenames often contains slashes '/', so if the file in question contains
  the INCLUDE keyword it will be skipped and left untouched.
- If there are comments within the data section of a keyword, that
  data section will not be compressed.
- The script is designed for compression of one parameter pr. file, one
  at a time. It can handle more, but the more complex Eclipse syntax you
  put into the files you try to compress, eventually you might encounter
  some bug or limitation. Check the test-function in the source code
  for what it at least can handle.
- The compression factor outputted on the command line and in the header of
  the compressed file, does not take the extra header (two lines) in the
  compressed file into account.
- Eclipse loading time of the compressed file is probably reduced by the
  same factor as the compression factor.
- Only known compressable keywords are compressed.


Possible improvements
---------------------
-  Support for comments inside data sections.
