import pandas as pd
from typing import List
from pathlib import Path
import yaml

import pytest


from subscript.rmsecl_volumetrics.rmsecl_volumetrics import _compare_volumetrics, main


@pytest.mark.parametrize(
    "disjoint_sets, simvolumes, volumetrics, expected",
    [
        # One set, one region, one zone, one fipnum:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 1, "STOIIP_OIL": 1100}],
            [{"REGION": "A", "ZONE": "U", "STOIIP_OIL": 1000}],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100,
                    "RMS_STOIIP_OIL": 1000,
                    # Positive DIFF means increased from RMS to Eclipse
                    "DIFF_STOIIP_OIL": 100,
                }
            ],
        ),
        # One set, one region, one zone, one fipnum, but no common columns:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 1, "STOIIP_OIL": 1100}],
            [{"REGION": "A", "ZONE": "U", "GIIP_TOTAL": 1000}],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100,
                    "RMS_GIIP_TOTAL": 1000,
                }
            ],
        ),
        # One set, one region, one zone, one fipnum, two common columns:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 1, "STOIIP_OIL": 1100, "GIIP_GAS": 1e9}],
            [
                {
                    "REGION": "A",
                    "ZONE": "U",
                    "STOIIP_OIL": 1000,
                    "GIIP_GAS": 1e9,
                }
            ],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100.0,
                    "RMS_STOIIP_OIL": 1000.0,
                    "ECL_GIIP_GAS": 1.0e9,
                    "RMS_GIIP_GAS": 1.0e9,
                    "DIFF_STOIIP_OIL": 100.0,
                    "DIFF_GIIP_GAS": 0.0,
                }
            ],
        ),
        # One set, one region, one zone, two fipnums:
        (
            [
                {"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1},
                {"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 2},
            ],
            [{"FIPNUM": 1, "STOIIP_OIL": 550}, {"FIPNUM": 2, "STOIIP_OIL": 550}],
            [
                {
                    "REGION": "A",
                    "ZONE": "U",
                    "STOIIP_OIL": 1000,
                }
            ],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100.0,
                    "RMS_STOIIP_OIL": 1000.0,
                    "DIFF_STOIIP_OIL": 100.0,
                }
            ],
        ),
        # One set, two regions, one zone, two fipnums:
        (
            [
                {"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1},
                {"SET": 0, "REGION": "B", "ZONE": "U", "FIPNUM": 2},
            ],
            [{"FIPNUM": 1, "STOIIP_OIL": 550}, {"FIPNUM": 2, "STOIIP_OIL": 550}],
            [
                {
                    "REGION": "A",
                    "ZONE": "U",
                    "STOIIP_OIL": 500,
                },
                {
                    "REGION": "B",
                    "ZONE": "U",
                    "STOIIP_OIL": 500,
                },
            ],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100.0,
                    "RMS_STOIIP_OIL": 1000.0,
                    "DIFF_STOIIP_OIL": 100.0,
                }
            ],
        ),
        # One set, one region, two zones, two fipnums:
        (
            [
                # These disjoint sets are not minimal. The disjoint_sets()
                # code in fipmapper would have said this is two sets.
                {"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1},
                {"SET": 0, "REGION": "A", "ZONE": "L", "FIPNUM": 2},
            ],
            [{"FIPNUM": 1, "STOIIP_OIL": 550}, {"FIPNUM": 2, "STOIIP_OIL": 550}],
            [
                {
                    "REGION": "A",
                    "ZONE": "U",
                    "STOIIP_OIL": 500,
                },
                {
                    "REGION": "A",
                    "ZONE": "L",
                    "STOIIP_OIL": 500,
                },
            ],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 1100.0,
                    "RMS_STOIIP_OIL": 1000.0,
                    "DIFF_STOIIP_OIL": 100.0,
                }
            ],
        ),
        # Two sets, one region, two zones, two fipnums:
        # (this is the same as the one above, but with proper
        # disjoint sets)
        (
            [
                {"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1},
                {"SET": 1, "REGION": "A", "ZONE": "L", "FIPNUM": 2},
            ],
            [{"FIPNUM": 1, "STOIIP_OIL": 550}, {"FIPNUM": 2, "STOIIP_OIL": 550}],
            [
                {
                    "REGION": "A",
                    "ZONE": "U",
                    "STOIIP_OIL": 500,
                },
                {
                    "REGION": "A",
                    "ZONE": "L",
                    "STOIIP_OIL": 500,
                },
            ],
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 550.0,
                    "RMS_STOIIP_OIL": 500.0,
                    "DIFF_STOIIP_OIL": 50.0,
                },
                {
                    "SET": 1,
                    "ECL_STOIIP_OIL": 550.0,
                    "RMS_STOIIP_OIL": 500.0,
                    "DIFF_STOIIP_OIL": 50.0,
                },
            ],
        ),
        # One set, one region, one zone, but the FIPNUM data is mismatched:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 2, "STOIIP_OIL": 1100}],
            [{"REGION": "A", "ZONE": "U", "STOIIP_OIL": 1000}],
            [],
        ),
        # One set, one region, one zone, but the region data is mismatched:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 1, "STOIIP_OIL": 1100}],
            [{"REGION": "B", "ZONE": "U", "STOIIP_OIL": 1000}],
            [],
        ),
        # One set, one region, one zone, but the zone data is mismatched:
        (
            [{"SET": 0, "REGION": "A", "ZONE": "U", "FIPNUM": 1}],
            [{"FIPNUM": 1, "STOIIP_OIL": 1100}],
            [{"REGION": "A", "ZONE": "L", "STOIIP_OIL": 1000}],
            [],
        ),
    ],
)
def test_compare_volumetrics(
    disjoint_sets: List[dict],
    simvolumes: List[dict],
    volumetrics: List[dict],
    expected: List[dict],
):
    comparison_df = _compare_volumetrics(
        pd.DataFrame(disjoint_sets),
        pd.DataFrame(simvolumes).set_index("FIPNUM"),
        pd.DataFrame(volumetrics).set_index(["REGION", "ZONE"]),
    )

    pd.testing.assert_frame_equal(
        comparison_df, pd.DataFrame(expected), check_like=True, check_dtype=False
    )


def test_command_line(tmpdir, mocker):
    tmpdir.chdir()
    Path("FOO.PRT").write_text(
        """
  REPORT   0     1 JAN 2000
                                                =================================
                                                : FIPNUM  REPORT REGION    1    :
                                                :     PAV =        139.76  BARSA:
                                                :     PORV=     27777509.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :          100.                         100.:           200. :           400.           0.           400.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
"""  # noqa
    )
    Path("volumetrics_sim_oil_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv               Stoiip
UpperReek  1                             500.0              400.                300.00              100.40
"""  # noqa
    )
    Path("volumetrics_sim_gas_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv               Giip
UpperReek  1                             500.0              400.                300.00              100.0
"""  # noqa
    )
    Path("fipmap_config.yml").write_text(
        """
fipnum2region:
  1: 1
fipnum2zone:
  1: UpperReek"""
    )
    mocker.patch(
        "sys.argv",
        [
            "rmsecl_volumetrics",
            "FOO.PRT",
            "volumetrics_sim",
            "fipmap_config.yml",
            "--sets",
            "sets.yml",
            "--output",
            "volcomp.csv",
        ],
    )
    main()

    df_fromdisk = pd.read_csv("volcomp.csv")
    print(df_fromdisk.to_dict(orient="records"))
    pd.testing.assert_frame_equal(
        df_fromdisk,
        pd.DataFrame(
            [
                {
                    "SET": 0,
                    "ECL_STOIIP_OIL": 100.0,
                    "ECL_ASSOCIATEDOIL_GAS": 0,
                    "ECL_STOIIP_TOTAL": 100.0,
                    "ECL_WIIP_TOTAL": 200.0,
                    "ECL_GIIP_GAS": 400.0,
                    "ECL_ASSOCIATEDGAS_OIL": 0.0,
                    "ECL_GIIP_TOTAL": 400.0,
                    "RMS_BULK_OIL": 500.0,
                    "RMS_PORV_OIL": 400.0,
                    "RMS_HCPV_OIL": 300.0,
                    "RMS_STOIIP_OIL": 100.4,
                    "RMS_BULK_GAS": 500.0,
                    "RMS_PORV_GAS": 400.0,
                    "RMS_HCPV_GAS": 300.0,
                    "RMS_GIIP_GAS": 100.0,
                    "DIFF_GIIP_GAS": 300.0,
                    "DIFF_STOIIP_OIL": -0.4,
                }
            ]
        ),
        check_like=True,
        check_dtype=False,
    )

    sets_fromdisk = yaml.safe_load(Path("sets.yml").read_text())
    assert sets_fromdisk == {
        0: {"FIPNUM": 1, "REGION": "1", "REGZONE": "1-UpperReek", "ZONE": "UpperReek"}
    }
