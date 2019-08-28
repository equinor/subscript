import pytest  # noqa: F401
import os
import sys

import presentvalue


def test_main():
    sys.argv = [
        "presentvalue",
        "--discountto",
        "2001",
        os.path.join(
            os.path.dirname(__file__), "data/reek/eclipse/model/2_R001_REEK-0.DATA"
        ),
    ]
    # We only test that the script actually runs
    presentvalue.main()
    # If stdout is captured, we could do this:
    # assert "PresentValue 11653.94" in stdout  # stdout not captured yet, fixme.
