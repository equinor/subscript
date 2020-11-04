*********
subscript
*********

Subscript is Equinors collection of scripts used for subsurface reservoir modelling.

Docs are hosted on https://fmu-docs.equinor.com/docs/subscript (requires Equinor
login).

Using subscript
===============

In Equinor, all subscript utilities are installed on all Linux
computers, and are available in every users path when Komodo is activated::

  source /prog/res/komodo/stable/enable.csh

Remove the ``.csh`` from the line above if you are using *bash* (recommended).

Other users can install using Python setuptools as a developer.
Some subscript tools depend on software
only on Equinor Linux computers and these will not work.


Getting started as developer
============================

Developing subscript tools is recommended to do in a "virtual environment".
In a fresh virtual environment you should be able to do::

  git clone git@github.com:equinor/subscript
  cd subscript
  pip install -e .[tests,docs]

and all dependencies should be installed. Confirm your installation with::

  pytest

and this should run for some minutes without failures.

* `Contributor guidelines <docs/contribution.rst>`_

