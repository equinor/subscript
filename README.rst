.. image:: https://img.shields.io/github/workflow/status/equinor/subscript/subscript
    :target: https://github.com/equinor/subscript/actions?query=workflow%3Asubscript

.. image:: https://img.shields.io/lgtm/alerts/g/equinor/subscript.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/equinor/subscript/alerts/

.. image:: https://codecov.io/gh/equinor/subscript/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/equinor/subscript

.. image:: https://img.shields.io/lgtm/grade/python/g/equinor/subscript.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/equinor/subscript/context:python

.. image:: https://img.shields.io/badge/python-3.6%20|%203.7%20|%203.8%20|%203.9-blue.svg
    :target: https://www.python.org

.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
    :target: https://www.gnu.org/licenses/gpl-3.0

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
￼
*********
subscript
*********

Subscript is Equinors collection of scripts used for subsurface reservoir modelling.

Docs are hosted on https://equinor.github.io/subscript/.

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

Copyright 2020 Equinor ASA
