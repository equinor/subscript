#!/usr/bin/env python
from ecl.eclfile import EclKW
from ecl.grid import EclRegion

try:
    from ecl import EclDataType
except ImportError:
    from ecl import EclTypeEnum

import sys
import subscript.sector2fluxnum.flux_util as futil
import os


class Fluxnum:

    """    Superclass
    """

    def __init__(self, grid):
        # ParamObject.__init__(self)
        """
        Input for all classes is the actual grid
        Needed for evaluation of regions

        Creates a non-initialized  FLUXNUM keyword
        """

        try:
            int_type = EclDataType.ECL_INT
        except NameError:
            int_type = EclTypeEnum.ECL_INT_TYPE

        self.grid = grid
        self.fluxnum_kw = EclKW("FLUXNUM", grid.getGlobalSize(), int_type)
        self.included_wells = []
        self.dummy_lgr_cell = []
        self.dummy_lgr_well = []
        self.dummy_lgr_name = []
        self.lgr_region = None
        self.inner_region = None

    def copy_actnum(self, actnum):
        """

        Copy data from ACTNUM keyword to the FLUXNUM keyword
        """

        self.fluxnum_kw = actnum.deep_copy()
        self.fluxnum_kw.name = "FLUXNUM"

    def setInnerRegion(self):
        """

        Initializes inner region used to define the FLUXNUM
        """
        self.inner_region = EclRegion(self.grid, False)
        self.inner_region.select_all()

    def setLgrBoxRegion(self, i, j, k):
        """

        Sets an LGR region with one cell indent from the box boundaries.
        Only works for Box regions

        """
        self.lgr_region = EclRegion(self.grid, False)
        ijk_list = futil.unpack_ijk(i, j, k)

        # Drags lgr boundaries one cell from box region
        i_lgr_start = ijk_list[0]
        i_lgr_end = ijk_list[1] - 2
        j_lgr_start = ijk_list[2]
        j_lgr_end = ijk_list[3] - 2
        k_lgr_start = ijk_list[4]
        k_lgr_end = ijk_list[5] - 2

        self.lgr_region.select_box(
            (i_lgr_start, j_lgr_start, k_lgr_start), (i_lgr_end, j_lgr_end, k_lgr_end)
        )

    def set_fluxnum_kw(self):
        """

        Initialize FLUXNUM

        NB: Can take some time if the grid is large
        """
        self.fluxnum_kw.assign(0)
        self.inner_region.set_kw(self.fluxnum_kw, 1)

    def set_fluxnum_kw_from_file(self, fluxnum_file):
        """

        Initialize FLUXNUM from file

        NB: Can take some time if the grid is large
        """

        if not os.path.isfile(fluxnum_file):
            print("ERROR: FLUXNUM input file not found!")
            sys.exit(1)

        try:
            int_type = EclDataType.ECL_INT
        except NameError:
            int_type = EclTypeEnum.ECL_INT_TYPE

        with open(fluxnum_file, "r") as fileH:
            self.fluxnum_kw = EclKW.read_grdecl(fileH, "FLUXNUM", ecl_type=int_type)

    def get_fluxnum_kw(self):
        return self.fluxnum_kw

    def include_nnc(self, EGRID_file):
        """
        Adds NNC connections to FLUXNUM region.

        @EGRID file

        This is useful for LGR since LGR region must be one cell away from FLUXNUM
        boundaries. If NNC for LGR is outside FLUXNUM, an error will be sent by ECLIPSE.

        Needs NNC data from EGRID file.
        """

        if EGRID_file[11].header[0] == "NNC1":
            NNC1_list = EGRID_file[11]
        else:
            print("ERROR: NNC info not included in EGRID ...")
        if EGRID_file[12].header[0] == "NNC2":
            NNC2_list = EGRID_file[12]
        else:
            print("ERROR: NNC info not included in EGRID ...")

        # Checks for NNC pairs. Sets both to 1 if detected in FLUXNUM KW
        for i in range(len(NNC1_list)):
            nnc1_global_index = NNC1_list[i] - 1  # Converts ECL index
            nnc2_global_index = NNC2_list[i] - 1  # Converts ECL index
            if self.fluxnum_kw[nnc1_global_index] == 1:
                self.fluxnum_kw[nnc2_global_index] = 1

            if self.fluxnum_kw[nnc2_global_index] == 1:
                self.fluxnum_kw[nnc1_global_index] = 1

    def include_well_completions(self, completion_list, well_list, exclude_list=[]):
        """
        Includes well completions in FLUXNUM keyword.
        This is necessary for ECLIPSE to accept
        the FLUXNUM region.

        @completion_list : List of completions to be included.
        @well_list : List of wells to be included
        @exclude_list = List of wells to be excluded from the FLUXNUM. Usually empty.
        """

        for well in well_list:
            includeWell = False
            temp_g = []
            wellIndex = well_list.index(well)

            for pos in completion_list[wellIndex]:
                globalIndex = self.grid.get_global_index(ijk=pos)
                temp_g.append(globalIndex)

                if self.fluxnum_kw[globalIndex] == 1:
                    includeWell = True

            if well in exclude_list:
                includeWell = False

            if includeWell:
                print(well)
                self.included_wells.append(well)
                for g in temp_g:
                    self.fluxnum_kw[g] = 1

    def write_fluxnum_kw(self, filename_path):
        """
        Writes FLUXNUM keyword to file.

        @filename_path : FLUXNUM keyword file
        """

        with open(filename_path, "w") as fileH:
            self.fluxnum_kw.write_grdecl(fileH)


