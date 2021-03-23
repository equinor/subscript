"""The FipMapper class, mapping region/zones in RMS to FIPxxx in Eclipse.

This API should be considered private to prtvol2csv until it has moved somewhere
else"""
from typing import Union
from pathlib import Path
import yaml

from subscript import getLogger

logger = getLogger(__name__)


class FipMapper:
    def __init__(
        self,
        yamlfile: Union[str, Path] = None,
        mapdata: dict = None,
        skipstring: Union[list, str] = None,
    ):
        """FipMapper is a utility class for being able to map between
        regions/zones in the geomodel (RMS) and to different region divisions in the
        dynamic model (Eclipse).

        Primary usage is to determine which RMS regions corresponds to
        which FIPNUMs, similarly for zones, and in both directions

        Configuration is via a yaml-file or directly with a dictionary.

        Several data structures in the dictionary can be used, such that
        the needed information can be extracted from the global configurations
        file.

        Args:
            yamlfile (Path): Filename
            mapdata (dict): direct dictionary input. Provide only one of the
                arguments, not both.
            skipstring: List of strings which will be ignored (e.g. ["Totals"]).
        """
        self._mapdata = {}  # To be filled with data we need.

        if skipstring is None:
            self.skipstring = []
        if isinstance(skipstring, str):
            self.skipstring = [skipstring]

        if yamlfile is not None and mapdata is not None:
            raise ValueError(
                "Initialize with either yamlfile or explicit data, not both"
            )
        if yamlfile is None and mapdata is None:
            logger.warning("FipMapper initialized with no data")

        if yamlfile is not None:
            logger.info("Loading data from %s", yamlfile)
            with open(yamlfile) as stream:
                yamldata = yaml.safe_load(stream)
            logger.debug(str(yamldata))
        else:
            yamldata = mapdata

        if yamldata is not None:
            self._get_explicit_mapdata(yamldata)

        if yamldata is not None and "global" in yamldata:
            # This is a fmu-config file.
            self._fipdata_from_fmuconfigyaml(yamldata)

        # Webviz YML format:
        if yamldata is not None and "FIPNUM" in yamldata:
            self._fipdata_from_webvizyaml(yamldata)

        assert isinstance(self._mapdata, dict), "FipMapper needs a dictionary"

        # Determine our capabilities:
        self.has_fip2region = "fipnum2region" in self._mapdata
        self.has_fip2zone = "fipnum2zone" in self._mapdata
        self.has_region2fip = "region2fipnum" in self._mapdata
        self.has_zone2fip = "zone2fipnum" in self._mapdata

    def _get_explicit_mapdata(self, yamldata: dict):
        """Fetch explicit mapping configuration from a dictionary,

        Set internal flags when maps are found

        Invert maps when possible/needed

        Args:
            yamldata (dict): Configuration object with predefined items
                at the first level.
        """
        if self._mapdata is None:
            self._mapdata = {}
        if "fipnum2region" in yamldata:
            self._mapdata["fipnum2region"] = yamldata["fipnum2region"]
            if "region2fipnum" not in yamldata:
                self._mapdata["region2fipnum"] = invert_map(
                    self._mapdata["fipnum2region"], skipstring=self.skipstring
                )
            self.has_fip2region = True
            self.has_region2fip = True

        if "region2fipnum" in yamldata:
            self._mapdata["region2fipnum"] = yamldata["region2fipnum"]
            if "fipnum2region" not in yamldata:
                logger.debug(self._mapdata["region2fipnum"])
                self._mapdata["fipnum2region"] = invert_map(
                    self._mapdata["region2fipnum"], skipstring=self.skipstring
                )
            self.has_fip2region = True
            self.has_region2fip = True

        if "fipnum2zone" in yamldata:
            self._mapdata["fipnum2zone"] = yamldata["fipnum2zone"]
            if "zone2fipnum" not in yamldata:
                self._mapdata["zone2fipnum"] = invert_map(
                    self._mapdata["fipnum2zone"], skipstring=self.skipstring
                )
            self.has_fip2zone = True
            self.has_zone2fip = True

        if "zone2fipnum" in yamldata:
            self._mapdata["zone2fipnum"] = yamldata["zone2fipnum"]
            if "fip2zone" not in yamldata:
                self._mapdata["fipnum2zone"] = invert_map(
                    self._mapdata["zone2fipnum"], skipstring=self.skipstring
                )
            self.has_fip2zone = True
            self.has_zone2fip = True

    def _fipdata_from_fmuconfigyaml(self, yamldict: dict):
        """This function should be able to build mapping from region/zones to
        FIPNUM based on data it finds in a fmu-config global_master_config.yml
        file.

        How that map should be deduced is not yet defined, and we only support
        having the explicit maps "region2fipnum" etc under the global section

        Args:
            yamldict (dict):
        """
        self._get_explicit_mapdata(yamldict["global"])

    def _fipdata_from_webvizyaml(self, yamldict: dict):
        """This function loads the Webviz yaml syntax for
        REGION/ZONE to FIPNUM mapping,

        The syntax is defined in
        https://github.com/equinor/webviz-subsurface/blob/master/webviz_subsurface/plugins/_reservoir_simulation_timeseries_regional.py#L1422

        Args:
            yamldict (dict):
        """
        self._get_explicit_mapdata(webviz_to_prtvol2csv(yamldict))

    def fip2region(self, fip: Union[list, int]) -> Union[list, str]:
        """Maps FIP(NUM) integers to Region strings.

        Args:
            array (list): List/array of FIPNUMS, or integer.

        Returns:
            Union[list, str]: Returns str or list, depending on input. Region
            names that are "integers" will be returned as strings.
        """
        if isinstance(fip, list):
            return list(map(self.fip2region, fip))
        assert "fipnum2region" in self._mapdata, "No data provided for fip2region"
        try:
            return self._mapdata["fipnum2region"][fip]
        except KeyError:
            logger.warning(
                "Unknown fip %s, known map is %s",
                str(fip),
                str(self._mapdata["fipnum2region"]),
            )
            return None

    def region2fip(self, region: Union[list, str]) -> Union[list, int]:
        """Maps Region string(s) to FIPNUM(s)

        Args:
            array (list): List/array of FIPNUMS, or integer.

        Returns:
            int: FIPNUM value. None if the region is unknown
        """
        if isinstance(region, list):
            return list(map(self.region2fip, region))
        assert "region2fipnum" in self._mapdata, "No data provided for region2fip"
        try:
            return int(self._mapdata["region2fipnum"][region])
        except KeyError:
            logger.warning(
                "Unknown region %s, known map is %s",
                str(region),
                str(self._mapdata["region2fipnum"]),
            )
            return None

    def fip2zone(self, fip: Union[list, int]) -> Union[list, str]:
        """Maps an array of FIPNUM integers to an array of Zone strings

        Args:
            array (list): List/array of FIPNUMS, or integer.

        Returns:
            list: Region strings. Always returned as list, and always as
            strings, even if zone "names" are integers.
        """
        if isinstance(fip, list):
            return list(map(self.fip2zone, fip))
        assert "fipnum2zone" in self._mapdata, "No data provided for fip2zone"
        try:
            return self._mapdata["fipnum2zone"][fip]
        except KeyError:
            logger.warning("The zone belonging to FIPNUM %s is unknown", str(fip))
            return None


