#!/usr/bin/env python
"""The runrms script.

See also the assosiated runrms.yml YAML file paths in SETUP variable.
"""

import argparse
import datetime
import getpass
import json
import logging
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

import yaml

from subscript import detect_os, getLogger

logger = getLogger(__name__)


DESCRIPTION = """
Script to run a rms project from command line, which will in turn use the
'rms...' command OR will look at /prog/roxar/site. Note that not all
options valid for the base script 'rms' should be covered.

* It should understand current RMS version from project and launch correct
  RMS executable
* It should be able to run test versions of RMS
* Set the correct Equinor valid PYTHONPATH.
* Set company wide plugin path

Example of usage:

* runrms newreek.rms10.1.3 (if new project: warn and just start rms default)
* runrms reek.rms10.1.3  (automatically detect version from .master)
* runrms -project reek.10.1.3 (alternative to previous, but using -project as in
  former rms command)
* runrms reek.rms10.1.3 -v 11.0.1 (force version 11.0.1)

Notes:

1. The 'runrms' will be aliased to 'rms' in Equinor after summer 2022. When that
   implemented, running the original 'rms' script can still be done with (where
   the '$' means terminal prompt):

     $ /prog/roxar/rms/rms.

2. For backward compatibility a project name can be prepended with -project.
   Hence, to specify a project use either:
   $ runrms myproject.rms13.0.3
   which is preferred, or

     $ runrms -project myproject.rms13.0.3

   or

     $ runrms --project myproject.rms13.0.3

   If both are used, e.g.:

     $ runrms foo.rms13.0.3 -project bar.rms12.1.2

   then the alternative without -project will 'win', here 'foo.rms13.0.3' and
   a warning will be issued.
"""

try:
    from ..version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"

THISSCRIPT = pathlib.Path(sys.argv[0]).name
RHEL_ID = pathlib.Path("/etc/redhat-release")


# location of setup file; for testing this can be overriden by the --setup argument
SETUP = "/prog/res/roxapi/config/runrms.yml"


def xwarn(mystring):
    """Print a warning with colors."""
    print(_BColors.WARN, mystring, _BColors.ENDC)


def xalert(mystring):
    """Print an alert warning in an appropriate color."""
    print(_BColors.ERROR, mystring, _BColors.ENDC)


def xcritical(mystring):
    """Print an critical error in an appropriate color."""
    print(_BColors.CRITICAL, mystring, _BColors.ENDC)


def get_parser():
    """Make a parser for command line arguments and for documentation."""
    prs = argparse.ArgumentParser(
        description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # positional:
    prs.add_argument("project", type=str, nargs="?", help="RMS project name")

    prs.add_argument(
        "--project",
        "-project",
        dest="project_alt",
        help="RMS project name. Alternative option for backward user experience "
        "compatibility. See details in Note (2) above",
    )

    prs.add_argument(
        "--listversions",
        "-l",
        dest="listversions",
        action="store_true",
        help="Use this option to list current RMS versions available. If this option "
        "is set then all other options are disabled",
    )

    prs.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="If you want to run this script in verbose mode",
    )

    prs.add_argument(
        "--dryrun",
        dest="dryrun",
        action="store_true",
        help="Run this script without actually launching RMS",
    )

    prs.add_argument(
        "--version",
        "-v",
        dest="rversion",
        type=str,
        default=None,
        nargs="?",
        help="RMS version, e.g. 10.1.3",
    )

    prs.add_argument(
        "--beta",
        dest="beta",
        action="store_true",
        help="Will try latest RMS (alpha, beta or test) version, alternative -v latest",
    )

    prs.add_argument(
        "--readonly",
        "-r",
        "-readonly",
        dest="ronly",
        action="store_true",
        help="Read only mode (disable save)",
    )

    prs.add_argument(
        "--dpiscaling",
        "-d",
        dest="sdpi",
        default=100,
        type=float,
        help="Specify RMS DPI display scaling as percent, where 100 is no scaling",
    )

    prs.add_argument(
        "--batch",
        "-batch",
        dest="bworkflows",
        nargs="+",
        type=str,
        help=(
            "Runs project in batch mode (req. project) with workflows as argument(s)"
        ),
    )

    prs.add_argument(
        "--seed",
        "-seed",
        dest="seed",
        nargs=1,
        type=str,
        help=(
            "Runs project with seed number set. Needs to be combined with --batch "
            "and project!"
        ),
    )

    prs.add_argument(
        "--nopy",
        dest="nopy",
        action="store_true",
        help="If you want to run RMS withouth any modication of current PYTHONPATH",
    )

    prs.add_argument(
        "--includesyspy",
        dest="incsyspy",
        action="store_true",
        help="If you want to run RMS and include current "
        "system PYTHONPATH (typically Komodo based)",
    )

    prs.add_argument(
        "--testpylib",
        dest="testpylib",
        action="store_true",
        help="If you want to run RMS and use a test version of the Equinor "
        "installed Python modules for RMS, e.g. test XTGeo (NB special usage!)",
    )

    prs.add_argument(
        "--setup",
        dest="altsetup",
        type=str,
        help="Alternative path to runrms.yml (NB special usage/testing!)",
    )

    return prs


