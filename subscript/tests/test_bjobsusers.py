import pandas as pd

from .. import bjobsusers


def fake_bjobs(status):
    return "foobar 3*computenode1\nfoobert 1*computenode2\nfoobar 8*computenode3"


def fake_finger(username):
    return "Login: {}          Name: Foo Barrer (foo.bar.com)"


def test_get_jobs():
    jobs_df = bjobsusers.get_jobs("RUN", fake_bjobs)
    assert isinstance(jobs_df, pd.DataFrame)
    assert "ncpu" in jobs_df.columns
    assert "user" in jobs_df.index.name
    assert not jobs_df.empty
    assert len(jobs_df.index.unique()) == len(jobs_df)
    assert jobs_df["ncpu"].sum() > 0


def test_userinfo():
    usersummary = bjobsusers.userinfo("foobar", fake_finger)
    assert isinstance(usersummary, str)
    assert usersummary
    assert "Login" not in usersummary
