# subscript #

Subscript takes over where ResScript left. ResScript worked as the repository for sharing
scripts between subsurface people from its inception in ~2013 to end of Python2 in 2020. 
For the Python 2 to Python 3 transition, code quality and requirements have been elevated
in order to increase maintainability.

* https://wiki.equinor.com/wiki/index.php/ResScript

## Tools in subscript ##

* eclcompress
* summaryplot
* bjobsusers
* csv2ofmvol
* csv_merge_ensembles
* csv_stack
* gen_satfunc
* interp_relperm
* merge_schedule
* params2csv
* presentvalue
* prtvol2csv
* pvt2csv
* sunsch
* vfp2csv

For help, run `<toolname> --help` on your terminal.

## Contributing to subscript ##

* Each tool has its own subdirectory under `src/subscript`. 
* Use `setup.py` for installing endpoints that users should have in their `$PATH`
* Use `argparse`, and with a specific `fill_parser()` function to facilitate `sphinx-argparse`
* Always use the `if __name__ = "__main__"` idiom. Scripts should not start if they are `import`ed, this is to facilitate testing++
* There must be at least test code that directly test that the endpoint is installed and that it does at least something to a standard input. Preferably unit test code for isolated parts of the code as well.
* Docstrings on all functions.

### Code style ###

This section is dedicated to code contributors to subscript.

* subscript shall work in Python 3!

* PEP8 is the rule for naming of files, functions, classes, etc.
  * Convert old code from camelCase style to snake_style unless "impossible"...
  * Keep old script names were camelCase as both camelCase (for backward compatibility) and snake_case
  * The latter will be done by entry points pointing to same script, see e.g. csvStack/csv_stack in setup.py
  * Be compliant
  * Exception is maximum width 88 instead of PEP8's 79; as 88 is the `black` default

* Use the black formatter to format your code
  * `pip install black`
  * black <modulename.py> ... no discussion

* Use pylint to improve coding
  * `pip install pylint`
  * Then run `pylint src`
  * Deviations from default (strict) pylint are stored in .pylintrc at root level, or as comments in the file e.g. `# pylint: disable=broad-except`

## Documentation ##

Install the development requirements
```
pip install -r requirements-dev.txt
```

Then, to build the documentation for subscript run the following command:
```
sphinx-build -b html -nv docs/ build/docs
```

And now you can find the start page of the documentation in the build folder: `build/docs/index.html`
