
Contributing to subscript
=========================

* The code is hosted on https://github.com/equinor/subscript
* Each tool has its own subdirectory under ``src/subscript``.
* Use ``setup.py`` for installing endpoints that users should have in their ``$PATH``
* Use ``argparse``, and with a specific ``get_parser()`` function to facilitate ``sphinx-argparse``
* Always use the ``if __name__ = "__main__"`` idiom. Scripts should not start if they are
  imported, this is to facilitate testing.
* There must be at least test code that directly test that the endpoint is installed and
  that it does at least something to a standard input. Preferably unit test code for
  isolated parts of the code as well.
* Docstrings on all functions. Docstrings can include RST formatting and will
  be checked for compliance with sphinx on every pull request. Warnings from sphinx
  must be fixed.
* For a new script, write a new file ``docs/scripts/scriptname.rst`` describing
  the script. Use sphinx-argparse to document the command line syntax.

Maintenance responsibility
--------------------------

* Equinor (PETEC Reservoir Toolbox) maintains the repository infrastructure,
  monitoring that automated tests pass on updated dependencies, and ensures
  deploy to Komodo is active.
* Maintenance responsibility for each admitted scripts (response to bug reports
  and adaptations to changes in dependencies) belongs to the Product Owner
  in Equinor.
* Scripts/changes admitted from actors external to Equinor will be maintained
  by Equinor.
* Unmaintained scripts that fail to pass tests will be removed.

Open source
-----------

Subscript is both open source and closed source. The twin repository
``subscript-internal`` holds similar infrastructure but with scripts that are
excepted from the Open Source requirement in TR1621. Internal or confidental
data should never be submitted to subscript. For each open script, there must
be accompanying public test data.

Code style
----------

* subscript shall work in Python 3!
* Python2 compatibility is encouraged throughout 2020, but not required.
* PEP8 is the rule for naming of files, functions, classes, etc.

  * Convert old code from camelCase style to snake_style.
  * Keep old script names with camelCase as both camelCase (for backward compatibility)
    and snake_case
  * The latter will be done by entry points pointing to same script,
    see e.g. csvStack/csv_stack in setup.py
  * Be compliant
  * Exception to PEP8 is maximum width at 88 instead of PEP8's 79; as
    88 is the `black` default

* Use the black formatter to format your code

  * ``pip install black``
  * ``black <modulename.py>``, must be done prior to any pull request.

* Use flake8 code checker

  * ``pip install flake8``
  * ``flake8 src tests`` must pass before any pull request is accepted
  * Exceptions are listed in ``setup.cfg``

* Use pylint to improve coding

  * ``pip install pylint``
  * Then run ``pylint src``
  * Deviations from default (strict) pylint are stored in ``.pylintrc`` at root level,
    or as comments in the file e.g. ``# pylint: disable=broad-except``.
  * Only use deviations when e.g. black and pylint are in conflict, or if conformity with
    pylint would clearly make the code worse or not work at all. Do not use it to
    increase pylint score.

Building documentation
----------------------

Install the development requirements::

  pip install .[tests]

Then, to build the documentation for subscript run the following command::

  sphinx-build -W -b html -nv docs/ build/docs

And now you can find the start page of the documentation in the
build folder: ``build/docs/index.html``
