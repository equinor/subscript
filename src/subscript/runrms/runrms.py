#!/usr/bin/env python
"""
The runrms script. See also the assosiated runrms.yml YAML file paths in SETUP variable
"""
import os
import pathlib
import sys
import time
import argparse
import copy
import logging
import shutil
import datetime
import getpass
import platform
import json
import subprocess

import yaml


LOGGER = logging.getLogger("runrms")


DESCRIPTION = """
Script to run a rms project from command line, which will in turn use the
'rms...' command OR will look at /prog/roxar/site. Note that not all
options valid for 'rms' should be covered.

* It should understand current RMS version in project and launch correct RMS executable
* It should be able to run test versions of RMS
* It should be able to set the correct Equinor valid PYTHONPATH.
* Company wide plugin path

Example of usage::

    runrms newreek.rms10.1.3 (if new project: warn and just start rms default)
    runrms reek.rms10.1.3  (automatically detect version from .master)
    runrms -project reek.10.1.3  (same as previous)
    runrms reek.rms10.1.3 -v 11.0.1 (force version 11.0.1)

"""

try:
    from ..version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"

THISSCRIPT = pathlib.Path(sys.argv[0]).name
RHEL_ID = pathlib.Path("/etc/redhat-release")

# where to look for setup/config file
SETUP = [
    "/prog/roxar/rms/versions/runrms.yml",
    "/project/res/roxapi/aux/runrms.yml",
    "tests/data/runrms/runrms.yml",
]

RMS_ENV_PATH_PREFIX = "/project/res/roxapi/bin"


def xwarn(mystring):
    """Print a warning with colors"""
    print(_BColors.WARN, mystring, _BColors.ENDC)


def xerror(mystring):
    """Print an error in an appropriate color"""
    print(_BColors.ERROR, mystring, _BColors.ENDC)


