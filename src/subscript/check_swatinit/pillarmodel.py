import textwrap
from typing import List, Optional, Union

import numpy as np


class PillarModel:
    """Represents a simple Eclipse reservoir model with one or more
    rectangular cells stacked on top of each other.

    The reservoir model is parametrizable in terms of options related
    to SWATINIT analysis"""

    # pylint: disable=too-many-arguments,too-many-instance-attributes,too-many-locals
    def __init__(
        self,
        cells: int = 1,
        apex: int = 1000,
        phases: Optional[List[str]] = None,
        perm: Optional[List[float]] = None,
        poro: Optional[List[float]] = None,
        swatinit: Optional[List[float]] = None,
        satnum: Optional[List[int]] = None,  # one value pr. cell
        swl: Optional[List[float]] = None,  # first saturation in swof, one pr. satnum
        swlpc: Optional[
            List[float]
        ] = None,  # swl scaler for pc only, leaving kr unmodified
        swu: Optional[List[float]] = None,  # maximum saturation in swof, one pr. satnum
        maxpc: Optional[List[float]] = None,  # max pc in SWOF
        minpc: Optional[List[float]] = None,  # pc at sw=1 in SWOF
        ppcwmax: Optional[List[float]] = None,  # PPCWMAX keyword.
        eqlnum: Optional[List[int]] = None,  # One value pr cell
        owc: Optional[
            List[float]
        ] = None,  # One value pr. eqlnum region, also used for gwc.
        goc: Optional[
            Union[List[float], List[str]]
        ] = None,  # One value pr. eqlnum region
        oip_init: int = 0,  # EQUIL item 9. Eclipse default is -5
        filleps: str = "FILLEPS",
        rptrst: str = "ALLPROPS",
        unifout: str = "UNIFOUT",
    ):
        """Set up a reservoir grid and dynamic model that can be
        exported as an Eclipse deck.

        This particular class is tailored for SWATINIT analysis.
        """
        self.cells = cells
        if phases is None:
            self.phases = {"OIL", "WATER"}
        else:
            self.phases = set(phases)

        if perm is None:
            self.perm = [100.0] * self.cells
        else:
            self.perm = perm
        assert len(self.perm) == self.cells

        if poro is None:
            self.poro = [0.2] * self.cells
        else:
            self.poro = poro
        assert len(self.poro) == self.cells

        # PROPS:
        if satnum is None:
            self.satnum = [1] * self.cells
        else:
            self.satnum = satnum

        if swl is None:
            self.swl = [0.1] * max(self.satnum)
        else:
            self.swl = swl
        # SWL is pr. SATNUM, not pr. cell in this class
        assert len(self.swl) == max(self.satnum)

        if swlpc is None:
            self.swlpc = None
        else:
            self.swlpc = swlpc
            # SWLPC is pr. cell
            assert len(self.swlpc) == self.cells

        if swu is None:
            self.swu = [1.0] * max(self.satnum)
        else:
            self.swu = swu
        # SWU is pr. SATNUM, not pr. cell in this class
        assert len(self.swu) == max(self.satnum)

        if maxpc is None:
            self.maxpc = [3.0] * max(self.satnum)
        else:
            self.maxpc = maxpc
        assert len(self.maxpc) == max(self.satnum)

        if minpc is None:
            self.minpc = [0.0] * max(self.satnum)
        else:
            self.minpc = minpc
        assert len(self.minpc) == max(self.satnum)

        self.ppcwmax = ppcwmax  # if None is handled later

        # EQUIL:
        if eqlnum is None:
            self.eqlnum = [1] * self.cells
        else:
            self.eqlnum = eqlnum
        assert len(self.eqlnum) == self.cells

        if owc is None:
            self.owc = [1000.0] * max(self.eqlnum)
        else:
            self.owc = owc

        self.goc: Union[List[str], List[float]]
        if goc is None:
            self.goc = ["1*"] * max(self.eqlnum)
        else:
            self.goc = goc

        assert len(self.owc) == max(self.eqlnum)
        assert len(self.goc) == max(self.eqlnum)

        self.oip_init = oip_init

        self.apex = apex

        cellheight = 10
        self.cellheights = [cellheight] * self.cells  # DZ keyword
        self.tops = self.apex + np.cumsum(self.cellheights) - cellheight

        self.filleps = filleps

        self.rptrst = rptrst

        self.unifout = unifout

        # Cell midpoints:
        self.midpoints = self.tops + np.array(self.cellheights) / 2.0

        if swatinit is not None:
            self.swatinit = swatinit
        # Note: swatinit being a list of None is ok, means
        # we should not output SWATINIT keyword.
        else:
            # Mock a SWATINIT (constant above contact)
            self.swatinit = [0] * self.cells
            for cell_idx, _ in enumerate(self.midpoints):
                if self.midpoints[cell_idx] <= self.owc[self.eqlnum[cell_idx] - 1]:
                    self.swatinit[cell_idx] = 0.4
                else:
                    self.swatinit[cell_idx] = 1.0

    def __repr__(self) -> str:
        """Make an Eclipse deck"""

        string = ""

        string += self.runspec() + "\n"

        string += self.grid() + "\n"

        string += self.props() + "\n"

        string += self.regions() + "\n"

        string += self.solution() + "\n"

        string += self.schedule() + "\n"

        return string

    def runspec(self) -> str:
        """Make a string for the RUNSPEC section"""
        string = ""
        string += "RUNSPEC\n\n"

        string += f"DIMENS\n  1 1 {self.cells} /\n\n"

        string += "\n".join(list(self.phases)) + "\n\n"

        string += "START\n  1 'JAN' 2000 /\n\n"
        string += f"TABDIMS\n  {max(self.satnum)} /\n\n"
        string += f"EQLDIMS\n  {max(self.eqlnum)} /\n\n"

        string += f"{self.unifout}\n\n"
        return string

    def grid(self) -> str:
        """Make a string for the GRID section"""
        string = "GRID\n\n"
        string += "DX\n" + _wrap(" ".join(["100"] * self.cells) + "/") + "\n"
        string += "DY\n" + _wrap(" ".join(["100"] * self.cells) + "/") + "\n"
        string += "DZ\n" + _wrap(" ".join(map(str, self.cellheights)) + "/") + "\n"
        string += "TOPS\n" + _wrap(" ".join(map(str, self.tops)) + "/") + "\n"

        string += "PORO\n"
        string += _wrap("  ".join(map(str, self.poro)) + "/") + "\n"
        string += "PERMX\n"
        string += _wrap("  ".join(map(str, self.perm)) + "/") + "\n"
        string += "PERMY\n"
        string += _wrap("  ".join(map(str, self.perm)) + "/") + "\n"
        string += "PERMZ\n"
        string += _wrap("  ".join(map(str, self.perm)) + "/") + "\n"

        string += "GRIDFILE\n  0 1 /\n\n"
        string += "INIT\n\n"

        return string

    def evaluate_pc(
        self, s_water: float, scaling: float = 1.0, satnum: int = 1
    ) -> float:
        """Evaluate the capilllary pressure value for a given Sw value
        for a SATNUM. Interpolated linearly.

        Args:
            s_water: Saturation value between swl and 1.
            scaling: Scaling factor capillary pressure
            satnum: Starts at 1. Default 1.

        Returns:
            pc
        """
        return float(
            np.interp(
                s_water,
                [self.swl[satnum - 1], 1],
                [self.maxpc[satnum - 1] * scaling, self.minpc[satnum - 1] * scaling],
            )
        )

    def evaluate_sw(self, p_cap: float, scaling: float = 1.0, satnum: int = 1) -> float:
        """Evaluate the saturation at a given capillary pressure
        for a SATNUM. Interpolated linearly.

        Args:
            p_cap
            scaling: Scaling factor capillary pressure
            satnum: Starts at 1. Default 1.

        Returns:
            sw: Between 0 and 1
        """
        return float(
            np.interp(
                p_cap,
                [self.minpc[satnum - 1] * scaling, self.maxpc[satnum - 1] * scaling],
                [self.swu[satnum - 1], self.swl[satnum - 1]],
            )
        )

    def regions(self) -> str:
        """Make a string for the REGIONS section"""
        string = "REGIONS\n\n"

        string += "SATNUM\n"
        string += _wrap("  ".join(map(str, self.satnum)) + "/") + "\n"

        string += "EQLNUM\n"
        string += _wrap("  ".join(map(str, self.eqlnum)) + "/") + "\n"

        return string

    def props(self) -> str:
        """Make a string for the PROPS section"""
        string = "PROPS\n\n"

        if self.ppcwmax is not None:
            string += "PPCWMAX\n"
            assert isinstance(self.ppcwmax, list)
            assert len(self.ppcwmax) == max(self.satnum)
            string += (
                "\n".join([f"  {value:g} NO /" for value in self.ppcwmax]) + "\n\n"
            )

        if any(self.swatinit):
            string += "SWATINIT\n"
            string += _wrap(" ".join(map(str, self.swatinit)) + "/") + "\n"

        if "OIL" in self.phases:
            for satnum_idx, satnum in enumerate(range(len(self.swl))):
                if satnum_idx == 0:
                    string += "SWOF\n"
                string += "-- SW KRW KROW PC\n"
                string += f"  {self.swl[satnum]:g} 0 1 {self.maxpc[satnum]:g}\n"
                string += f"  {self.swu[satnum]:g} 1.0 0.0 {self.minpc[satnum]:g}\n/\n"

        if "GAS" in self.phases and "OIL" in self.phases:
            for satnum_idx, satnum in enumerate(range(len(self.swl))):
                if satnum_idx == 0:
                    string += "SGOF\n"
                string += "-- SG KRG KROG PC\n"
                string += "  0 0 1 0 \n"
                string += f"  {1-self.swl[satnum]:g} 1.0 0.0 0\n/\n"

        if "GAS" in self.phases and "OIL" not in self.phases:
            for satnum_idx, satnum in enumerate(range(len(self.swl))):
                if satnum_idx == 0:
                    string += "SWFN\n"
                string += "-- SW KRW PC\n"
                string += f"  {self.swl[satnum]:g} 0 {self.maxpc[satnum]:g}\n"
                string += f"  {self.swu[satnum]:g} 1.0 {self.minpc[satnum]:g}\n/\n"

            for satnum_idx, satnum in enumerate(range(len(self.swl))):
                if satnum_idx == 0:
                    string += "SGFN\n"
                string += "-- SG KRG PC\n"
                string += "  0 0 0\n"
                string += f"  {1 - self.swl[satnum]:g} 1.0 0.0\n/\n"

        if self.swlpc is not None:
            string += "SWLPC\n"
            string += _wrap("  ".join(map(str, self.swlpc)) + "/") + "\n"

        string += """\n
DENSITY
  800 1000 1.2 /

PVTW
  1 1 0.0001 0.2 0.00001 /
"""
        if "OIL" in self.phases:
            string += """
PVDO
  10 1   1
  150 0.9 1 /

"""
        if "GAS" in self.phases:
            string += """
PVDG
  100 1 1
  150 0.9 1 /

"""
        string += "ROCK\n  100 0.0001 /\n\n"

        string += self.filleps + "\n"  # Needed to get SWL in INIT file.
        return string

    def solution(self) -> str:
        """Make a string for the SOLUTION section"""
        string = "SOLUTION\n\n"
        string += ""
        string += "EQUIL\n"
        string += (
            "-- datum pressure_datum owc/gwc pc@owc goc pc@goc item7 item8 oip_init\n"
        )
        for eqlnum in range(max(self.eqlnum)):
            string += f"  1000 100 {self.owc[eqlnum]} 0 {self.goc[eqlnum]} "
            string += f"1* 1* 1* {self.oip_init}/\n"
        string += "\n"

        if self.rptrst:
            string += f"RPTRST\n  {self.rptrst}/ \n"
        return string

    def schedule(self) -> str:
        # pylint: disable=no-self-use
        """Make a string for the SCHEDULE section"""
        string = "SCHEDULE\n\n"
        string += "TSTEP \n  1 / \n"
        return string


def _wrap(longstring: str) -> str:
    return (
        "\n".join(
            textwrap.wrap(longstring, initial_indent="  ", subsequent_indent="  ")
        )
        + "\n"
    )
