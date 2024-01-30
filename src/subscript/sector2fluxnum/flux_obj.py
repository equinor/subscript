import os
import sys

from resdata import ResDataType
from resdata.grid import ResdataRegion
from resdata.resfile import ResdataKW

from subscript.sector2fluxnum import flux_util


class Fluxnum:
    """Superclass"""

    def __init__(self, grid):
        # ParamObject.__init__(self)
        """
        Input for all classes is the actual grid
        Needed for evaluation of regions

        Creates a non-initialized  FLUXNUM keyword
        """
        int_type = ResDataType.RD_INT
        self.grid = grid
        self.fluxnum_kw = ResdataKW("FLUXNUM", grid.getGlobalSize(), int_type)
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

    def set_inner_region(self):
        """

        Initializes inner region used to define the FLUXNUM
        """
        self.inner_region = ResdataRegion(self.grid, False)
        self.inner_region.select_all()

    def set_lgr_box_region(self, i, j, k):
        """

        Sets an LGR region with one cell indent from the box boundaries.
        Only works for Box regions

        """
        self.lgr_region = ResdataRegion(self.grid, False)
        ijk_list = flux_util.unpack_ijk(i, j, k)

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

        int_type = ResDataType.RD_INT

        with open(fluxnum_file, "r", encoding="utf8") as file_handle:
            self.fluxnum_kw = ResdataKW.read_grdecl(
                file_handle, "FLUXNUM", rd_type=int_type
            )

    def get_fluxnum_kw(self):
        return self.fluxnum_kw

    def include_nnc(self, egrid_file):
        """
        Adds NNC connections to FLUXNUM region.

        @EGRID file

        This is useful for LGR since LGR region must be one cell away from FLUXNUM
        boundaries. If NNC for LGR is outside FLUXNUM, an error will be sent by ECLIPSE.

        Needs NNC data from EGRID file.
        """

        if egrid_file[11].header[0] == "NNC1":
            nnc1_list = egrid_file[11]
        else:
            print("ERROR: NNC info not included in EGRID ...")
        if egrid_file[12].header[0] == "NNC2":
            nnc2_list = egrid_file[12]
        else:
            print("ERROR: NNC info not included in EGRID ...")

        # Checks for NNC pairs. Sets both to 1 if detected in FLUXNUM KW
        for idx, _ in enumerate(nnc1_list):
            nnc1_global_index = nnc1_list[idx] - 1  # Converts ECL index
            nnc2_global_index = nnc2_list[idx] - 1  # Converts ECL index
            if self.fluxnum_kw[nnc1_global_index] == 1:
                self.fluxnum_kw[nnc2_global_index] = 1

            if self.fluxnum_kw[nnc2_global_index] == 1:
                self.fluxnum_kw[nnc1_global_index] = 1

    def include_well_completions(self, completion_list, well_list, exclude_list=None):
        """
        Includes well completions in FLUXNUM keyword.
        This is necessary for ECLIPSE to accept
        the FLUXNUM region.

        @completion_list : List of completions to be included.
        @well_list : List of wells to be included
        @exclude_list = List of wells to be excluded from the FLUXNUM. Usually empty.
        """
        if exclude_list is None:
            exclude_list = []

        for well in well_list:
            include_well = False
            temp_g = []
            well_index = well_list.index(well)

            for pos in completion_list[well_index]:
                global_index = self.grid.get_global_index(ijk=pos)
                temp_g.append(global_index)

                if self.fluxnum_kw[global_index] == 1:
                    include_well = True

            if well in exclude_list:
                include_well = False

            if include_well:
                print(well)
                self.included_wells.append(well)
                for g_ in temp_g:
                    self.fluxnum_kw[g_] = 1

    def write_fluxnum_kw(self, filename_path):
        """
        Writes FLUXNUM keyword to file.

        @filename_path : FLUXNUM keyword file
        """

        with open(filename_path, "w", encoding="utf8") as file_handle:
            self.fluxnum_kw.write_grdecl(file_handle)


class FluxnumBox(Fluxnum):
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

        self.set_inner_region(i_start, i_end, j_start, j_end, k_start, k_end)
        self.set_outer_region(i_start, i_end, j_start, j_end, k_start, k_end)

    def set_inner_region(self, i_start, i_end, j_start, j_end, k_start, k_end):
        self.inner_region = ResdataRegion(self.grid, False)
        self.inner_region.select_box((i_start, j_start, k_start), (i_end, j_end, k_end))

    def set_outer_region(self, i_start, i_end, j_start, j_end, k_start, k_end):
        self.outer_region = ResdataRegion(self.grid, False)
        self.outer_region.select_box((i_start, j_start, k_start), (i_end, j_end, k_end))
        self.outer_region.invert()


class FluxnumFipnum(Fluxnum):
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
        self.set_inner_region(i, j, k, fipnum_region, fipnum_file)

    def set_inner_region(self, i, j, k, fipnum_region, fipnum_file):
        fipnum_region_str = fipnum_region

        if fipnum_file:
            if not os.path.isfile(fipnum_file):
                raise Exception("ERROR: FIPNUM input file not found!")

            with open(fipnum_file, "r", encoding="utf8") as file_handle:
                fipnum = ResdataKW.read_grdecl(
                    file_handle, "FIPNUM", rd_type=ResDataType.RD_INT
                )

        else:
            fipnum = self.init.iget_named_kw("FIPNUM", 0)

        self.inner_region = flux_util.filter_region(
            self.grid, i, j, k, fipnum_region_str, fipnum
        )
