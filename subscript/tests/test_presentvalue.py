import pytest  # noqa: F401
import sys

import presentvalue


def test_main():
    # Ouch: Only works when cwd is subscript/subscript. Fixme.
    sys.argv = [
        "presentvalue",
        "--discountto",
        "2001",
        "tests/data/reek/eclipse/model/2_R001_REEK-0.DATA",
    ]
    presentvalue.main()
    # assert "PresentValue 11653.94" in stdout  # stdout not captured yet, fixme.
