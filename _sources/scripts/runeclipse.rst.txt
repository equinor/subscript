
RUNECLIPSE
==========

Send individual Eclipse simulations to the cluster, by DATA-filename

.. code-block:: console

  usage: runeclipse [-p program] [-q que_name] [-v version] [-x]  [-i] DATAFILE

Positional Arguments
--------------------

:DATAFILE: Path to Eclipse datafile

Named Arguments
---------------

:program: Set to either eclipse or e300, default value: eclipse

:que_name: Set to wanted LSF queue name, default value: daily

:version: Set to wanted valid ECLIPSE version, default: 2018.2

:-x: Force execution on single host for parallel runs

:-i: Selects interactive execution on your local computer

