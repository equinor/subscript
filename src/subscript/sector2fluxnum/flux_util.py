from resdata.grid import ResdataRegion


def filter_region(
    grid, idx_i, idx_j, idx_k, fipnum, fipnum_kw, combine_operator="intersect"
):
    # Filter out the selected grid cells
    region = ResdataRegion(grid, False)
    region1 = ResdataRegion(grid, False)
    region_i = ResdataRegion(grid, False)
    region_j = ResdataRegion(grid, False)
    region_k = ResdataRegion(grid, False)
    region_fip = ResdataRegion(grid, False)

    # Create selected regions for each filter type
    if idx_i:
        for i_slice in unpack_filter(idx_i):
            region_i.select_islice(
                i_slice - 1, i_slice - 1
            )  # -1 because ert defines i=1 as i=0
    else:
        region_i.select_all()

    if idx_j:
        for j_slice in unpack_filter(idx_j):
            region_j.select_jslice(
                j_slice - 1, j_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_j.select_all()

    if idx_k:
        for k_slice in unpack_filter(idx_k):
            region_k.select_kslice(
                k_slice - 1, k_slice - 1
            )  # -1 because ert defines j=1 as j=0
    else:
        region_k.select_all()

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
        region.select_all()  # region.select_active()
        return region & region_i & region_j & region_k & region_fip

    if combine_operator == "union":
        # Union
        region1.select_active()
        region2 = region_i | region_j | region_k | region_fip
        return region1 & region2

    raise Exception(
        f"ERROR: '{combine_operator}' is not a valid operator to combine regions."
    )


def unpack_filter(filter_list):
    filter_list = filter_list.split(",")
    filter_list_return = []
    for idx, _ in enumerate(filter_list):
        if "-" in str(filter_list[idx]):
            filter_start = int(filter_list[idx].split("-")[0])
            filter_end = int(filter_list[idx].split("-")[1])
            for idx2 in range(filter_start, filter_end + 1):
                filter_list_return.append(int(idx2))
        else:
            filter_list_return.append(int(filter_list[idx]))
    return filter_list_return


def unpack_ijk(i_str, j_str, k_str):
    i_str_split = i_str.split("-")
    if len(i_str_split) < 2:
        raise Exception("Wrong format of i range. Should be: i_start-i_end")

    i_start = int(i_str_split[0])
    i_end = int(i_str_split[1])

    j_str_split = j_str.split("-")
    if len(j_str_split) < 2:
        raise Exception("Wrong format of j range. Should be: j_start-j_end")

    j_start = int(j_str_split[0])
    j_end = int(j_str_split[1])

    k_str_split = k_str.split("-")
    if len(k_str_split) < 2:
        raise Exception("Wrong format of k range. Should be: k_start-k_end")

    k_start = int(k_str_split[0])
    k_end = int(k_str_split[1])

    return [i_start, i_end, j_start, j_end, k_start, k_end]
