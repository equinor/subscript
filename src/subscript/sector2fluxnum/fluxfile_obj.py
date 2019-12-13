import sys


class Fluxfile:
    """
    Container class for FLUX file data.
    """

    #    commonElements in all FLUX files and templates = 7

    def __init__(self, grid, flux):
        """
        Loads grid from EGRID and FLUX file from
        @grid
        @flux
        """
        self.grid = grid
        self.flux = flux
        self.number_flux_cells = int(len(flux[6]) / 3)  # Cast for Python3
        self.xyz_list = []
        self.index_list = []

    def set_index_list(self):
        self.index_list = list(self.flux[6][0 : self.number_flux_cells])

    def reset_index_list(self):
        self.index_list = []

    def get_index_list(self):
        return self.index_list

    def set_xyz_list(self):
        for index in self.flux[6][0 : self.number_flux_cells]:
            self.xyz_list.append(self.grid.get_xyz(global_index=index - 1))

    def reset_xyz_list(self):
        self.xyz_list = []

    def get_xyz_list(self):
        return self.xyz_list

    def get_flux(self):
        """
        Returns FLUX file.
        """
        return self.flux


def create_map_rst(
    destFlux, sourceGrid, scale_i=1, scale_j=1, scale_k=1, shift_i=0, shift_j=0
):
    """
    Creates a map from coarse to fine index.

    Will return a map to be used to look up data from coarse RESTART file for later
    population of FLUX file data.

    @destFlux: Template FLUX file to be populated
    @sourceGrid: Full field grid
    @scale_i: Scale in resolution in i-direction
    @scale_j: Scale in resolution in j-direction
    @scale_k: Scale in resolution in k-direction
    (Keep at 1 in this workflow)
    @shift_i: Shift in i-direction in the coarse RMS model used
    for further resolution refinement.
    This value needs to be recorded in the process
    of exporting the refined grid from RMS.
    The corresponding coarse i-index in the refined grid is
    i_coarse = (i_refine/scale_i) + shift_i)

    @scale_j: Shift in j-direction in the coarse RMS model used
    for further resolution refinement.
    This value needs to be recorded in the process
    of exporting the refined grid from RMS.

    The corresponding coarse j-index in the refined grid is
    j_coarse = (j_refine/scale_j) + shift_j)

    If no suitable coarse index is found using the simple
    index scaling, a distance function is lauched to locate
    the nearest cell. This function is time consuming and
    it should be investigated if grids are correctly initialized.
    """

    mapping = []
    counter = 0
    print("Creating map...")

    for index in destFlux.flux[6][0 : destFlux.number_flux_cells]:

        # Find global coordinates in the fine grid
        (i_f, j_f, k_f) = destFlux.grid.get_ijk(global_index=index - 1)

        # Do transform ijk fine to coarse
        ijk_source = (
            int((i_f) / scale_i) + shift_i,
            int((j_f) / scale_j) + shift_j,
            int((k_f) / scale_k),
        )

        # Identify the global index in the coarse grid
        source_active_index = sourceGrid.get_active_index(ijk_source)

        if source_active_index > -1:
            mapping.append(source_active_index)

        else:
            print("Warning: Not able to find direct cell. Using global position ...")
            # Find global coordinates in the fine grid
            (x_f, y_f, z_f) = destFlux.grid.get_xyz(global_index=index - 1)

            min_dist = 1e12

            for a in range(sourceGrid.get_num_active()):
                (x_s, y_s, z_s) = sourceGrid.get_xyz(active_index=a)

                dist = (x_s - x_f) ** 2 + (y_s - y_f) ** 2 + (z_s - z_f) ** 2

                if dist < min_dist:
                    min_dist = dist
                    min_pos_index = a

            # print min_pos_index, min_dist, c_g_index
            # Identify map of coarse grid to collect values to fine grid
            mapping.append(min_pos_index)

        counter += 1

        if counter % 100 == 0:
            print("Map progress: %i" % counter)

    return mapping


