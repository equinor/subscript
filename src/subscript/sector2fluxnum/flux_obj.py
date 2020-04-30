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

        fileH = open(fluxnum_file, "r")
        self.fluxnum_kw = EclKW.read_grdecl(fileH, "FLUXNUM", ecl_type=int_type)
        fileH.close()

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

    def include_well_completions_extra_layer_lgr(
            self, completion_list, well_list, exclude_list=()
    ):
        """
        Includes well completions in FLUXNUM keyword.
        This is necessary for ECLIPSE to accept
        the FLUXNUM region.
        Adds extra padding to well paths for LGR applications.

        @completion_list : List of completions to be included.
        @well_list : List of wells to be included
        @exclude_list = List of wells to be excluded from the FLUXNUM. Usually empty.
        """

        for well in well_list:
            includeWell = False
            temp_g = []
            neighbor = []
            wellIndex = well_list.index(well)

            for pos in completion_list[wellIndex]:
                (i, j, k) = pos

                globalIndex = self.grid.get_global_index(ijk=pos)
                temp_g.append(globalIndex)

                if k > 0:
                    neighbor.append(self.grid.get_global_index(ijk=(i, j, k + 1)))
                    neighbor.append(self.grid.get_global_index(ijk=(i, j, k - 1)))

                    neighbor.append(self.grid.get_global_index(ijk=(i - 1, j, k)))
                    neighbor.append(self.grid.get_global_index(ijk=(i - 1, j, k + 1)))
                    neighbor.append(self.grid.get_global_index(ijk=(i - 1, j, k - 1)))

                    neighbor.append(self.grid.get_global_index(ijk=(i + 1, j, k)))
                    neighbor.append(self.grid.get_global_index(ijk=(i + 1, j, k + 1)))
                    neighbor.append(self.grid.get_global_index(ijk=(i + 1, j, k - 1)))

                    neighbor.append(self.grid.get_global_index(ijk=(i, j - 1, k)))
                    neighbor.append(self.grid.get_global_index(ijk=(i, j - 1, k - 1)))
                    neighbor.append(self.grid.get_global_index(ijk=(i, j - 1, k + 1)))

                    neighbor.append(self.grid.get_global_index(ijk=(i, j + 1, k)))
                    neighbor.append(self.grid.get_global_index(ijk=(i, j + 1, k - 1)))
                    neighbor.append(self.grid.get_global_index(ijk=(i, j + 1, k + 1)))

                    neighbor.append(self.grid.get_global_index(ijk=(i - 1, j + 1, k)))
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i - 1, j + 1, k - 1))
                    )
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i - 1, j + 1, k + 1))
                    )

                    neighbor.append(self.grid.get_global_index(ijk=(i - 1, j - 1, k)))
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i - 1, j - 1, k - 1))
                    )
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i - 1, j - 1, k + 1))
                    )

                    neighbor.append(self.grid.get_global_index(ijk=(i + 1, j - 1, k)))
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i + 1, j - 1, k - 1))
                    )
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i + 1, j - 1, k + 1))
                    )

                    neighbor.append(self.grid.get_global_index(ijk=(i + 1, j + 1, k)))
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i + 1, j + 1, k - 1))
                    )
                    neighbor.append(
                        self.grid.get_global_index(ijk=(i + 1, j + 1, k + 1))
                    )

                if self.fluxnum_kw[globalIndex] == 1:
                    includeWell = True

            if well in exclude_list:
                includeWell = False

            if includeWell:
                print(well)
                self.included_wells.append(well)
                for g in temp_g:
                    (i, j, k) = self.grid.get_ijk(global_index=g)

                    self.fluxnum_kw[g] = 1

                for n in neighbor:
                    self.fluxnum_kw[n] = 1

    def set_dummy_lgr_well_completions(
            self, completion_list, well_list, exclude_list=()
    ):
        dummy_lgr_nr = 0
        for well in well_list:
            includeWell = False
            temp_g = []
            wellIndex = well_list.index(well)

            for pos in completion_list[wellIndex]:
                (i, j, k) = pos
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
                    neighbor_fluxnum_kw = []
                    (i, j, k) = self.grid.get_ijk(global_index=g)

                    if k > 0:
                        neighbor_index = self.grid.get_global_index(ijk=(i, j, k + 1))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j, k - 1))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j + 1, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j - 1, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i + 1, j, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i - 1, j, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])

                    if self.fluxnum_kw[g] == 0:
                        if self.grid.get_ijk(global_index=g) in self.dummy_lgr_cell:
                            index1 = self.dummy_lgr_cell.index(
                                self.grid.get_ijk(global_index=g)
                            )
                            self.dummy_lgr_name.append(self.dummy_lgr_name[index1])
                        else:
                            dummy_lgr_nr += 1
                            self.dummy_lgr_name.append(("LGRD" + str(dummy_lgr_nr)))
                        self.dummy_lgr_cell.append(self.grid.get_ijk(global_index=g))
                        self.dummy_lgr_well.append(well)

                    elif self.fluxnum_kw[g] == 1 and 0 in neighbor_fluxnum_kw:
                        if self.grid.get_ijk(global_index=g) in self.dummy_lgr_cell:
                            index1 = self.dummy_lgr_cell.index(
                                self.grid.get_ijk(global_index=g)
                            )
                            self.dummy_lgr_name.append(self.dummy_lgr_name[index1])
                        else:
                            dummy_lgr_nr += 1
                            self.dummy_lgr_name.append(("LGRD" + str(dummy_lgr_nr)))

                        self.dummy_lgr_cell.append(self.grid.get_ijk(global_index=g))
                        self.dummy_lgr_well.append(well)

    def write_fluxnum_kw(self, filename_path):
        """
        Writes FLUXNUM keyword to file.

        @filename_path : FLUXNUM keyword file
        """

        fileH = open(filename_path, "w")
        self.fluxnum_kw.write_grdecl(fileH)
        fileH.close()

    def set_dummy_lgr_well_completions_region_filter(
            self, completion_list, well_list, exclude_list=()
    ):
        dummy_lgr_nr = 0

        if not self.lgr_region:
            print("ERROR: LGR region not defined ...")
            sys.exit(1)

        for well in well_list:
            includeWell = False
            temp_g = []
            wellIndex = well_list.index(well)

            for pos in completion_list[wellIndex]:
                (i, j, k) = pos
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
                    neighbor_fluxnum_kw = []
                    (i, j, k) = self.grid.get_ijk(global_index=g)

                    if k > 0:
                        neighbor_index = self.grid.get_global_index(ijk=(i, j, k + 1))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j, k - 1))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j + 1, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i, j - 1, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i + 1, j, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])
                        neighbor_index = self.grid.get_global_index(ijk=(i - 1, j, k))
                        neighbor_fluxnum_kw.append(self.fluxnum_kw[neighbor_index])

                    if not self.lgr_region.contains_global(g):
                        if self.grid.get_ijk(global_index=g) in self.dummy_lgr_cell:
                            index1 = self.dummy_lgr_cell.index(
                                self.grid.get_ijk(global_index=g)
                            )
                            self.dummy_lgr_name.append(self.dummy_lgr_name[index1])
                        else:
                            dummy_lgr_nr += 1
                            self.dummy_lgr_name.append(("LGRD" + str(dummy_lgr_nr)))
                        self.dummy_lgr_cell.append(self.grid.get_ijk(global_index=g))
                        self.dummy_lgr_well.append(well)

                    elif (
                            not self.lgr_region.contains_global(g)
                            and 0 in neighbor_fluxnum_kw
                    ):
                        if self.grid.get_ijk(global_index=g) in self.dummy_lgr_cell:
                            index1 = self.dummy_lgr_cell.index(
                                self.grid.get_ijk(global_index=g)
                            )
                            self.dummy_lgr_name.append(self.dummy_lgr_name[index1])
                        else:
                            dummy_lgr_nr += 1
                            self.dummy_lgr_name.append(("LGRD" + str(dummy_lgr_nr)))

                        self.dummy_lgr_cell.append(self.grid.get_ijk(global_index=g))
                        self.dummy_lgr_well.append(well)

    def cluster_dummy_lgr_vertical_high_k(self, k):

        k_start = int(k.split("-")[0]) + 1
        k_end = int(k.split("-")[1]) - 1
        k_mid = (k_end + k_start) / 2

        LGR_names = []
        for index in range(len(self.dummy_lgr_cell)):
            lgr_name = self.dummy_lgr_name[index]
            (i1, j1, k1) = self.dummy_lgr_cell[index]
            if lgr_name not in LGR_names and k1 > k_mid:

                for index2 in range(len(self.dummy_lgr_cell)):
                    (i2, j2, k2) = self.dummy_lgr_cell[index2]
                    if i1 == i2 and j1 == j2 and k2 > k_mid:
                        self.dummy_lgr_name[index2] = lgr_name

                LGR_names.append(lgr_name)

    def cluster_dummy_lgr_vertical_low_k(self, k):

        k_start = int(k.split("-")[0])
        k_end = int(k.split("-")[1])
        k_mid = (k_end + k_start) / 2

        LGR_names = []
        for index in range(len(self.dummy_lgr_cell)):
            lgr_name = self.dummy_lgr_name[index]
            (i1, j1, k1) = self.dummy_lgr_cell[index]
            if lgr_name not in LGR_names and k1 < k_mid:

                for index2 in range(len(self.dummy_lgr_cell)):
                    (i2, j2, k2) = self.dummy_lgr_cell[index2]
                    if i1 == i2 and j1 == j2 and k2 < k_mid:
                        self.dummy_lgr_name[index2] = lgr_name

                LGR_names.append(lgr_name)


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
                print("ERROR: FIPNUM input file not found!")
                sys.exit(1)

            fileH = open(fipnum_file, "r")
            fipnum = EclKW.read_grdecl(
                fileH, "FIPNUM", ecl_type=EclTypeEnum.ECL_INT_TYPE
            )
            fileH.close()

        else:
            fipnum = self.init.iget_named_kw("FIPNUM", 0)

        self.inner_region = futil.filter_region(
            self.grid, i, j, k, fipnum_region_str, fipnum
        )
