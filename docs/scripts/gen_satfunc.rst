
GEN_SATFUNC
===========

*gen_satfunc is provided for backwards compatibility. PYSCAL is the recommended
tool for relperm include file generation*

The gen_satfunc.py can create a SWOF/SGOF include file based on LET-parameters,
initial water saturation, residual oil saturation and Krwo. The script requires
a simple configuration file as an input (example below) and returns a SWOF/SGOF
include file that you can directly include in Eclipse. The script can both be
beneficial in a manual setting where you want to test various relative
permeabilities, or in an automatic fashion where the configuration file is used
as a template for a forward model job.

.. argparse::
   :module: subscript.gen_satfunc.gen_satfunc
   :func: get_parser
   :prog: gen_satfunc

Configuration file
------------------

There are only 4 keywords allowed in the configuration file:

- ``SWOF`` *no arguments*
- ``SGOF`` *no arguments*
- ``COMMENT`` {some comment to print in the output file}
- ``RELPERM {Lw, Ew, Tw, Lo, Eo, To, Sorw, Swirr, Krwo, num_sw_steps} [PORO, a, b, sigma_costau]``

Required input are the LET-parameters for the oil and water (or gas) relative
permeability curves, as well as the irreducible water saturation, the remaining
oil saturations and Krwo.

Optionally you may specify a permeability (mD), porosity (-), a & b
petrophysical J-function fitting parameters and the interfacial tension
sigma_costau (mN/m). These inputs will be used to calculated the capillary
pressure. Currently, some Heidrun specific values for the capillary pressure
calculation are hard-coded in the source code. When you require the calculation
of capillary pressure please contact the script author.  In addition to these
keywords you can add comments freely throughout the config file similar to
comments in Eclipse files (that is, using to dashed --).

The following example config file can be used to generate a SWOF file with 4
relative permeability curves:

Example configuration file for gen_satfunc.py::

  COMMENT Relperm curve for fantasy field
  SWOF
  RELPERM 4 2 1   3 2 1   0.15 0.10 0.5 20
  RELPERM 4 1 1   4 2 1   0.14 0.12 0.3 20
  RELPERM 4 3 1   3 3 1   0.13 0.11 0.6 20
  RELPERM 4 1 0.5 3 2 0.5 0.16 0.09 0.4 20