def write_new_fluxfile_from_rst(destFlux, sourceGrid, sourceRST, mapping, fortio):
    """
    Populates a templated .FLUX file with full field data from a RESTART file.

    @destFlux: Template FLUX file to be populated
    @sourceFlux: Template FLUX file from full field grid (Not used)
    @sourceRST: RESTART data from full field simulation. Used to populate @destFlux
    @mapping: Map from refined to coarse index
    @fortio: File stream for unformated data.

    The population of the FLUX file is sensitive to the format of the template file.
    Later versions of Eclipse may have changed formating.
    Report issue in the GitHub repo if deviations are found!
    """

    # Importing elements
    flux_fine = destFlux.get_flux()

    if sourceGrid.getNumLGR() > 0:
        print(" ")
        print("***************************************")
        print("WARNING: LGR present in native grid.")
        print("Check ECL manual for restrictions")
        print("***************************************")
        print(" ")

    # Common elements in both FLUX files
    nCommonElements = 7

    for i in range(nCommonElements):
        kw_temp = flux_fine[i].deep_copy()
        kw_temp.fwrite(fortio)  # Writes to file succesivly

    blockSize = len(flux_fine) - nCommonElements

    # Manipulating existing blocks in the fine grid
    # Importing data from the coarse grid

    prevDate = sourceRST.dates[0]
    prevDaysFlux = flux_fine.iget_named_kw("DTIME", 0)[0]

    for i in range(0, len(sourceRST.report_dates)):

        i_coarse_grid = i * (sourceGrid.getNumLGR() + 1)

        currentDate = sourceRST.dates[i]
        deltaTime = currentDate - prevDate
        deltaDays = deltaTime.days
        prevDate = currentDate

        for j in range(nCommonElements, nCommonElements + blockSize):

            # Not related to grid cells
            if flux_fine[j].header[0] == "ITIME":
                kw_temp = flux_fine[j].deep_copy()
                kw_temp[0] = 1

            elif flux_fine[j].header[0] == "DTIME":
                kw_temp = flux_fine[j].deep_copy()
                kw_temp[0] = prevDaysFlux
                kw_temp[1] = prevDaysFlux + deltaDays
                prevDaysFlux += deltaDays

            elif flux_fine[j].header[0] == "WELLNAME":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "WELLFLOW":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "PMER":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "PADMAX":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "PMAX":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "PADS":
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "":  # OBS!
                kw_temp = flux_fine[j].deep_copy()

            elif flux_fine[j].header[0] == "POIL":
                kw_temp = flux_fine[j].deep_copy()
                kw_source = sourceRST.iget_named_kw("PRESSURE", i_coarse_grid)

                if len(kw_source) != sourceGrid.get_num_active():
                    print("ERROR: Mismatch between restart data and grid size!")
                    print(
                        "kw size = %i and restart size = %i"
                        % (len(kw_source), sourceGrid.get_num_active())
                    )
                    sys.exit(1)

                # Maps property data from coarse to fine grid.
                # Related to grid cells.
                for k in range(flux_fine[j].header[1]):
                    kw_temp[k] = kw_source[mapping[k]]

            elif flux_fine[j].header[0] == "SWAT":
                kw_temp = flux_fine[j].deep_copy()
                kw_source = sourceRST.iget_named_kw("SWAT", i_coarse_grid)

                for k in range(flux_fine[j].header[1]):
                    kw_temp[k] = kw_source[mapping[k]]

            elif flux_fine[j].header[0] == "SGAS":
                kw_temp = flux_fine[j].deep_copy()
                kw_source = sourceRST.iget_named_kw("SGAS", i_coarse_grid)

                for k in range(flux_fine[j].header[1]):
                    kw_temp[k] = kw_source[mapping[k]]

            elif flux_fine[j].header[0] == "SOIL":
                kw_temp = flux_fine[j].deep_copy()

                if sourceRST.has_kw("SGAS"):
                    kw_source1 = sourceRST.iget_named_kw("SGAS", i_coarse_grid)
                    kw_source2 = sourceRST.iget_named_kw("SWAT", i_coarse_grid)

                    for k in range(flux_fine[j].header[1]):
                        kw_temp[k] = 1 - kw_source1[mapping[k]] - kw_source2[mapping[k]]

                else:
                    kw_source2 = sourceRST.iget_named_kw("SWAT", i_coarse_grid)

                    for k in range(flux_fine[j].header[1]):
                        kw_temp[k] = 1 - kw_source2[mapping[k]]

            elif flux_fine[j].header[0] == "RS":
                kw_temp = flux_fine[j].deep_copy()

                if sourceRST.has_kw("RS"):
                    kw_source = sourceRST.iget_named_kw("RS", i_coarse_grid)

                    for k in range(flux_fine[j].header[1]):
                        kw_temp[k] = kw_source[mapping[k]]

            elif flux_fine[j].header[0] == "OILAPI":
                kw_temp = flux_fine[j].deep_copy()

                if sourceRST.has_kw("OILAPI"):
                    kw_source = sourceRST.iget_named_kw("OILAPI", i_coarse_grid)

                    for k in range(flux_fine[j].header[1]):
                        kw_temp[k] = kw_source[mapping[k]]

            kw_temp.fwrite(fortio)

        print("Writing restart reportstep %s to FLUX file" % (i))
