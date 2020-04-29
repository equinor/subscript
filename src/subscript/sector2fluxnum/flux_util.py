#!/usr/bin/env python
from ecl.eclfile import EclFile, EclKW
from ecl.grid import EclRegion
from ecl import EclFileFlagEnum
import sys


def project_DTIME(NEW_FLUXFILE, DTIME_value_scale=1.0):

    # ######################################################
    # Importing elements
    # ######################################################

    newFluxFile = EclFile(NEW_FLUXFILE, EclFileFlagEnum.ECL_FILE_WRITABLE)

    new_DTIME = newFluxFile[newFluxFile.size - 13]
    new_DTIME[1] *= DTIME_value_scale

    newFluxFile.save_kw(new_DTIME)

    newFluxFile.close()


def manipulate_PORV(FLUXFILE, POROFILE):

    flux = EclFile(FLUXFILE)
    poro = EclKW.read_grdecl(
        open(POROFILE, "r"), "PORO"
    )  # , ecl_type = ECL_DOUBLE_TYPE )

    multpv = EclKW("MULTPV", len(poro), poro.getEclType())
    multpvFactor = 100.0

    for i in range(len(multpv)):
        multpv[i] = 1.0

    for index in flux[6][0 : flux[6].size / 3]:
        multpv[index] = multpvFactor

    print("Writing...", " ")

    fileH = open("include/%s_new.grdecl" % multpv.getName(), "w")
    multpv.write_grdecl(fileH)
    fileH.close()


