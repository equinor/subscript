# subscript #

Next-gen resscript

## Index ##

* [Introduction](#introduction)
* [Features](#features)
* [Getting started](#getting-started)
* [Tutorial](#tutorial)
* [Examples](#examples)
* [Code style](#codestyle)

## Features ##

* Prints hello world

## Getting started ##



## Tutorial ##


## Examples ##

### Example 1 ###

## Code style ##

This section is dedicated to code contributors to subscript.

* subscript shall work in Python 3!

* PEP8 is the rule for naming of files, functions, classes, etc.
  * Convert old code from camelCase style to snake_style unless "impossible"...
  * Keep old script names were camelCase as both camelCase (for backward compatibility) and snake_case

  * The latter will be done by entry points pointing to same script, see e.g. csvStack/csv_stack in setup.py
  * Be compliant
  * Excpetion is maximum width 88 instead of PEP8's 79; as 88 is the black default

* Use the black formatter to format your code
  * `pip install black`
  * black <modulename.py> ... no discussion

* Use pylint to improve coding
  * `pip install pylint`
  * Then run `pylint src`
  * Deviations from default (strict) pylint are stored in .pylintrc at root level, or as comments in the file e.g. `# pylint: disable=broad-except`