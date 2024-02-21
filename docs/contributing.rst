Contributing
============

Thanks for considering contributing to subscript! All contributions are
welcome. This document is meant to help you get started and contains some
guidelines that must be met before a contribution can be accepted.


Getting started
---------------

We recommend developing from a personal fork rather than branches on the
upstream repository. Create a fork from the repository and then clone it 
to your machine:

.. code-block:: console

  git clone git@github.com:<youraccount>/subscript
  cd subscript

Then add the upstream repository:

.. code-block:: console

  git remote add upstream git@github.com:equinor/subscript

After cloning, you need a Python virtual environment in which you install 
subscript and its dependencies. If you develop on an Equinor computer you
should use ``komodoenv``; instructions for how to do this can be found
`here <https://fmu-docs.equinor.com/docs/komodo/equinor_komodo_usage.html>`_
(internal). Otherwise, set up a normal virtual environment.

.. code-block:: console

  python3 -m venv venv-subscript
  source venv-subscript/bin/activate  # append ".csh" if c-shell

and then upgrade and install the dependencies with ``pip``:

.. code-block:: console

  pip install -U pip
  pip install -e ".[tests,docs]"

to install subscript in "edit"-mode together will all the dependencies for
subscript, its test suite, and documentation dependencies.

A good start is to verify that all tests pass after having cloned the
repository, which you can do by running:

.. code-block:: console

  pytest -n auto

If you want to run the full test-suite within the Equinor Linux environment
you can invoke the test run in the following manner. This will include
running tests that rely upon a black oil simulation.

.. code-block:: console

  # running on redhat 7
  pytest -n auto --flow-simulator="/project/res/x86_64_RH_7/bin/flowdaily" --eclipse-simulator="runeclipse"

  # running on redhat 8
  pytest -n auto --flow-simulator="/project/res/x86_64_RH_8/bin/flowdaily" --eclipse-simulator="runeclipse"

Code style
----------

Before making a pull request you should verify that your changes will pass
the linting done in CI:

 .. code-block:: console

  ruff . 
  ruff format .
  mypy src/subscript
  rstcheck -r docs


Documentation
-------------

Ensure the documentation is up-to-date with your changes. You can build and
view the documentation like so:

 .. code-block:: console

  sphinx-build -b html docs build/docs/html
  firefox build/docs/html/index.html


Repository conventions
----------------------

* Each tool has its own subdirectory under ``src/subscript``.
* Use ``pyproject.toml`` for installing endpoints that users should have in 
  their ``$PATH``
* Use ``argparse``, and with a specific ``get_parser()`` function to facilitate 
  ``sphinx-argparse``
* Always use the ``if __name__ = "__main__"`` idiom. Scripts should not start 
  if they are imported, this is to facilitate testing.
* There must be at least test code that directly test that the endpoint is 
  installed and that it does at least something to a standard input. Preferably
  unit test code for isolated parts of the code as well.
* Docstrings on all functions. Docstrings can include RST formatting and will
  be checked for compliance with sphinx on every pull request. Warnings from 
  sphinx must be fixed.
* For a new script, write a new file ``docs/scripts/scriptname.rst`` describing
  the script, its usage, and examples. Use sphinx-argparse to document the 
  command line syntax.
* Type hinting is encouraged. If type hinting is included in the source, it has
  to pass mypy.