def filter_region(grid, i, j, k, fipnum, fipnum_kw, combine_operator="intersect"):

    # Filter out the selected grid cells
    region = EclRegion(grid, False)
    region1 = EclRegion(grid, False)
    region2 = EclRegion(grid, False)
    region_i = EclRegion(grid, False)
    region_j = EclRegion(grid, False)
    region_k = EclRegion(grid, False)
    region_fip = EclRegion(grid, False)

    # Create selected regions for each filter type
    if i:
        for i_slice in unpack_filter(i):
            region_i.select_islice(
                i_slice - 1, i_slice - 1
            )  # -1 because ert defines i=1 as i=0
    else:
        region_i.select_all()
    if j:
        for j_slice in unpack_filter(j):
            region_j.select_jslice(
                j_slice - 1, j_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_j.select_all()
    if k:
        for k_slice in unpack_filter(k):
            region_k.select_kslice(
                k_slice - 1, k_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_k.select_all()
    if fipnum:
        for fip in unpack_filter(fipnum):
            print(fip)
            region_fip.select_equal(fipnum_kw, fip)
    else:
        region_fip.select_all()

    # Combine regions by
    if (
        combine_operator == "intersect"
        or combine_operator == ""
        or combine_operator is None
    ):
        # Intersection
        region.select_all()  # region.select_active()
        region = region & region_i & region_j & region_k & region_fip
        return region
    elif combine_operator == "union":
        # Union
        region1.select_active()
        region2 = region_i | region_j | region_k | region_fip
        region = region1 & region2
        return region
    else:
        sys.exit("'%s' is not a valid operator to combine regions." % combine_operator)


def filter_region_fipnum(grid, fipnum, fipnum_kw, combine_operator="intersect"):

    # Filter out the selected grid cells
    region = EclRegion(grid, False)
    region1 = EclRegion(grid, False)
    region2 = EclRegion(grid, False)
    region_fip = EclRegion(grid, False)

    # Create selected regions for each filter type
    if fipnum:
        for fip in unpack_filter(fipnum):
            region_fip.select_equal(fipnum_kw, fip)
    else:
        region_fip.select_all()

    # Combine regions by
    if (
        combine_operator == "intersect"
        or combine_operator == ""
        or combine_operator is None
    ):
        # Intersection
        region.select_all()
        region = region & region_fip
        return region
    elif combine_operator == "union":
        # Union
        region1.select_active()
        region2 = region_fip
        region = region1 & region2
        return region
    else:
        sys.exit("'%s' is not a valid operator to combine regions." % combine_operator)


def filter_region_ijk(grid, i, j, k, combine_operator="intersect"):

    # Filter out the selected grid cells
    region = EclRegion(grid, False)
    region1 = EclRegion(grid, False)
    region2 = EclRegion(grid, False)
    region_i = EclRegion(grid, False)
    region_j = EclRegion(grid, False)
    region_k = EclRegion(grid, False)

    # Create selected regions for each filter type
    if i:
        for i_slice in unpack_filter(i):
            region_i.select_islice(
                i_slice - 1, i_slice - 1
            )  # -1 because ert defines i=1 as i=0
    else:
        region_i.select_all()
    if j:
        for j_slice in unpack_filter(j):
            region_j.select_jslice(
                j_slice - 1, j_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_j.select_all()
    if k:
        for k_slice in unpack_filter(k):
            region_k.select_kslice(
                k_slice - 1, k_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_k.select_all()

    # Combine regions by
    if (
        combine_operator == "intersect"
        or combine_operator == ""
        or combine_operator is None
    ):
        # Intersection
        region.select_all()
        region = region & region_i & region_j & region_k
        return region
    elif combine_operator == "union":
        # Union
        region1.select_active()
        region2 = region_i | region_j | region_k
        region = region1 & region2
        return region
    else:
        sys.exit("'%s' is not a valid operator to combine regions." % combine_operator)


def unpack_filter(filter_list):

    filter_list = filter_list.split(",")
    filter_list_return = []
    for i in range(0, len(filter_list)):
        if "-" in str(filter_list[i]):
            filter_start = int(filter_list[i].split("-")[0])
            filter_end = int(filter_list[i].split("-")[1])
            for j in range(filter_start, filter_end + 1):
                filter_list_return.append(int(j))
        else:
            filter_list_return.append(int(filter_list[i]))
    return filter_list_return


def unpack_ijk(i_str, j_str, k_str):

    i_str_split = i_str.split("-")
    if len(i_str_split) < 2:
        print("Wrong format of i range. Should be: i_start-i_end")
        sys.exit(1)

    i_start = int(i_str_split[0])
    i_end = int(i_str_split[1])

    j_str_split = j_str.split("-")
    if len(j_str_split) < 2:
        print("Wrong format of j range. Should be: j_start-j_end")
        sys.exit(1)

    j_start = int(j_str_split[0])
    j_end = int(j_str_split[1])

    k_str_split = k_str.split("-")
    if len(k_str_split) < 2:
        print("Wrong format of k range. Should be: k_start-k_end")
        sys.exit(1)

    k_start = int(k_str_split[0])
    k_end = int(k_str_split[1])

    ijk_list = [i_start, i_end, j_start, j_end, k_start, k_end]

    return ijk_list


def get_FLUXNUM_STOIIP(grid, init, restart):
    """
    Returns STOIIP from the FLUXNUM region
    """

    fluxnum = init.iget_named_kw("FLUXNUM", 0)
    swat = restart.iget_named_kw("SWAT", 0)
    sgas = restart.iget_named_kw("SGAS", 0)
    poro = init.iget_named_kw("PORO", 0)
    ntg = init.iget_named_kw("NTG", 0)

    STOIIP = 0
    for act_i in range(grid.nactive):
        if fluxnum[act_i] > 0:
            STOIIP += (
                (1 - swat[act_i] - sgas[act_i])
                * poro[act_i]
                * grid.cell_volume(active_index=act_i)
                * ntg[act_i]
            )

    return STOIIP


def get_FLUXNUM_OIP(grid, init, restart, index=0):
    """
    Returns STOIIP from the FLUXNUM region
    """

    fluxnum = init.iget_named_kw("FLUXNUM", 0)
    swat = restart.iget_named_kw("SWAT", index)
    sgas = restart.iget_named_kw("SGAS", index)
    poro = init.iget_named_kw("PORO", 0)
    ntg = init.iget_named_kw("NTG", 0)

    STOIIP = 0
    for act_i in range(grid.nactive):
        if fluxnum[act_i] > 0:
            STOIIP += (
                (1 - swat[act_i] - sgas[act_i])
                * poro[act_i]
                * grid.cell_volume(active_index=act_i)
                * ntg[act_i]
            )

    return STOIIP


def get_FLUXNUM_GIIP(grid, init, restart):
    """
    Returns GIIP from the FLUXNUM region
    """

    fluxnum = init.iget_named_kw("FLUXNUM", 0)
    sgas = restart.iget_named_kw("SGAS", 0)
    poro = init.iget_named_kw("PORO", 0)
    ntg = init.iget_named_kw("NTG", 0)

    GIIP = 0
    for act_i in range(grid.nactive):
        if fluxnum[act_i] > 0:
            GIIP += (
                sgas[act_i]
                * poro[act_i]
                * grid.cell_volume(active_index=act_i)
                * ntg[act_i]
            )

    return GIIP


def get_FLUXNUM_PRESSURE_AVG(grid, init, restart):
    """
    Returns average pressure from the FLUXNUM region
    """

    fluxnum = init.iget_named_kw("FLUXNUM", 0)
    pressure = restart.iget_named_kw("PRESSURE", 0)

    pres = 0
    fluxnum_cells = 0
    for act_i in range(grid.nactive):
        if fluxnum[act_i] > 0:
            pres += pressure[act_i]
            fluxnum_cells += 1

    return pres / fluxnum_cells


def compare_STOIIP(STOIIP_coarse, STOIIP_fine):

    diff = (abs(STOIIP_fine - STOIIP_coarse)) / STOIIP_coarse * 100
    print("STOIIP in refined FLUXNUM region is:     %.4e" % (STOIIP_fine))
    print("STOIIP in coarse FLUXNUM region is:    %.4e" % (STOIIP_coarse))
    print("Deviation is %.2f %s" % (diff, "%"))

    if diff > 2:
        print(
            "WARNING: The difference in STOIIP between the models is larger than 2 %s"
            % ("%")
        )


def compare_GIIP(GIIP_coarse, GIIP_fine):
    diff = (abs(GIIP_fine - GIIP_coarse)) / GIIP_coarse * 100
    print("GIIP in refined FLUXNUM region is:  %.4e" % (GIIP_fine))
    print("GIIP in coarse FLUXNUM region is:  %.4e" % (GIIP_coarse))
    print("Deviation is %.2f %s" % (diff, "%"))

    if diff > 2:
        print(
            "WARNING: The difference in GIIP between the models is larger than 2 %s"
            % ("%")
        )


def compare_pressure(PRES_coarse, PRES_fine):
    diff = (abs(PRES_fine - PRES_coarse)) / PRES_coarse * 100
    print("Pressure in refined FLUXNUM region is:  %d" % (PRES_fine))
    print("Pressure in coarse FLUXNUM region is:  %d" % (PRES_coarse))
    print("Deviation is %.2f %s" % (diff, "%"))

    if diff > 2:
        print("WARNING: The difference in average pressure between the models")
        print("is larger than 2 %s" % ("%"))
