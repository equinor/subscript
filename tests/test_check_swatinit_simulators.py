"""Test the assumptions behind the code in check_swatinit by running reservoir
simulators on mocked reservoir models

This code is not critical to run in a CI context, as it would only uncover
changes in simulators, not the tool check_swatinit.

flow and Eclipse100 does not always yield exactly the same results, for
which this test code has separate code paths for asserts.
"""

import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import res2df
from subscript.check_swatinit.check_swatinit import (
    __HC_BELOW_FWL__,
    __PC_SCALED__,
    __PPCWMAX__,
    __SWATINIT_1__,
    __SWL_TRUNC__,
    __WATER__,
    main,
    make_qc_gridframe,
    qc_volumes,
)
from subscript.check_swatinit.pillarmodel import PillarModel

IN_SUBSCRIPT_GITHUB_ACTIONS = os.getenv("GITHUB_REPOSITORY") == "equinor/subscript"

pd.set_option("display.max_columns", 100)


def run_reservoir_simulator(simulator, resmodel, perform_qc=True):
    """Run the given simulator (Eclipse100 or OPM-flow)
    on a dictionary representing a dynamical reservoir model

    After simulation, runs check_swatinit on the results and
    returns the dataframe with QC information.

    Will write to cwd. Caller is responsible for starting
    in a suitable directory.

    If the simulator fails, the stdout and stderr will be printed.

    Args:
        simulator (string): Path to a working reservoir simulator
            executable
        resmodel (PillarModel): A dynamical reservoir model
        perform_qc (bool): Whether a qc dataframe should be computed
            on the result.
    Returns:
        pd.DataFrame if perform_qc is True, else None
    """
    Path("FOO.DATA").write_text(str(resmodel), encoding="utf8")
    simulator_option = []
    if "runeclipse" in simulator:
        simulator_option = ["-i"]
    if "flow" in simulator:
        simulator_option = ["--parsing-strictness=low"]

    result = subprocess.run(  # pylint: disable=subprocess-run-check
        [simulator] + simulator_option + ["FOO.DATA"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if (
        result.returncode != 0
        and "runeclipse" in simulator
        and "LICENSE FAILURE" in result.stdout.decode() + result.stderr.decode()
    ):
        print("Eclipse failed due to license server issues. Retrying in 30 seconds.")
        time.sleep(30)
        result = subprocess.run(  # pylint: disable=subprocess-run-check
            [simulator] + simulator_option + ["FOO.DATA"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    if result.returncode != 0:
        print(result.stdout.decode())
        print(result.stderr.decode())
        raise AssertionError(f"reservoir simulator failed in {os.getcwd()}")

    if perform_qc:
        return make_qc_gridframe(res2df.ResdataFiles("FOO.DATA"))
    return None


def test_swat_higher_than_swatinit_via_swl_above_contact(simulator, tmp_path):
    """If SWL is set higher than SWATINIT, both Eclipse and flow
    truncates SWAT to SWL.

    QC category is "Water gained"
    """
    os.chdir(tmp_path)
    model = PillarModel(cells=1, apex=1000, owc=[2000], swatinit=[0.3], swl=[0.5])
    qc_frame = run_reservoir_simulator(simulator, model)
    assert qc_frame["QC_FLAG"][0] == __SWL_TRUNC__
    assert np.isclose(qc_frame["SWAT"][0], 0.5)
    assert np.isclose(qc_frame["SWATINIT"][0], 0.3)

    qc_vols = qc_volumes(qc_frame)
    assert np.isclose(qc_vols[__SWL_TRUNC__], (0.5 - 0.3) * qc_frame["PORV"][0])

    if "flow" in simulator:
        expected_ppcw = 12.650095
        assert np.isclose(qc_frame["PPCW"][0], expected_ppcw)  # oip_init=0
    else:
        assert np.isclose(qc_frame["PPCW"][0], 3.0)

    # When SWL is truncated, we cannot trust PC_SCALING to be used to
    # compute PC, so it is removed from the dataframe.
    assert pd.isnull(qc_frame["PC_SCALING"][0])
    assert pd.isnull(qc_frame["PC"][0])


def test_swat_limited_by_ppcwmax_above_contact(simulator, tmp_path):
    """Test PPCWMAX far above contact. This keyword is only supported by Eclipse100
    and will be ignored by flow.

    This leads to water being lost from SWATINIT to SWAT.
    """
    os.chdir(tmp_path)
    swatinit = 0.8
    model = PillarModel(
        cells=1, apex=1000, owc=[1100], swatinit=[swatinit], ppcwmax=[3.01]
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["PPCWMAX"][0], 3.01)
    qc_vols = qc_volumes(qc_frame)
    if "eclipse" in simulator:
        # for PPCWMAX set to 3.01 Eclipse100 will scale the swatinit value to this:
        actual_pc = 1.4226775
        swat_if_ppcwmax = 0.5746147
    else:
        # OPM Flow gives different swat due to different resolution
        # in number of sections to calculate equilibrium
        actual_pc = 1.4051635
        swat_if_ppcwmax = 0.57985145

    assert qc_frame["QC_FLAG"][0] == __PPCWMAX__
    assert np.isclose(qc_frame["SWAT"][0], swat_if_ppcwmax)
    assert np.isclose(qc_frame["PC_SCALING"][0], 3.01 / 3.00)
    assert np.isclose(
        model.evaluate_pc(swat_if_ppcwmax, scaling=3.01 / 3.00), actual_pc
    )
    assert np.isclose(qc_frame["PC"][0], actual_pc)

    assert np.isclose(
        qc_vols[__PPCWMAX__], (swat_if_ppcwmax - swatinit) * qc_frame["PORV"][0]
    )


def test_accepted_swatinit_slightly_above_contact(simulator, tmp_path):
    """Test a "normal" scenario, SWATINIT is accepted and some PC scaling will
    be applied some meters above the contact

    QC-wise, these cells will not be flagged, but contribute to average
    PC_SCALING
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1, apex=1000, owc=[1020], swatinit=[0.5], swl=[0.0], maxpc=[3.0]
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    # E100 is not very accurate here, flow gives exactly 0.5
    assert np.isclose(qc_frame["SWAT"][0], 0.5, atol=0.001)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    # Here, the Pc-curve is scaled (it goes from 3 to 0 in SWOF). At
    # swatinit=0.5, pc_swof is 1.5.

    qc_vols = qc_volumes(qc_frame)
    assert np.isclose(qc_vols[__PC_SCALED__], 0, atol=0.00001)

    if "flow" in simulator:
        # Flow returns the unscaled SWOF input here
        assert np.isclose(qc_frame["PCW"][0], 3.0)

        expected_ppcw = 0.4495535

        assert np.isclose(qc_frame["PPCW"][0], expected_ppcw)

        # This is what it had to be scaled to to reach swatinit.
        assert np.isclose(qc_frame["PC_SCALING"][0], expected_ppcw / 3.0)

        actual_pc = model.evaluate_pc(0.5, scaling=expected_ppcw / 3.0)
        assert np.isclose(actual_pc, 0.22477675)
        assert np.isclose(qc_frame["PC"], actual_pc)
    else:
        # Eclipse100, numbers are a tad different:
        assert np.isclose(qc_frame["PCW"][0], 0.4485523)
        assert np.isclose(qc_frame["PPCW"][0], 0.4485523)
        # (cell centre is 5 meters above contact)
        # Note: For e100, this does not change with oip_init (!)


def test_accepted_swatinit_far_above_contact(simulator, tmp_path):
    """Test a "normal" scenario, SWATINIT is accepted and some PC scaling will
    be applied far above the contact
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1, apex=1000, owc=[1100], swatinit=[0.1], swl=[0.0], maxpc=[3.0]
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["SWAT"][0], 0.1)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__

    qc_vols = qc_volumes(qc_frame)
    assert np.isclose(qc_vols[__PC_SCALED__], 0, atol=0.0001)

    if "flow" in simulator:
        # Flow returns the unscaled SWOF input here
        assert np.isclose(qc_frame["PCW"][0], 3.0)
        expected_ppcw = 1.5612928
        assert np.isclose(
            qc_frame["PPCW"][0], expected_ppcw
        )  # This is what it had to be scaled to to reach swatinit.
        assert np.isclose(qc_frame["PC_SCALING"][0], expected_ppcw / 3.0)

        # The actual Pc value can be back-calculated from SWOF:
        actual_pc = model.evaluate_pc(0.1, scaling=expected_ppcw / 3.0)
        assert np.isclose(actual_pc, 1.4051635)  # in bars.
        assert np.isclose(qc_frame["PC"], actual_pc)
        # At surface conditions, density difference is 200 kg/m3, this number
        # is sort of "close" to 200 kg/m3 * 9.81 m/s^2 * 100 meters / 1e5 = 1.96
        # (mismatch due to Bo and compressibility)
    else:
        # Eclipse100, numbers are only slightly different:
        expected_ppcw = 1.5807527
        assert np.isclose(qc_frame["PCW"][0], expected_ppcw)
        assert np.isclose(qc_frame["PPCW"][0], expected_ppcw)
        assert np.isclose(qc_frame["PC_SCALING"][0], expected_ppcw / 3.0)
        # (cell centre is 5 meters above contact)

        # The actual Pc value can be back-calculated from SWOF:
        actual_pc = model.evaluate_pc(0.1, scaling=expected_ppcw / 3.0)
        assert np.isclose(actual_pc, 1.42267743)
        assert np.isclose(qc_frame["PC"], actual_pc)


def test_accepted_swatinit_in_gas(simulator, tmp_path):
    """Repeat the test above, but with a gas-oil contact below the reservoir cell

    This gives higher capillary pressure (larger scaling) in the single reservoir cell.
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        phases=["OIL", "WATER", "GAS"],
        apex=1000,
        owc=[1100],
        goc=[1050],
        swatinit=[0.1],
        swl=[0.0],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["SWAT"][0], 0.1)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    # Capillary pressure number are the same as when goc is not used:
    if "flow" in simulator:
        # Flow returns the unscaled SWOF input here
        assert np.isclose(qc_frame["PCW"][0], 3.0)
        expected_ppcw = 5.773265
        assert np.isclose(qc_frame["PPCW"][0], expected_ppcw)
        assert np.isclose(qc_frame["PC_SCALING"][0], expected_ppcw / 3.0)
        actual_pc = model.evaluate_pc(0.1, scaling=expected_ppcw / 3.0)
        assert np.isclose(actual_pc, 5.1959385)  # in bars.
        assert np.isclose(qc_frame["PC"], actual_pc)
    else:
        # Eclipse100, numbers are slightly different:
        expected_ppcw = 5.79644012
        assert np.isclose(qc_frame["PCW"][0], expected_ppcw)
        assert np.isclose(qc_frame["PPCW"][0], expected_ppcw)
        actual_pc = model.evaluate_pc(0.1, scaling=expected_ppcw / 3.0)
        assert np.isclose(actual_pc, 5.216796)  # in bars.
        assert np.isclose(qc_frame["PC"], actual_pc)


@pytest.mark.skipif(IN_SUBSCRIPT_GITHUB_ACTIONS, reason="Test require flow dev version")
def test_swatinit_1_far_above_contact(simulator, tmp_path):
    """If SWATINIT is 1 far above the contact, we are in an unstable
    situation (water should not be mobile e.g)

    Eclipse doc says this:
    "If a cell is given saturation corresponding to a zero capillary pressure
    (typically 1.0) above the contact, then the Pc curve cannot be scaled to
    honor the saturation, hence the Pc curve is left unscaled."

    The SWATINIT is effectively ignored by Eclipse100: SWAT is taken from
    the SWOF table and the relevant Pc pressure, and since that Pc curve
    is not touched by SWATINIT, SWAT becomes SWL far above contact.
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1, apex=1000, owc=[2000], swatinit=[1], swl=[0.1], maxpc=[3.0]
    )

    qc_frame = run_reservoir_simulator(simulator, model)

    qc_vols = qc_volumes(qc_frame)

    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__

    # E100/flow ignores SWATINIT and sets the saturation to SWL:
    assert np.isclose(qc_frame["SWAT"][0], 0.1)
    # PPCW is the input Pc:
    assert np.isclose(qc_frame["PPCW"][0], 3.0)
    # Negative number means water is lost:
    assert np.isclose(qc_vols[__SWATINIT_1__], -(1 - 0.1) * qc_frame["PORV"])
    # Not possible to compute PC, it should be Nan:
    assert np.isnan(qc_frame["PC"][0])

    # Bigger reservoir model, so that OWC is within the grid, should
    # not make a difference:
    biggermodel = PillarModel(
        cells=200, apex=1000, owc=[2000], swatinit=[1] * 200, swl=[0.1]
    )
    qc_frame = run_reservoir_simulator(simulator, biggermodel)
    assert set(qc_frame["QC_FLAG"]) == {__SWATINIT_1__, __WATER__}
    assert qc_frame[qc_frame["Z"] < 2000]["QC_FLAG"].unique()[0] == __SWATINIT_1__
    assert qc_frame[qc_frame["Z"] > 2000]["QC_FLAG"].unique()[0] == __WATER__
    # E100/flow ignores SWATINIT and sets the saturation to SWL:
    assert np.isclose(qc_frame["SWAT"][0], 0.1)
    # PPCW is the input Pc:
    assert np.isclose(qc_frame["PPCW"][0], 3.0)
    # Not possible to compute PC, it should be Nan:
    assert np.isnan(qc_frame["PC"][0])


@pytest.mark.skipif(IN_SUBSCRIPT_GITHUB_ACTIONS, reason="Test require flow dev version")
def test_swatinit_1_slightly_above_contact(simulator, tmp_path):
    """If we are slightly above the contact, item 9 in EQUIL plays
    a small role.

    SWATINIT=1 is still ignored above contact, Pc curve is left untouched.
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1, apex=1000, owc=[1030], swatinit=[1], swl=[0.1], oip_init=0
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__
    qc_vols = qc_volumes(qc_frame)
    # Slightly different results between flow and E100
    if "flow" in simulator:
        expected_swat = 0.887824
        actual_pc = 0.37392
    else:
        expected_swat = 0.887849
        actual_pc = 0.3738366

    assert np.isclose(qc_frame["SWAT"][0], expected_swat)
    assert np.isclose(qc_frame["PC"][0], actual_pc)
    assert np.isclose(qc_vols[__SWATINIT_1__], (expected_swat - 1) * qc_frame["PORV"])
    assert model.evaluate_pc(0.1) == 3.0
    assert model.evaluate_pc(1) == 0

    # The actual capillary pressure in this cell:
    assert np.isclose(model.evaluate_pc(expected_swat), actual_pc)

    # Check that if we run without SWATINIT, even flow will give this
    # saturation:
    model.swatinit = [None]  # hacking the model object
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["SWAT"][0], expected_swat, atol=0.001)


def test_capillary_entry_pressure(simulator, tmp_path):
    """With some capillary entry pressure, we should have SWATINIT=1 some
    distance above the contact and also SWAT=1 there. Above the capillary entry
    pressure, both swat and swatinit should be less than 1."""
    os.chdir(tmp_path)

    pc_25m_above_contact = 0.373919 if "flow" in simulator else 0.373836

    model = PillarModel(
        cells=1,
        apex=1000,  # cell extends from 1000 to 1010 m, cell centre 1005
        owc=[1030],
        swatinit=[1],
        swl=[0.1],
        oip_init=0,
        minpc=[pc_25m_above_contact],
        maxpc=[3],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["SWAT"][0], 1)
    assert np.isclose(qc_frame["PPCW"][0], 3)
    assert np.isclose(qc_frame["PC_SCALING"][0], 1)
    assert np.isclose(qc_frame["PC"][0], pc_25m_above_contact)

    # Might not be important whether this is flagged as SWATINIT_1 or
    # PC_SCALED, as the volume difference is zero.
    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__


def test_below_capillary_entry_pressure(simulator, tmp_path):
    """Test what we get below the capillary entry pressure"""
    os.chdir(tmp_path)

    pc_10m_above_contact = 0.150006 if "flow" in simulator else 0.148862

    model = PillarModel(
        cells=1,
        apex=1015,  # The cell is then between 1015 and 1025 m, cell centre 1020
        owc=[1030],
        swatinit=[1],
        swl=[0.1],
        oip_init=0,
        minpc=[pc_10m_above_contact],
        maxpc=[3],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame["SWAT"][0], 1)
    assert np.isclose(qc_frame["PPCW"][0], 3.0)
    assert np.isclose(qc_frame["PC"][0], pc_10m_above_contact)
    assert np.isclose(qc_frame["PC_SCALING"][0], 1.0)

    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__


def test_swatinit_almost1_slightly_above_contact(simulator, tmp_path):
    """The result is discontinuous close to swatinit=1 for Eclipse100, because
    at swatinit = 1 - epsilon, Eclipse will try to scale  the capillary
    pressure, and is only limited by PPCWMAX (but not in this test).

    flow is not discontinuous in SWAT as a function of SWATINIT, but in PPCW as a
    function of SWATINIT.
    """
    os.chdir(tmp_path)

    p_cap = 0.37392 if "flow" in simulator else 0.3738366

    model = PillarModel(cells=1, apex=1000, owc=[1030], swatinit=[0.999], swl=[0.1])
    qc_frame = run_reservoir_simulator(simulator, model)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    assert np.isclose(qc_frame["SWAT"][0], 0.999)
    assert np.isclose(qc_frame["PC"], p_cap, atol=0.001)
    needed_scaling = p_cap / model.evaluate_pc(0.999)
    # Worryingly inaccurate?
    assert np.isclose(qc_frame["PPCW"][0], needed_scaling * 3.0, atol=1)

    qc_vols = qc_volumes(qc_frame)
    assert np.isclose(qc_vols[__PC_SCALED__], 0.0, atol=0.0003)


def test_swatinit_less_than_1_below_contact(simulator, tmp_path):
    """SWATINIT below the contact is ignored, and SWAT is set based on the
    input SWOF table. In water-wet system (pc>0), this always yields SWAT=1
    """
    os.chdir(tmp_path)
    model = PillarModel(cells=1, apex=1000, owc=[900], swatinit=[0.7], swl=[0.1])
    qc_frame = run_reservoir_simulator(simulator, model)
    qc_vols = qc_volumes(qc_frame)
    assert qc_frame["QC_FLAG"][0] == __HC_BELOW_FWL__
    assert np.isclose(qc_frame["SWAT"][0], 1)

    assert np.isclose(qc_vols[__HC_BELOW_FWL__], (1 - 0.7) * qc_frame["PORV"][0])
    if "flow" in simulator:
        assert np.isclose(qc_frame["PPCW"][0], 3.0)
        assert np.isclose(qc_frame["PC_SCALING"][0], 1.0)
        assert np.isclose(qc_frame["PC"], 0)
    else:
        # E100 will not report a PPCW in this case, libecl gives -1e20,
        # which becomes a NaN through res2df and then NaN columns are dropped.
        if "PPCW" in qc_frame:
            assert pd.isnull(qc_frame["PPCW"][0])
        if "PC_SCALING" in qc_frame:
            assert pd.isnull(qc_frame["PC_SCALING"][0])
        if "PC" in qc_frame:
            assert pd.isnull(qc_frame["PC"][0])


@pytest.mark.skipif(IN_SUBSCRIPT_GITHUB_ACTIONS, reason="Test require flow dev version")
def test_swatinit_less_than_1_below_contact_neg_pc(simulator, tmp_path):
    """For an oil-wet system, there can be oil below free water level.

    Flow will set water saturation to 1 no questions asked. Bug?

    Eclipse ignores SWATINIT but calculates SWAT based on the input
    Pc-curve, and can thus give SWAT<1 if pc_min < 0.
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=1000,
        owc=[900],
        swatinit=[0.7],
        swl=[0.1],
        maxpc=[3.0],
        minpc=[-3.0],
    )
    # Eclipse and flow give slightly different value
    if "flow" in simulator:
        expected_swat = 0.7906856
        actual_pc = -1.604571
    else:
        expected_swat = 0.7915066
        actual_pc = -1.610044

    p_cap = model.evaluate_pc(expected_swat)
    assert np.isclose(p_cap, actual_pc)
    qc_frame = run_reservoir_simulator(simulator, model)
    assert qc_frame["QC_FLAG"][0] == __HC_BELOW_FWL__

    qc_vols = qc_volumes(qc_frame)
    if "flow" in simulator:
        assert np.isclose(qc_frame["SWAT"][0], expected_swat)
        assert np.isclose(qc_frame["PPCW"][0], 3.0)
        assert np.isclose(qc_frame["PC_SCALING"][0], 1.0)

        # Computed Pc is wrong here, but is what corresponds
        # to the saturation picked by OPM-flow:
        assert np.isclose(qc_frame["PC"][0], actual_pc)

        assert np.isclose(
            qc_vols[__HC_BELOW_FWL__], (expected_swat - 0.7) * qc_frame["PORV"][0]
        )
    else:
        assert np.isclose(qc_frame["SWAT"][0], expected_swat)
        # PPCW is set to NaN, so we don't have that column
        if "PPCW" in qc_frame:
            assert pd.isnull(qc_frame["PPCW"][0])
        if "PC_SCALING" in qc_frame:
            assert pd.isnull(qc_frame["PC_SCALING"][0])
        if "PC" in qc_frame:
            assert pd.isnull(qc_frame["PC"][0])
        assert np.isclose(qc_frame["PCW"][0], 3.0)  # Untouched input

        assert np.isclose(
            qc_vols[__HC_BELOW_FWL__],
            (expected_swat - 0.7) * qc_frame["PORV"][0],
            atol=0.1,
        )


def test_swu(simulator, tmp_path):
    """Test SWATINIT < SWU < 1.

    Both flow and Eclipse will scale the PC curve according to
    SWU and SWATINIT."""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=900,  # pc is around 1.443238 here.
        owc=[1000],
        swatinit=[0.9],
        swu=[0.95],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    # All good when SWU > SWATINIT
    assert np.isclose(qc_frame["SWAT"][0], 0.9)
    if "flow" in simulator:
        assert np.isclose(qc_frame["PC"][0], 1.442738)
        assert np.isclose(qc_frame["PC_SCALING"], 8.175515)
    else:
        # These PC values are the same for all SWU between SWATINIT and 1
        assert np.isclose(qc_frame["PC"][0], 1.443238)
        # But PPCW goes to infinity as SWU approaches SWATINIT
        assert np.isclose(qc_frame["PC_SCALING"], 8.178345)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__


@pytest.mark.skipif(IN_SUBSCRIPT_GITHUB_ACTIONS, reason="Test require flow dev version")
def test_swu_equal_swatinit(simulator, tmp_path):
    """Test SWU equal to SWATINIT, this is the same as SWATINIT_1

    Eclipse will ignore SWATINIT because it is equal to SWU.
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=900,  # pc is around 1.443238 here.
        owc=[1000],
        swatinit=[0.9],
        swu=[0.9],  # Behaviour in Eclipse is discontinuous at swu=swatinit
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)

    if "flow" in simulator:
        actual_pc = 1.4427379
        expected_swat = 0.51526989
    else:
        actual_pc = 1.443238
        expected_swat = 0.51513567

    swat_from_pc_input = model.evaluate_sw(actual_pc)
    assert np.isclose(swat_from_pc_input, expected_swat)
    assert np.isclose(qc_frame["SWAT"][0], swat_from_pc_input)
    # There is no scaling when SWATINIT==SWU:
    assert np.isclose(qc_frame["PC_SCALING"][0], 1)
    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__
    print(qc_frame)


@pytest.mark.skipif(IN_SUBSCRIPT_GITHUB_ACTIONS, reason="Test require flow dev version")
def test_swu_lessthan_swatinit(simulator, tmp_path):
    """Test SWU equal to SWATINIT

    In Eclipse this looks like the same situation as SWATINIT_1,
    SWATINIT is totally ignored. In flow, it looks like the SWU
    value (which here is the SWOF table endpoint) is ignored
    """
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=900,  # pc is around 1.443238 here.
        owc=[1000],
        swatinit=[0.9],
        swu=[0.8],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)

    if "flow" in simulator:
        actual_pc = 1.4427379
        expected_swat = 0.463361
    else:
        actual_pc = 1.443238
        expected_swat = 0.463244

    swat_from_pc_input = model.evaluate_sw(actual_pc)
    assert np.isclose(swat_from_pc_input, expected_swat)
    assert np.isclose(qc_frame["SWAT"][0], swat_from_pc_input)
    # There is no scaling when SWU < SWATINIT:
    assert np.isclose(qc_frame["PC_SCALING"][0], 1)
    assert qc_frame["QC_FLAG"][0] == __SWATINIT_1__
    print(qc_frame)


def test_swatinit_1_below_contact(simulator, tmp_path):
    """An all-good scenario, below contact, water-wet, ask for water, we get water."""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=1000,
        owc=[100],
        swatinit=[1],
        swl=[0.1],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    assert qc_frame["QC_FLAG"][0] == __WATER__
    assert np.isclose(qc_frame["SWAT"][0], 1)
    if "flow" in simulator:
        assert np.isclose(qc_frame["PPCW"][0], 3.0)
        assert np.isclose(qc_frame["PC"][0], 0)
    else:
        if "PPCW" in qc_frame:
            assert pd.isnull(qc_frame["PPCW"][0])

    qc_vols = qc_volumes(qc_frame)
    assert np.isclose(qc_vols[__WATER__], 0.0)


def test_swlpc_trunc(simulator, tmp_path):
    """SWAT truncated by SWLPC is the same as being truncated by SWL"""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=1000,
        owc=[1020],
        swatinit=[0.1],
        swl=[0.0],
        swlpc=[0.8],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    print(qc_frame)
    if "eclipse" in simulator:
        assert qc_frame["QC_FLAG"][0] == __SWL_TRUNC__
    else:
        # SWLPC is not supported by flow, the SWLPC data is effectively ignored.
        assert qc_frame["QC_FLAG"][0] == __PC_SCALED__


def test_swlpc_correcting_swl(simulator, tmp_path):
    """SWLPC should be allowed to override SWL, so that
    if an SWL value would trigger SWL_TRUNC, we can save the day by SWLPC"""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=1000,
        owc=[1020],
        swatinit=[0.1],
        swl=[0.4],
        swlpc=[0.0],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    print(qc_frame)
    if "eclipse" in simulator:
        assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    else:
        # SWLPC is not supported by flow, the SWLPC data is effectively ignored.
        assert qc_frame["QC_FLAG"][0] == __SWL_TRUNC__


def test_swlpc_scaling(simulator, tmp_path):
    """Test that PC is scaled differently when SWLPC is included"""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        apex=1000,
        owc=[1020],
        swatinit=[0.5],
        swl=[0.0],
        swlpc=[0.4],
        maxpc=[1.0],
    )
    qc_frame = run_reservoir_simulator(simulator, model)
    print(qc_frame)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    if "flow" in simulator:
        # SWLPC is partly supported by flow, the SWLPC data affects PC:
        # assert np.isclose(qc_frame["PC"], 0.224777)  # without SWLPC

        # check_swatinit's PC estimate assumes the SWLPC is in use, and this
        # perturbs the PC estimate, it should have been 0.224777:
        assert np.isclose(qc_frame["PC"], 0.374628)
        assert np.isclose(qc_frame["PC_SCALING"], 0.449553)
    else:
        assert np.isclose(qc_frame["PC"], 0.224276)  # this is independent of SWLPC
        # Without SWLPC, pc_scaling is 0.448552, but when SWLPC=0.4
        # the curve is pushed to the right before it is scaled vertically, and
        # then it must be pushed further down:
        assert np.isclose(qc_frame["PC_SCALING"], 0.269131)


# Gas-water is not supported by flow.
def test_pc_scaled_above_gwc(eclipse_simulator, tmp_path):
    """Test a two-phase gas-water problem, scaled capillary pressure above contact"""

    os.chdir(tmp_path)
    model = PillarModel(
        cells=1,
        phases=["WATER", "GAS"],
        apex=1000,
        owc=[1100],
        swatinit=[0.5],
        swl=[0.1],
        maxpc=[3.0],
    )
    qc_frame = run_reservoir_simulator(eclipse_simulator, model)
    assert qc_frame["QC_FLAG"][0] == __PC_SCALED__
    assert np.isclose(qc_frame["PPCW"][0], 16.913918)
    assert np.isclose(qc_frame["PC"][0], 9.396621)


def test_ppcwmax_gridvector(simulator, tmp_path):
    """Test that ppcwmax_gridvector maps ppcwmax values correctly in the grid"""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=3,
        owc=[1050],
        satnum=[2, 1, 2],
        maxpc=[0.001, 0.002],
        ppcwmax=[0.01, 0.02],
    )
    # NB: Eclipse errors if PPCWMAX is smaller than maxpc pr. SATNUM. Flow does not.
    qc_frame = run_reservoir_simulator(simulator, model)
    assert np.isclose(qc_frame[qc_frame["SATNUM"] == 1]["PPCWMAX"].unique(), 0.01)
    assert np.isclose(qc_frame[qc_frame["SATNUM"] == 2]["PPCWMAX"].unique(), 0.02)


def test_ppcwmax_gridvector_eqlnum(flow_simulator, tmp_path):
    """Test that ppcwmax unrolling also works with EQLNUM (historical bug)"""
    os.chdir(tmp_path)
    model = PillarModel(
        cells=3,
        satnum=[2, 1, 2],
        eqlnum=[3, 2, 1],
        owc=[1051, 1052, 1053],
        maxpc=[0.001, 0.002],
        ppcwmax=[0.01, 0.02],
    )
    qc_frame = run_reservoir_simulator(flow_simulator, model)
    assert qc_frame[qc_frame["SATNUM"] == 1]["PPCWMAX"].unique() == [0.01]
    assert qc_frame[qc_frame["SATNUM"] == 2]["PPCWMAX"].unique() == [0.02]


def test_no_swatinit(tmp_path, mocker, caplog, flow_simulator):
    """Test what check_swatinit does on a case not initialized by SWATINIT"""
    os.chdir(tmp_path)
    model = PillarModel(swatinit=[None])
    run_reservoir_simulator(flow_simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    main()
    assert "INIT-file/deck does not have SWATINIT" in caplog.text


def test_no_filleps(tmp_path, mocker, caplog, flow_simulator):
    """Test the output when we don't have SWL (FILLEPS is needed)"""
    os.chdir(tmp_path)
    model = PillarModel(filleps="")
    run_reservoir_simulator(flow_simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    main()
    assert "SWL not found" in caplog.text
    assert "FILLEPS" in caplog.text


def test_no_unrst(tmp_path, mocker, flow_simulator):
    """Test what happens when there is no restart file with SWAT[0]"""
    os.chdir(tmp_path)
    model = PillarModel()
    run_reservoir_simulator(flow_simulator, model, perform_qc=False)
    os.unlink("FOO.UNRST")
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    with pytest.raises(SystemExit, match="UNRST"):
        main()


def test_no_rptrst(tmp_path, mocker, flow_simulator):
    """Test what happens when RPTRST is not included, no UNRST"""
    os.chdir(tmp_path)
    model = PillarModel(rptrst="")
    run_reservoir_simulator(flow_simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    with pytest.raises(SystemExit, match="UNRST"):
        main()


def test_rptrst_basic_1(simulator, tmp_path, mocker):
    """Test what happens when RPTRST is BASIC=1"""
    os.chdir(tmp_path)
    model = PillarModel(rptrst="BASIC=1")
    run_reservoir_simulator(simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    main()  # No exceptions/errors.


def test_rptrst_allprops(simulator, tmp_path, mocker):
    """Test what happens when RPTRST is ALLPROPS (which probably implies BASIC=1)"""
    os.chdir(tmp_path)
    model = PillarModel(rptrst="ALLPROPS")
    run_reservoir_simulator(simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    main()  # No exceptions.


def test_no_unifout(tmp_path, mocker, flow_simulator):
    """Test what happens when UNIFOUT is not included"""
    os.chdir(tmp_path)
    model = PillarModel(unifout="")
    run_reservoir_simulator(flow_simulator, model, perform_qc=False)
    mocker.patch("sys.argv", ["check_swatinit", "FOO.DATA"])
    with pytest.raises(SystemExit, match="UNIFOUT"):
        main()
