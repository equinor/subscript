import logging

import subscript


def test_subscriptlogger_name():
    """Test that the subscript logger can compute a correct name for itself"""
    assert subscript.getLogger().name == "subscript"
    assert subscript.getLogger("").name == "subscript"
    assert subscript.getLogger("subscript.eclcompress").name == "subscript.eclcompress"
    assert (
        subscript.getLogger("subscript.eclcompress.eclcompress").name
        == "subscript.eclcompress"
    )
    assert (
        subscript.getLogger("subscript.eclcompress.eclcompress.eclcompress").name
        == "subscript.eclcompress"
    )
    assert (
        subscript.getLogger("subscript.eclcompress.eclcompress.somesubmodule").name
        == "subscript.eclcompress.somesubmodule"
    )

    assert subscript.getLogger("subscript_internal").name == "subscript"
    assert (
        subscript.getLogger("subscript_internal.completor").name
        == "subscript.completor"
    )
    assert (
        subscript.getLogger("subscript_internal.completor.sub").name
        == "subscript.completor.sub"
    )


def test_default_logger_levels(capsys):
    """Verify that the intended usage of this logger have expected results"""

    # Scripts should start with this:
    logger = subscript.getLogger("test_levels")

    logger.debug("This DEBUG is not to be seen")
    captured = capsys.readouterr()
    assert "DEBUG" not in captured.out
    assert "DEBUG" not in captured.err

    logger.info("This INFO is not to be seen by default")
    captured = capsys.readouterr()
    assert "INFO" not in captured.out
    assert "INFO" not in captured.err

    logger.warning("This WARNING is to be seen")
    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert "WARNING" not in captured.err

    logger.error("This ERROR should only be in stderr")
    captured = capsys.readouterr()
    assert "ERROR" not in captured.out
    assert "ERROR" in captured.err


def test_script_verbose_mode(capsys):
    """Some scripts accept a --verbose option, which usually
    mean that logging should be at INFO level"""
    logger = subscript.getLogger("test_verbose")
    logger.setLevel(logging.INFO)

    logger.info("This INFO is to be seen")
    captured = capsys.readouterr()
    assert "INFO" in captured.out


def test_script_debug_mode(capsys):
    """Some scripts accept a --verbose option, which usually
    mean that logging should be at INFO level"""
    logger = subscript.getLogger("test_debug")
    logger.setLevel(logging.DEBUG)

    logger.info("This DEBUG is to be seen")
    captured = capsys.readouterr()
    assert "DEBUG" in captured.out
