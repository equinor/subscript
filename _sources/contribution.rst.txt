
Contributing to subscript
=========================

Getting started on Equinor Linux computers
------------------------------------------

On Equinor Linux computers, is is recommended to run with the Komodo
environment, which will provide an analogue to ``virtualenv`` for making a
virtual environment.

Follow instructions on
https://fmu-docs.equinor.com/docs/komodo/equinor_komodo_usage.html for
activating a Komodo release, and perform the instructions for extending Komodo
in order a functioning ``pip`` tool.

Getting started as a developer
------------------------------

The first thing to do, is to create a fork of subscript to your personal github
account. Go to https://github.com/equinor/subscript and click the "Fork"
button.

Clone your fork to your local computer:

.. code-block:: console

  git clone git@github.com:<youraccount>/subscript
  cd subscript

Then add the upstream repository:

.. code-block:: console

  git remote add upstream git@github.com:equinor/subscript

This requires a valid login setup with SSH keys for you github account, needed
for write access.

After cloning, you need a Python virtual environment in which you install
subscript and its dependencies. If you develop on an Equinor computer you
should use `komodoenv` as outlined above, if not, you can create a new virtual
environment for subscript using the commands:

.. code-block:: console

  python3 -m venv venv-subscript
  source venv-subscript/bin/activate  # append ".csh" if c-shell

and then run ``pip`` :

.. code-block:: console

  pip install -e ".[tests,docs]"

to install subscript in "edit"-mode together will all the dependencies for
subscript, its test suite and documentation.

A good start is to verify that all tests pass after having cloned the
repository, which you can do by running:

.. code-block:: console

  pytest -n auto


Repository conventions
----------------------

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
* Type hinting is encouraged. If type hinting is included in the source, it has to pass
  mypy.


Maintenance responsibility
--------------------------

* Equinor (PETEC Reservoir Toolbox) maintains the repository infrastructure,
  monitors that automated tests pass on updated dependencies, and ensures
  deploy to Komodo is active.
* Maintenance responsibility for each admitted script (response to bug reports
  and adaptations to changes in dependencies) belongs to the Product Owner
  in Equinor.
* Scripts/changes admitted from actors external to Equinor will be maintained
  by Equinor.
* Unmaintained scripts that fail to pass tests will be removed.

Open source
-----------

Subscript is both open source and closed source. The twin repository
``subscript-internal`` holds similar infrastructure but with scripts that are
exempted from the Open Source requirement in TR1621. Internal or confidental
data should never be submitted to subscript. For each open script, there must
be accompanying public test data.

Code style
----------

* PEP8 is the rule for naming of files, functions, classes, etc. Exception to
  PEP8 is maximum width at 88 instead of PEP8's 79; as 88 is the ``black``
  default

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

* Use "pre-commit" to enforce compliance before commit. Install using ``pip install pre-commit``
  and then run ``pre-commit install`` in the repository root. This will save you from
  pushing code that will fail the code style tests required before merge.

Building documentation
----------------------

Assuming the developer instructions above, run the following command to to
build the documentation for subscript::

  sphinx-build -b html docs build/docs/html

and then point your browser to the file ``build/docs/index.html``.