class Fluxnum_box(Fluxnum):

    """
    Subclass
    """

    def __init__(self, grid, i_start, i_end, j_start, j_end, k_start=0, k_end=0):
        """
        Define FLUXNUM region based on box dimensions

        """

        Fluxnum.__init__(self, grid)

        i_start -= 1
        i_end -= 1
        j_start -= 1
        j_end -= 1

        if k_end == 0:
            k_start = 0
            k_end = self.grid.nz - 1

        else:
            k_start -= 1
            k_end -= 1

        self.setInnerRegion(i_start, i_end, j_start, j_end, k_start, k_end)
        self.setOuterRegion(i_start, i_end, j_start, j_end, k_start, k_end)

    def setInnerRegion(self, i_start, i_end, j_start, j_end, k_start, k_end):
        self.inner_region = EclRegion(self.grid, False)
        self.inner_region.select_box((i_start, j_start, k_start), (i_end, j_end, k_end))

    def setOuterRegion(self, i_start, i_end, j_start, j_end, k_start, k_end):
        self.outer_region = EclRegion(self.grid, False)
        self.outer_region.select_box((i_start, j_start, k_start), (i_end, j_end, k_end))
        self.outer_region.invert()


class Fluxnum_fipnum(Fluxnum):
    """
    Subclass
    """

    def __init__(self, grid, init, i, j, k, fipnum_region, fipnum_file=None):
        """
        Defines FLUXNUM region based on box dimensions
        and list of FIPNUM regions

        @grid : Grid data based on EGRID input
        @init : Init data based in INIT file input
        @i : i range (i_start - i_end)
        @j : j range (j_start - j_end)
        @k : k range (k_start - k_end)
        @fipnum_region : List of FIPNUM regions
        @fipnum_file : FIPNUM keyword read from file instead if INIT.

        If it is important that the FIPNUM regions do not contain
        any in-active cells, the FIPNUM needs to be collected
        from input file @fipnum_file.
        """

        Fluxnum.__init__(self, grid)
        self.init = init
        self.setInnerRegion(i, j, k, fipnum_region, fipnum_file)

    def setInnerRegion(self, i, j, k, fipnum_region, fipnum_file):
        fipnum_region_str = fipnum_region

        if fipnum_file:
            if not os.path.isfile(fipnum_file):
                raise Exception("ERROR: FIPNUM input file not found!")

            with open(fipnum_file, "r") as fileH:
                fipnum = EclKW.read_grdecl(
                    fileH, "FIPNUM", ecl_type=EclTypeEnum.ECL_INT_TYPE
                )

        else:
            fipnum = self.init.iget_named_kw("FIPNUM", 0)

        self.inner_region = futil.filter_region(
            self.grid, i, j, k, fipnum_region_str, fipnum
        )