def get_parser():
    """Make a parser for command line arguments and for documentation"""
    prs = argparse.ArgumentParser(description=DESCRIPTION)

    # positional:
    prs.add_argument("project", type=str, nargs="?", help="RMS project name")

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
        help="RMS version, e.g. 10.1.3",
    )

    prs.add_argument(
        "--beta",
        dest="beta",
        action="store_true",
        help="Will try latest RMS (alpha, beta or test) version, alternative -v latest",
    )

    prs.add_argument(
        "--project",
        "-project",
        dest="rproject2",
        type=str,
        help="Name of RMS project (alternative launch)",
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
        help="Spesify RMS DPI display scaling as percent, where 100 is no scaling",
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
    """A class for setting up an environment in which to execute RMS"""

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
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
        self.command = "rms"
        self.setdpiscaling = ""
        self.runloggerfile = "/prog/roxar/site/log/runrms_usage.log"

        self.oldpythonpath = ""
        if "PYTHONPATH" in os.environ:
            self.oldpythonpath = os.environ["PYTHONPATH"]

        print(
            _BColors.BOLD,
            "\nRunning <{0}>. Type <{0} -h> for help\n".format(THISSCRIPT),
            _BColors.ENDC,
        )

    def detect_os(self):
        """Detect operating system string in runtime, just use default if not found"""
        if RHEL_ID.is_dir():
            with open(RHEL_ID, "r") as buffer:
                major = buffer.read().split(" ")[6].split(".")[0].replace("'", "")
                self.osver = "x86_64_RH_" + str(major)
                LOGGER.debug("RHEL version found in %s", RHEL_ID)

    def do_parse_args(self, args):
        """Parse command line args"""
        if args is None:
            args = sys.argv[1:]

        myparser = get_parser()

        args = myparser.parse_args(args)

        self.args = args

        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG)

        for key, value in vars(self.args).items():
            LOGGER.debug("Arg = %s: %s", key, value)

    def parse_setup(self):
        """Parse setup YAML file to set spesific settings for the requested RMS ver"""

        setup = copy.deepcopy(SETUP)
        if self.args.altsetup:
            # allow for user path from command line for testing
            setup.insert(0, self.args.altsetup)

        for mysetup in setup:
            try:
                with open(mysetup, "r") as stream:
                    LOGGER.debug("Actual setup file: %s", mysetup)
                    self.setupfile = mysetup
                    self.setup = yaml.safe_load(stream)
            except FileNotFoundError:
                continue
            else:
                break
        out = json.dumps(self.setup, sort_keys=True, indent=4, separators=(",", ": "))
        LOGGER.debug("Setup:\n%s", out)

    def requested_rms_version(self):
        """
        Find requested RMS version, based on following rules:
        * Command line --version is provided, this will win if it exists in setup
        * Version found in given project, if project is provided, and not --version
        * Version marked as default in setup
        """

        proposed_version = None
        default_version = None

        rmssection = "rms"  # in yaml, keep as variable in case rms_nonstandard is used

        for rmsver in self.setup[rmssection]:
            LOGGER.debug("Possible RMS version... %s", rmsver)
            rmsversions = self.setup[rmssection][rmsver]
            if "default" in rmsversions and rmsversions["default"] is True:
                LOGGER.debug("Default found as %s", rmsver)
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
            xwarn(f"The requested version {proposed_version} is replaced with {newp}")
            proposed_version = newp

        self.version_requested = proposed_version
        self.exe = self.setup[rmssection][proposed_version].get("exe", None)

        if self.exe is None:
            raise RuntimeError("Executable is not found, probably a config/setup error")

        pypath = self.setup[rmssection][proposed_version].get("pythonpath", None)
        pypath = self._process_pypath(pypath)
        self.pythonpath = pypath

        self.tcltkpath = self.setup[rmssection][proposed_version].get("tcltkpath", None)

        LOGGER.debug("EXECUTABLE: %s", self.exe)
        LOGGER.debug("PYTHONPATH: %s", self.pythonpath)
        LOGGER.debug("TCLTK: %s", self.tcltkpath)

    def _process_pypath(self, pypath):
        """The proposed pythonpath from setup may be a list; select from this"""

        if isinstance(pypath, list):
            for pyp in pypath:
                pyp = pyp.replace("<PLATFORM>", self.osver)

                if self.args.dryrun:
                    return pyp + "... DRYRUN FAKE MODE"

                if pathlib.Path(pyp).is_dir():
                    return pyp

        xwarn("Actual python path is not present")
        return None

    def scan_rms(self):  # noqa: C901
        """
        Scan the RMS project's .master and returns some basic data needed
        for launching the RMS project.

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
            xerror("Stop! Cannot open .master file: {}".format(err))
            print("Possible causes:")
            print(" * Project is not existing")
            print(" * Project is corrupt")
            print(" * Project is RMS 2013.0.x version (incompatible with this script)")
            raise SystemExit

        try:
            with open(pathlib.Path(self.project) / "project_lock_file", "r") as lockf:
                for line in lockf.readlines():
                    self.lockf = line.replace("\n", "")
                    self.locked = True
                    break
        except EnvironmentError:
            pass

        LOGGER.debug("project is %s", self.project)
        LOGGER.debug("version from project is %s", self.version_fromproject)
        LOGGER.debug("lock status from project is %s", self.locked)
        for mkey in mkeys:
            value = getattr(self, mkey)
            LOGGER.debug("MKEY %s: %s", mkey, value)

    def _complete_version_fromproject(self):
        """For RMS 10.0.0 and 11.0.0 (etc) the release is reported as
        10 or 11 in the .master file. Extend this to always have 3
        fields e.g. 10 --> 10.0.0
        """

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

    def launch_rms(self, empty=False):  # pylint: disable=too-many-branches # noqa: C901
        """Launch RMS with correct pythonpath"""

        args_list = self.exe.split()

        if self.args.ronly:
            args_list.append("-readonly")
        if self.args.bworkflows:
            args_list.append("-batch")
            for bjobs in self.args.bworkflows:
                args_list.append(bjobs)

        if not empty:
            args_list += ["-project", self.project]

        self.command = " ".join(args_list)
        print(_BColors.BOLD, "\nRunning: {}\n".format(self.command), _BColors.ENDC)
        print("=" * 132)

        if self.locked:
            xwarn(
                "NB! Opening a locked RMS project (you have 5 seconds to press "
                "Ctrl-C to abort)"
            )
            for sec in range(5, 0, -1):
                time.sleep(1)
                print("... {}".format(sec))

        # if not self.args.debug:
        #     print(_BColors.OKGREEN)

        rms_exec_env = os.environ.copy()
        pythonpath = ""
        if not self.args.nopy:
            if self.args.testpylib:
                pythonpath += self.args.testpylib + ":" + self.pythonpath
            else:
                pythonpath += self.pythonpath
            if self.args.incsyspy:
                pythonpath += ":" + self.oldpythonpath

        LOGGER.debug("Actual PYTHONPATH: %s", pythonpath)

        rms_exec_env["PYTHONPATH"] = pythonpath
        rms_exec_env["RMS_IPL_ARGS_TO_PYTHON"] = "1"

        if self.pluginspath:
            rms_exec_env["RMS_PLUGINS_LIBRARY"] = self.pluginspath

        if self.tcltkpath:
            rms_exec_env["TCL_LIBRARY"] = self.tcltkpath
            rms_exec_env["TK_LIBRARY"] = self.tcltkpath

        if self.setdpiscaling:
            rms_exec_env["QT_SCALE_FACTOR"] = self.setdpiscaling

        LOGGER.debug("args_list    : %s", args_list)
        for key, value in rms_exec_env.items():
            LOGGER.debug("rms_exec_env... %s: %s", key, value)

        if shutil.which("disable_komodo_exec"):
            rms_exec_env["PATH_PREFIX"] = RMS_ENV_PATH_PREFIX
            args_list = ["disable_komodo_exec"] + args_list

        if self.args.dryrun:
            xwarn("<<<< DRYRUN, do not start RMS >>>>")
            print(_BColors.ENDC)
        else:
            rms_process = subprocess.run(args_list, env=rms_exec_env, check=True)
            print(_BColors.ENDC)
            return rms_process.returncode

        return None

    def showinfo(self):
        """Show info on RMS project"""

        print("=" * 132)
        print(f"Script runrms from subscript version {__version__}")
        print("=" * 132)
        print("{0:30s}: {1}".format("Setup for runrms", self.setupfile))
        print("{0:30s}: {1}".format("Project name", self.project))
        print("{0:30s}: {1}".format("Last saved by", self.user))
        print("{0:30s}: {1} {2}".format("Last saved date & time", self.date, self.time))
        print("{0:30s}: {1}".format("Locking info", self.lockf))
        if not self.okext:
            print(
                "{0:30s}: {2}{1}{3}".format(
                    "File extension status",
                    self.extstatus,
                    _BColors.UNDERLINE,
                    _BColors.ENDC,
                )
            )

        print("{0:30s}: {1}".format("Setup for runrms", self.setupfile))
        print("{0:30s}: {1}".format("RMS version requested", self.version_requested))
        print("{0:30s}: {1}".format("Equinor current default ver.", self.defaultver))
        print("{0:30s}: {1}".format("RMS version in project", self.version_fromproject))
        print("{0:30s}: {1}".format("RMS internal storage ID", self.fileversion))
        print("{0:30s}: {1}".format("RMS executable variant", self.variant))
        print("{0:30s}: {1}".format("System pythonpath*", self.oldpythonpath))
        print("{0:30s}: {1}".format("Pythonpath added as first**", self.pythonpath))
        print("{0:30s}: {1}".format("RMS plugins path", self.pluginspath))
        print("{0:30s}: {1}".format("TCL/TK path", self.tcltkpath))
        print("{0:30s}: {1}".format("RMS DPI scaling", self.setdpiscaling))
        print("{0:30s}: {1}".format("RMS executable", self.exe))
        print("=" * 132)
        print("NOTES:")
        print("*   Will be added if --includesyspy option is used")
        print("**  Will be added unless --nopy option is used")
        print("=" * 132)

    def check_vconsistency(self):
        """Check consistency of file extension vs true version"""

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
        """Get and check dpiscaling"""

        usedpi = 100
        if self.args.sdpi:
            tmpdpi = self.args.sdpi
            if isinstance(tmpdpi, float) and 20 <= tmpdpi <= 500:
                usedpi = tmpdpi

            self.setdpiscaling = "{}".format(usedpi / 100.0)

    def runlogger(self):
        """Add a line to /prog/roxar/site/log/runrms_usage.log"""

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

        with open(self.runloggerfile, "a") as logg:
            logg.write(lline)

        LOGGER.debug("Logging usage to %s:", self.runloggerfile)
        LOGGER.debug(lline)


def main(args=None):
    """Running RMS version ..."""

    runner = RunRMS()

    runner.do_parse_args(args)

    runner.parse_setup()

    runner.project = runner.args.project
    if runner.args.rproject2:
        runner.project = runner.args.rproject2

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
    runner.showinfo()
    status = runner.launch_rms(empty=emptyproject)

    LOGGER.debug("Status from subprocess: %s", status)

    if not runner.args.dryrun:
        runner.runlogger()


if __name__ == "__main__":
    main()
