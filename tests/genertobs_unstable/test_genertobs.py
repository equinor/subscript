import pytest
from subscript.genertobs_unstable import _config as conf


@pytest.mark.parametrize(
    "table_file_name",
    [
        "drogon_rft_input.ods",
        "drogon_seismic_input.csv",
        "drogon_summary_input.txt",
        "config.ods",
        "summary_gor.csv",
        "summary_wwct.csv",
        "summary_wbhp.csv",
    ],
)
def test_read_tabular_file(drogon_project, table_file_name):
    """Test that parsing of all formats splits correctly the columns"""
    table = conf.read_tabular_file(
        drogon_project / "ert/input/observations/" / table_file_name
    )
    assert table.shape[1] > 1, f"{table_file_name} read as only one column"