class _BColors:
    # pylint: disable=too-few-public-methods
    # local class for ANSI term color commands

    HEADER = "\033[93;42m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARN = "\033[93;43m"
    ERROR = "\033[93;41m"
    CRITICAL = "\033[1;91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class RunRMS:
    """A class with methods local to this script.

    It is not likely that several instances of the class is required; the
    use of a class here is more for the convinience that 'self' can hold the
    different variables (attributes) across the methods.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        """Instantiate object."""
        self.setup = None
        self.setupfile = None
        self.version_requested = None  # RMS version requested
        self.osver = "x86_64_RH_7"
        self.pythonpath = None  # RMS pythonpath
        self.testpythonpath = None  # RMS pythonpath for testing
        self.tcltkpath = None
        self.pluginspath = None
        self.args = None  # The cmd line arguments
        self.project = None  # The path to the RMS project
        self.version_fromproject = None  # Actual ver from the .master (number/string)
        self.defaultver = None  # RMS default version
        self.fileversion = None  # Internal RMS file version
        self.variant = None  # Executable variant
        self.user = None  # user id
        self.date = None  # Date last opened
        self.time = None  # time last opened
        self.lockf = None  # lockfile
        self.locked = False  # locked (bool)
        self.exe = None  # RMS executable
        self.okext = True  # hmm
        self.extstatus = "OK"
        self.beta = None
        self.rmsinstallsite = None
        self.command = "/prog/roxar/rms/rms"
        self.setdpiscaling = ""
        self.runloggerfile = "/prog/roxar/site/log/runrms_usage.log"
        self.userwarnings = []  # a list of user warnings to display e.g. upgrade ver.
        self.warn_empty_version = False
        self.aps_toolbox_path = None

        self.osver = detect_os(RHEL_ID)

        self.oldpythonpath = ""
        if "PYTHONPATH" in os.environ:
            self.oldpythonpath = os.environ["PYTHONPATH"]

        self.oldpluginspath = ""
        if "RMS_PLUGINS_LIBRARY" in os.environ:
            self.oldpluginspath = os.environ["RMS_PLUGINS_LIBRARY"]

        print(
            _BColors.BOLD,
            "\nRunning <{0}>. Type <{0} -h> for help\n".format(THISSCRIPT),
            _BColors.ENDC,
        )

    def do_parse_args(self, args):
        """Parse command line args."""
        if args is None:
            args = sys.argv[1:]

        myparser = get_parser()
        parsed_args = myparser.parse_args(args)

        # just 'runrms' shall not trigger listing, hence test of len(inargs)
        if (
            parsed_args.rversion is None
            and len(args) > 0
            and ("-v" in args or "--version" in args)
        ):
            parsed_args.listversions = True
            self.warn_empty_version = True

        if parsed_args.project is None and parsed_args.project_alt:
            parsed_args.project = parsed_args.project_alt
        elif parsed_args.project and parsed_args.project_alt:
            xwarn("Conflict use two types of project input. First argument will win!")
            parsed_args.project_alt = None

        if parsed_args.seed and (
            parsed_args.bworkflows is None or parsed_args.project is None
        ):
            xcritical("The --seed option must be combined with --batch and a project!")
            raise SystemExit(" Cannot continue")

        self.args = parsed_args

        if self.args.debug:
            logger.setLevel(logging.DEBUG)

        for key, value in vars(self.args).items():
            logger.debug("Arg = %s: %s", key, value)

    def parse_setup(self):
        """Parse setup YAML file to set specific settings for the requested RMS ver."""
        setup = SETUP
        if self.args.altsetup:
            # allow for user path from command line for testing
            setup = self.args.altsetup

        if not pathlib.Path(setup).is_file():
            xcritical(f"Requested setup <{setup}> does not exist!")
            raise FileNotFoundError

        with open(setup, "r", encoding="utf-8") as stream:
            logger.debug("Actual setup file: %s", setup)
            self.setupfile = setup
            self.setup = yaml.safe_load(stream)

        out = json.dumps(self.setup, sort_keys=True, indent=4, separators=(",", ": "))
        logger.debug("Setup:\n%s", out)

    def requested_rms_version(self):
        """Find requested RMS version, based on various rules.

        * Command line --version is provided, this will win if it exists in setup
        * Version found in given project, if project is provided, and not --version
        * Version marked as default in setup
        """
        proposed_version = None
        default_version = None

        rmssection = "rms"  # in yaml, keep as variable in case rms_nonstandard is used

        for rmsver in self.setup[rmssection]:
            logger.debug("Possible RMS version... %s", rmsver)
            rmsversions = self.setup[rmssection][rmsver]
            if "default" in rmsversions and rmsversions["default"] is True:
                logger.debug("Default found as %s", rmsver)
                proposed_version = rmsver
                default_version = rmsver
                self.defaultver = rmsver

        if self.args.beta:
            self.args.rversion = "latest"

        if self.args.rversion:
            proposed_version = self.args.rversion

        elif self.version_fromproject:
            proposed_version = self.version_fromproject

        if proposed_version not in self.setup[rmssection]:
            xwarn(f"Proposed version {proposed_version} is not in standard setup")
            xwarn("Will try nonstandard... PLEASE USE STANDARD INSTALL IF POSSIBLE")
            if proposed_version not in self.setup["rms_nonstandard"]:
                xwarn(f"Nope, {proposed_version} is not in nonstandard setup either")
                xwarn(f"Will reset to default version {default_version}")
                proposed_version = default_version
            else:
                rmssection = "rms_nonstandard"

        # the proposed version may be ~valid, but it may have a "replaced_by" tag:
        propver = self.setup[rmssection][proposed_version]
        if "replaced_by" in propver:
            newp = propver["replaced_by"]
            msg = f"The requested version {proposed_version} is replaced with {newp}"
            proposed_version = newp
            self.userwarnings.append(msg)

        self.version_requested = proposed_version
        self.exe = self.setup[rmssection][proposed_version].get("exe", None)

        if self.exe is None:
            raise RuntimeError("Executable is not found, probably a config/setup error")

        self._pythonpath_etc_extract(rmssection, proposed_version)

        logger.debug("EXECUTABLE: %s", self.exe)
        logger.debug("PYTHONPATH: %s", self.pythonpath)
        logger.debug("PLUGINSPATH: %s", self.pluginspath)
        logger.debug("TCLTK: %s", self.tcltkpath)
        logger.debug("APS_TOOLBOX_PATH: %s", self.aps_toolbox_path)

    def _pythonpath_etc_extract(self, rmssection, proposed_version):
        """Get the PYTHONPATH etc given various options.

        Set state variables: pythonpath, pluginspath, aps_toolbox_path, tcltkpath
        """
        pypath = self.setup[rmssection][proposed_version].get("pythonpath", None)
        if self.args.testpylib:
            pypath = self.setup[rmssection][proposed_version].get(
                "pythonpathtest", None
            )
            if not pypath:
                raise ValueError("Could not retrieve 'pythonpathtest'")

        if isinstance(pypath, str):
            pypath = [pypath]

        if self.args.incsyspy:
            pypath.append(self.oldpythonpath)

        if self.args.nopy and not self.args.testpylib:
            pypath.pop(0)

        if self.args.nopy and self.args.testpylib:
            raise ValueError("Combing '--nopy' and '--testpylib' is not allowed")

        self.pythonpath = self._process_genericpath(pypath)

        if self.args.testpylib:
            pluginspath = self.setup[rmssection][proposed_version].get(
                "pluginspathtest", None
            )
        else:
            pluginspath = self.setup[rmssection][proposed_version].get(
                "pluginspath", None
            )
        self.pluginspath = self._process_genericpath(pluginspath)

        self.tcltkpath = self.setup[rmssection][proposed_version].get("tcltkpath", None)

        if (pathlib.Path(pypath[0]) / "aps").exists():
            self.aps_toolbox_path = f"{pypath[0]}/aps/toolbox"
        else:
            self.aps_toolbox_path = ""

    def _process_genericpath(self, pypath):
        """Collect and validate input pythonpath/testpythonpath/pluginspath from setup.

        The list in the setup YAML file is a priority list. E.g.
          - /some/main/python3.6/site-packages
          - /some/other/python3.6/site-packages

        Each folder is checked for existence, and omitted if folder is not present.
        If the final list is empty, a warning is made. In the case above, the
        following will be returned:

          "/some/main/python3.6/site-packages:/some/other/python3.6/site-packages"

        """

        pypathlist = []
        if not isinstance(pypath, list):
            # Allow both string and list syntax in yml:
            pypath = [pypath]

        for pyp in pypath:
            if pyp is None:
                continue

            pyp = pyp.replace("<PLATFORM>", self.osver)

            if self.args.dryrun:
                pypathlist.append(pyp)  # in dryrun mode accept non-existing dirs
                continue

            if pathlib.Path(pyp).is_dir():
                pypathlist.append(pyp)
            else:
                xwarn(f"Proposed {pypath} does not exist!")

        if not pypathlist:
            xwarn("No valid in-house PYTHONPATHS are provided")
            return None

        return ":".join(pypathlist)

    def scan_rms(self):  # TODO: reduce complexity
        """Scan the RMS project's .master and returns some basic data needed for launch.

        self.project
        self.locked
        self.lockf
        self.version_fromproject
        """

        def _fsplitter(xline):  # yes... an inner function
            if len(xline) == 3:
                return xline[2]
            return "unknown"

        # first check if folder exists, and issue a warning if not
        myproject = pathlib.Path(self.project)
        if not myproject.is_dir():
            print("Project does not exist, will only launch RMS!")
            self.project = None
            return

        mkeys = ("fileversion", "variant", "user", "date", "time")

        try:
            masterpath = myproject / ".master"
            with open(masterpath, "rb") as master:
                for line in master.read().decode("UTF-8").splitlines():
                    if line.startswith("End GEOMATIC"):
                        break
                    if line.startswith("release"):
                        rel = list(line.split())
                        self.version_fromproject = rel[2]
                        self._complete_version_fromproject()
                    for mkey in mkeys:
                        if line.startswith(mkey):
                            setattr(self, mkey, _fsplitter(line.split()))

        except EnvironmentError as err:
            xcritical("Stop! Cannot open .master file: {}".format(err))
            print("Possible causes:")
            print(" * Project is not existing")
            print(" * Project is corrupt")
            print(" * Project is RMS 2013.0.x version (incompatible with this script)")
            raise SystemExit

        try:
            lockfiletxt = (pathlib.Path(self.project) / "project_lock_file").read_text(
                encoding="utf-8"
            )
            for line in lockfiletxt:
                self.lockf = line.replace("\n", "")
                self.locked = True
                break
        except EnvironmentError:
            pass

        logger.debug("project is %s", self.project)
        logger.debug("version from project is %s", self.version_fromproject)
        logger.debug("lock status from project is %s", self.locked)
        for mkey in mkeys:
            value = getattr(self, mkey)
            logger.debug("MKEY %s: %s", mkey, value)

    def _complete_version_fromproject(self):
        """Get complete RMS version.

        For RMS 10.0.0 and 11.0.0 (etc) the release is reported as
        10 or 11 in the .master file. Extend this to always have 3
        fields e.g. 10 --> 10.0.0.

        For version 14, there is now a V in front
        """

        if self.version_fromproject.startswith("V"):  # e.g. version V14.1
            self.version_fromproject = self.version_fromproject[1:]

        # valid for beta versions:
        if not self.version_fromproject[0].isdigit():
            return

        # officials:
        numdots = self.version_fromproject.count(".")
        rls = self.version_fromproject
        if numdots == 0:
            rls = "{}{}".format(self.version_fromproject, ".0.0")
        elif numdots == 1:
            rls = "{}{}".format(self.version_fromproject, ".0")

        self.version_fromproject = rls

    def launch_rms(self, empty=False):
        """Launch RMS with correct pythonpath, pluginspath etc."""
        args_list = self.exe.split()

        if self.args.ronly:
            args_list.append("-readonly")

        if self.args.bworkflows:
            args_list.append("-batch")
            for bjobs in self.args.bworkflows:
                args_list.append(bjobs)

        if self.args.seed:
            args_list.append("-seed")
            args_list.append(*self.args.seed)

        if not empty:
            args_list += ["-project", self.project]

        # this should override all other settings
        if self.args.listversions:
            args_list = args_list[0:2]  # just to get ['/prog/roxar/rms/rms', '-v']

        self.command = " ".join(args_list)

        print(_BColors.BOLD, "\n -> Launch: {}\n".format(self.command), _BColors.ENDC)

        print("=" * shutil.get_terminal_size((132, 20)).columns)

        self._handle_locked_project()

        if not self.args.listversions:
            if not self.args.debug:
                print(_BColors.OKGREEN)

            rms_exec_env = self._collect_env_settings()

            env_args = ["env"]
            for key, value in rms_exec_env.items():
                env_args.append(f"{key}={value}")

            if shutil.which("disable_komodo_exec"):
                args_list = (
                    [
                        "env",
                        f"PATH_PREFIX={self.setup['roxenv_path']}",
                        "disable_komodo_exec",
                    ]
                    + env_args
                    + args_list
                )
            else:
                args_list = env_args + args_list
            logger.debug("args_list    : %s", args_list)

        if self.args.dryrun:
            xwarn("<<<< DRYRUN, do not start RMS >>>>")
        else:
            rms_process = subprocess.run(args_list, check=True)
            print(_BColors.ENDC)
            return rms_process.returncode

        return None

    def _handle_locked_project(self):
        """Do action if project is locked."""
        if self.locked:
            xwarn(
                "NB! Opening a locked RMS project (you have 5 seconds to press "
                "Ctrl-C to abort)"
            )
            for sec in range(5, 0, -1):
                time.sleep(1)
                print("... {}".format(sec))

    def _collect_env_settings(self):
        """Collect env settings."""
        rms_exec_env = {}
        pythonpathlist = []

        if not self.args.nopy:
            if self.pythonpath:
                pythonpathlist.append(self.pythonpath)
            if self.args.incsyspy:
                pythonpathlist.append(self.oldpythonpath)

        self.pythonpath = ":".join(pythonpathlist)

        logger.debug("Actual PYTHONPATH: %s", self.pythonpath)

        rms_exec_env["PYTHONPATH"] = self.pythonpath

        pluginspathlist = []
        if self.oldpluginspath:
            pluginspathlist.append(self.oldpluginspath)
        if self.pluginspath:
            pluginspathlist.append(self.pluginspath)

        self.pluginspath = ":".join(pluginspathlist)
        rms_exec_env["RMS_PLUGINS_LIBRARY"] = self.pluginspath

        rms_exec_env["RMS_IPL_ARGS_TO_PYTHON"] = "1"

        if self.tcltkpath:
            rms_exec_env["TCL_LIBRARY"] = self.tcltkpath
            rms_exec_env["TK_LIBRARY"] = self.tcltkpath

        if self.setdpiscaling:
            rms_exec_env["QT_SCALE_FACTOR"] = self.setdpiscaling

        if self.aps_toolbox_path:
            rms_exec_env["APS_TOOLBOX_PATH"] = self.aps_toolbox_path

        for key, value in rms_exec_env.items():
            logger.debug("rms_exec_env... %s: %s", key, value)

        return rms_exec_env

    def showinfo(self):
        """Show info on RMS project."""
        print("=" * shutil.get_terminal_size((132, 20)).columns)
        print(f"Script runrms from subscript version {__version__}")
        print("=" * shutil.get_terminal_size((132, 20)).columns)
        print("{0:30s}: {1}".format("Setup for runrms", self.setupfile))
        print("{0:30s}: {1}".format("Project name", self.project))
        print("{0:30s}: {1}".format("Last saved by", self.user))
        print("{0:30s}: {1} {2}".format("Last saved date & time", self.date, self.time))
        print("{0:30s}: {1}".format("Locking info", self.lockf))
        if not self.okext:
            self.userwarnings.append(self.extstatus)
            print(
                "{0:30s}: {2}{1}{3}".format(
                    "File extension status",
                    self.extstatus,
                    _BColors.UNDERLINE,
                    _BColors.ENDC,
                )
            )
        print("{0:30s}: {1}".format("RMS version requested", self.version_requested))
        print("{0:30s}: {1}".format("Equinor current default ver.", self.defaultver))
        print("{0:30s}: {1}".format("RMS version in project", self.version_fromproject))
        print("{0:30s}: {1}".format("RMS internal storage ID", self.fileversion))
        print("{0:30s}: {1}".format("RMS executable variant", self.variant))
        print("{0:30s}: {1}".format("System pythonpath*", self.oldpythonpath))

        order = "first"
        if self.args.testpylib and self.testpythonpath:
            print(
                "{0:30s}: {1}".format(
                    "Test Pypath added as first**", self.testpythonpath
                )
            )
            order = "second"
        print("{0:30s}: {1}".format(f"Pythonpath added as {order}**", self.pythonpath))
        print("{0:30s}: {1}".format("RMS plugins path", self.pluginspath))
        print("{0:30s}: {1}".format("TCL/TK path", self.tcltkpath))
        print("{0:30s}: {1}".format("APS TOOLBOX PATH", self.aps_toolbox_path))
        print("{0:30s}: {1}".format("RMS DPI scaling", self.setdpiscaling))
        print("{0:30s}: {1}".format("RMS executable", self.exe))
        print("=" * shutil.get_terminal_size((132, 20)).columns)
        print("NOTES:")
        print("*   Will be added if --includesyspy option is used")
        print("**  Will be added unless --nopy option is used")
        print("=" * shutil.get_terminal_size((132, 20)).columns)

        if self.userwarnings:
            print()
            xalert("NOTICE!")
            for msg in self.userwarnings:
                xalert(msg)

    def check_vconsistency(self):
        """Check consistency of file extension vs true version."""
        wanted = "rms" + self.version_requested

        if self.version_requested == "latest":
            self.extstatus = "Running latest alpha/beta/test, assume extension is OK..."
            self.okext = True

        # check file name vs release
        elif self.project.endswith(wanted):
            self.extstatus = (
                "Good, project name extension is consistent with actual RMS version"
            )
            self.okext = True
        else:
            self.extstatus = (
                "UPS, project name extension is inconsistent "
                "with actual RMS version: <{}> vs version <{}>"
            ).format(self.project, wanted)
            self.okext = False

    def get_scaledpi(self):
        """Get and check dpiscaling."""
        usedpi = 100
        if self.args.sdpi:
            tmpdpi = self.args.sdpi
            if isinstance(tmpdpi, float) and 20 <= tmpdpi <= 500:
                usedpi = tmpdpi

            self.setdpiscaling = "{}".format(usedpi / 100.0)

    def runlogger(self):
        """Add a line to /prog/roxar/site/log/runrms_usage.log."""
        # date,time,user,host,full_rms_exe,commandline_options

        now = datetime.datetime.now()
        nowtime = now.strftime("%Y-%m-%d,%H:%M:%S")
        user = getpass.getuser()
        host = platform.node()

        myargs = self.command

        lline = "{},{},{},{},{},{}\n".format(
            nowtime, user, host, "client", self.exe, myargs
        )

        if not os.path.isfile(self.runloggerfile):
            # if file is missing, simply skip!
            return

        with open(self.runloggerfile, "a", encoding="utf-8") as logg:
            logg.write(lline)

        logger.debug("Logging usage to %s:", self.runloggerfile)
        logger.debug(lline)


def main(args=None):
    """Run RMS, main script."""
    runner = RunRMS()

    runner.do_parse_args(args)

    runner.parse_setup()

    runner.project = runner.args.project

    if runner.project:
        runner.project = runner.project.rstrip("/")
        runner.scan_rms()

    runner.requested_rms_version()

    emptyproject = True
    if runner.project is not None:
        runner.check_vconsistency()
        emptyproject = False
    else:
        runner.version_fromproject = runner.version_requested

    runner.get_scaledpi()
    if not runner.args.listversions:
        runner.showinfo()
    status = runner.launch_rms(empty=emptyproject)

    logger.debug("Status from subprocess: %s", status)

    if not runner.args.dryrun:
        runner.runlogger()

    if runner.warn_empty_version:
        xwarn(
            "Avoid using empty --version/-v to list RMS versions; rather use "
            "runrms --listversions"
        )
        print("\n")


if __name__ == "__main__":
    main()
