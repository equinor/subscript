# encoding: utf-8

import os
import sys

import pandas as pd

import pytest

from .. import bjobsusers


def fake_bjobs(status):
    return "foobar 3*computenode1\nfoobert 1*computenode2\nfoobar 8*computenode3"


def bjobs_errors(status):
    # Example error message from bjobs
    return "LIM not responding"


def fake_finger(username):
    fing = "Login: {}          Name: Foo Barrer (foo.bar.com)"
    if sys.version_info[0] > 2:
        return fing
    else:
        return fing.decode("utf-8")


def fake_finger_unicode(username):
    fing = "Login: {}       Name: Føø Bårrær (foo.latin1.utf8.com)"
    if sys.version_info[0] > 2:
        return fing
    else:
        return fing.decode("utf-8")


def test_real_bjobs():
    """Test the real bjobs command. Can only be expected to
    work on production system interactively"""
    jobs_df = bjobsusers.get_jobs("RUN", bjobsusers.call_bjobs)
    if jobs_df.empty:
        pytest.skip("bjobs command not available, skipping test")
    assert isinstance(jobs_df, pd.DataFrame)
    assert "ncpu" in jobs_df.columns
    assert "user" in jobs_df.index.name

    # The real bjobs is allowed to return empty..
    if not jobs_df.empty:
        assert len(jobs_df.index.unique()) == len(jobs_df)
        assert jobs_df["ncpu"].sum() > 0


def test_get_jobs():
    jobs_df = bjobsusers.get_jobs("RUN", fake_bjobs)
    assert isinstance(jobs_df, pd.DataFrame)
    assert "ncpu" in jobs_df.columns
    assert "user" in jobs_df.index.name
    assert not jobs_df.empty
    assert len(jobs_df.index.unique()) == len(jobs_df)
    assert jobs_df["ncpu"].sum() > 0

    jobs_df = bjobsusers.get_jobs("RUN", bjobs_errors)
    assert isinstance(jobs_df, pd.DataFrame)
    assert jobs_df.empty


def test_userinfo():
    # assert isinstance(fake_finger(''), unicode)  # only relevant for Python 2
    usersummary = bjobsusers.userinfo("foobar", fake_finger)
    assert isinstance(usersummary, str)
    assert "Login" not in usersummary

    # assert isinstance(fake_finger_unicode(''), unicode)  # only relevant for Python 2
    usersummary = bjobsusers.userinfo("foobar", fake_finger_unicode)
    assert isinstance(usersummary, str)
    assert usersummary
    assert "Login" not in usersummary


def test_systemfinger():
    currentuser = os.getlogin()
    if not currentuser:
        return
    usersummary = bjobsusers.userinfo(currentuser, bjobsusers.call_finger)
    assert isinstance(usersummary, str)
    print("Myself is: " + usersummary)
    assert "Login" not in usersummary