def webviz_to_prtvol2csv(webvizdict: dict):
    """Convert a dict representation of a region/zone map in the Webviz format
    to the prtvol2csv format"""
    if "FIPNUM" in webvizdict and isinstance(webvizdict["FIPNUM"], dict):
        prtvoldict = dict()
        if "groups" in webvizdict["FIPNUM"]:
            if "REGION" in webvizdict["FIPNUM"]["groups"]:
                prtvoldict["region2fipnum"] = webvizdict["FIPNUM"]["groups"]["REGION"]
            if "ZONE" in webvizdict["FIPNUM"]["groups"]:
                prtvoldict["zone2fipnum"] = webvizdict["FIPNUM"]["groups"]["ZONE"]
        else:
            # The "groups" level might go away:
            if "REGION" in webvizdict["FIPNUM"]:
                prtvoldict["region2fipnum"] = webvizdict["FIPNUM"]["REGION"]
            if "ZONE" in webvizdict["FIPNUM"]:
                prtvoldict["zone2fipnum"] = webvizdict["FIPNUM"]["ZONE"]
        return prtvoldict
    return {}


def invert_map(
    dictmap: dict, join_on: str = ",", skipstring: Union[list, str] = None
) -> dict:
    """Invert a dictionary.

    When input is many-to-one, the keys will be joined with the supplied join
    string. Returned values inside dictionary will always be strings if joined,
    if not joined, the value type is unchanged.

    When the input is one-to-many,

    Args:
        dictmap (dict)
        join_on (str)
        skipstring: List of strings which will be ignored (e.g. "Totals").

    Returns:
        dict: Inverted map
    """
    if skipstring is None:
        skipstring = []
    if isinstance(skipstring, str):
        skipstring = [skipstring]

    inv_map = {}
    for key, value in dictmap.items():
        if key in skipstring or value in skipstring:
            continue
        if isinstance(value, list):
            for _value in value:
                inv_map[_value] = inv_map.get(_value, set()).union(set([key]))
        else:
            inv_map[value] = inv_map.get(value, set()).union(set([key]))
    assert join_on is not None, "A join operation must be specified"
    assert isinstance(join_on, str), f"The join_on must be a string, got {join_on}"
    for key, value in inv_map.items():
        inv_map[key] = list(inv_map[key])
        inv_map[key].sort()
        inv_map[key] = join_on.join(map(str, list(inv_map[key])))
    return inv_map
