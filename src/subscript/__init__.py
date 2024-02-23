import logging
import sys
from pathlib import Path

try:
    from importlib import metadata

    __version__ = metadata.version(__name__)
except metadata.PackageNotFoundError:
    pass


def detect_os(release_file: Path = Path("/etc/redhat-release")) -> str:
    """Detect operating system string in runtime, just use default if not found."""
    default_os_version = "x86_64_RH_7"

    if release_file.is_file():
        with open(release_file, "r", encoding="utf-8") as buffer:
            tokens = buffer.read().split()
            for t in tokens:
                if "." in t:
                    major = t.split(".")[0]
                    return f"x86_64_RH_{major}"
        raise ValueError("Could not detect RHEL version")
    return default_os_version


def getLogger(module_name="subscript"):
    # pylint: disable=invalid-name
    """Provides a unified logger for subscript scripts.

    Scripts in subscript are encouraged to use logging.info() instead of
    print().

    The logger name will typically be "subscript.prtvol2csv" for the command
    line tool prtvol2csv.

    Subscript scripts can set the level of the entire logger, through the
    setLevel() function. The default level is WARNING. Subscript scripts
    typically accept a --verbose argparse option to set the log level to INFO,
    and a --debug option to set to

    Logging output is split by logging levels (split between WARNING and ERROR)
    to stdout and stderr, each log occurs in only one of the streams. This
    deviates from Unix standard, but is accepted here because few to none
    subscript tool are meant to have their stdout piped into another
    application by default (some of them can, then the programmer and user must
    be careful with log levels).

    Args:
        module_name (str): A suggested name for the logger, usually
            __name__ should be supplied

    Returns:
        A logger object
    """
    if not module_name:
        return getLogger("subscript")

    # This logger is also used by subscript-internal, but we
    # don't want to expose that detail and repo difference in
    # the log output:
    module_name = module_name.replace("subscript_internal", "subscript")

    compressed_name = []
    for elem in module_name.split("."):
        if len(compressed_name) == 0 or elem != compressed_name[-1]:
            compressed_name.append(elem)

    logger = logging.getLogger(".".join(compressed_name))

    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.addFilter(lambda record: record.levelno >= logging.ERROR)
    stderr_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger
