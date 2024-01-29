import os
from pathlib import Path
from typing import List

import pandas as pd
import pytest
import yaml
from fmu.tools.fipmapper import fipmapper
from subscript.rmsecl_volumetrics.rmsecl_volumetrics import (
    _compare_volumetrics,
    _disjoint_sets_to_dict,
    main,
)


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
    """Test comparisons of example datasets"""
    comparison_df = _compare_volumetrics(
        pd.DataFrame(disjoint_sets),
        pd.DataFrame(simvolumes).set_index("FIPNUM"),
        pd.DataFrame(volumetrics).set_index(["REGION", "ZONE"]),
    )

    pd.testing.assert_frame_equal(
        comparison_df, pd.DataFrame(expected), check_like=True, check_dtype=False
    )


@pytest.mark.parametrize(
    "dframe, expected",
    [
        (
            [{"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1}],
            {0: {"REGION": ["Moon"], "ZONE": ["Soil"], "FIPNUM": [1]}},
        ),
        (
            [
                # Multiple FIPNUMs
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1},
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 2},
            ],
            {0: {"REGION": ["Moon"], "ZONE": ["Soil"], "FIPNUM": [1, 2]}},
        ),
        (
            [
                # Multiple ZONEs
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1},
                {"SET": 0, "REGION": "Moon", "ZONE": "Core", "FIPNUM": 1},
            ],
            {0: {"REGION": ["Moon"], "ZONE": ["Core", "Soil"], "FIPNUM": [1]}},
        ),
        (
            [
                # Sorting:
                {"SET": 0, "REGION": "Moon", "ZONE": "Core", "FIPNUM": 1},
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1},
            ],
            {0: {"REGION": ["Moon"], "ZONE": ["Core", "Soil"], "FIPNUM": [1]}},
        ),
        (
            [
                # Multiple REGIONs
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1},
                {"SET": 0, "REGION": "Venus", "ZONE": "Soil", "FIPNUM": 1},
            ],
            {0: {"REGION": ["Moon", "Venus"], "ZONE": ["Soil"], "FIPNUM": [1]}},
        ),
        (
            [
                # Multiple SETs
                {"SET": 0, "REGION": "Moon", "ZONE": "Soil", "FIPNUM": 1},
                {"SET": 1, "REGION": "Venus", "ZONE": "Soil", "FIPNUM": 2},
            ],
            {
                0: {"REGION": ["Moon"], "ZONE": ["Soil"], "FIPNUM": [1]},
                1: {"REGION": ["Venus"], "ZONE": ["Soil"], "FIPNUM": [2]},
            },
        ),
    ],
)
def test_disjoint_sets_to_dict(dframe: list, expected: dict):
    """Test that disjoint sets can be converted into dictionaries"""
    assert _disjoint_sets_to_dict(pd.DataFrame(dframe)) == expected


def test_documentation_example(tmp_path, mocker):
    """Test the example that is used in the documentation"""
    # pylint: disable=line-too-long
    os.chdir(tmp_path)
    print(f"\nLook in {tmp_path} for input and output to be used in documentation")
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

                                                =================================
                                                : FIPNUM  REPORT REGION    2    :
                                                :     PAV =        139.76  BARSA:
                                                :     PORV=     27777509.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :          200.                         200.:           400. :           800.           0.           800.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
""",  # noqa
        encoding="utf8",
    )
    Path("volumetrics_sim_oil_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv               Stoiip
Upper  West                             500.0              400.                300.00              50.40
Lower  West                             500.0              400.                300.00              50.40
Upper  East                            1000.0              800.                600.00              100.40
Lower  East                            1000.0              800.                600.00              100.40
""",  # noqa
        encoding="utf8",
    )
    Path("volumetrics_sim_gas_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv              Giip
Upper  West                             500.0              400.                300.00              200.40
Lower  West                             500.0              400.                300.00              200.40
Upper  East                            1000.0              800.                600.00              404.40
Lower  East                            1000.0              800.                600.00              404.40
""",  # noqa
        encoding="utf8",
    )
    Path("fipmap_config_1.yml").write_text(
        """
region2fipnum:
  West: [1]
  East: [2]
zone2fipnum:
  Upper: [1, 2]
  Lower: [1, 2]""",
        encoding="utf8",
    )
    Path("fipmap_config_2.yml").write_text(
        """
fipnum2region:
  1: West
  2: East
fipnum2zone:
  1:
   - Upper
   - Lower
  2:
   - Upper
   - Lower""",
        encoding="utf8",
    )
    Path("fipmap_config_3.yml").write_text(
        """
FIPNUM:
  groups:
    REGION:
      West: [1]
      East: [2]
    ZONE:
      Upper: [1, 2]
      Lower: [1, 2]""",
        encoding="utf8",
    )
    mocker.patch(
        "sys.argv",
        [
            "rmsecl_volumetrics",
            "FOO.PRT",
            "volumetrics_sim",
            "fipmap_config_1.yml",
            "--sets",
            "sets.yml",
            "--output",
            "volcomp.csv",
        ],
    )
    main()
    print(Path("sets.yml").read_text(encoding="utf8"))
    print(Path("volcomp.csv").read_text(encoding="utf8"))
    print(pd.read_csv("volcomp.csv"))
    sets_fromdisk = yaml.safe_load(Path("sets.yml").read_text(encoding="utf8"))
    assert sets_fromdisk == {
        0: {"FIPNUM": [2], "REGION": ["East"], "ZONE": ["Lower", "Upper"]},
        1: {"FIPNUM": [1], "REGION": ["West"], "ZONE": ["Lower", "Upper"]},
    }
    mocker.patch(
        "sys.argv",
        [
            "rmsecl_volumetrics",
            "FOO.PRT",
            "volumetrics_sim",
            "fipmap_config_1.yml",
        ],
    )
    main()

    # Run again to get the script output:

    # Test that the three yaml files give the same disjoint sets
    disjoint_sets_1 = fipmapper.FipMapper(
        yamlfile="fipmap_config_1.yml"
    ).disjoint_sets()
    disjoint_sets_2 = fipmapper.FipMapper(
        yamlfile="fipmap_config_2.yml"
    ).disjoint_sets()
    disjoint_sets_3 = fipmapper.FipMapper(
        yamlfile="fipmap_config_3.yml"
    ).disjoint_sets()

    pd.testing.assert_frame_equal(disjoint_sets_1, disjoint_sets_2)
    pd.testing.assert_frame_equal(disjoint_sets_1, disjoint_sets_3)


def test_command_line(tmp_path, mocker):
    """Test the command line utility with options"""
    # pylint: disable=line-too-long
    os.chdir(tmp_path)
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
""",  # noqa
        encoding="utf8",
    )
    Path("volumetrics_sim_oil_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv               Stoiip
UpperReek  1                             500.0              400.                300.00              100.40
""",  # noqa
        encoding="utf8",
    )
    Path("volumetrics_sim_gas_1.txt").write_text(
        """
   Zone      Region index          Bulk                Pore                Hcpv               Giip
UpperReek  1                             500.0              400.                300.00              100.0
""",  # noqa
        encoding="utf8",
    )
    Path("fipmap_config.yml").write_text(
        """
fipnum2region:
  1: 1
fipnum2zone:
  1: UpperReek""",
        encoding="utf8",
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

    sets_fromdisk = yaml.safe_load(Path("sets.yml").read_text(encoding="utf8"))
    assert sets_fromdisk == {0: {"FIPNUM": [1], "REGION": ["1"], "ZONE": ["UpperReek"]}}
