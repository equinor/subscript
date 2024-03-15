"""Engine part of casegen_upcars"""

import datetime
import io
import itertools
import math
from itertools import product

import numpy as np

from .udf import TERMINALCOLORS, listify, uniform_dist


def fracture_idx(matrix_elements, fracture_cell_count, boundary_fracture):
    """Return list of start of fracture cell index"""
    result = []
    if boundary_fracture:
        offset = 0
        result.append(offset)
        for idx in matrix_elements:
            offset += idx + fracture_cell_count
            result.append(offset)
    else:
        if len(matrix_elements) > 1:
            offset = matrix_elements[0]
            result.append(offset)
            for idx in matrix_elements[1:-1]:
                offset += idx + fracture_cell_count
                result.append(offset)
    return np.asarray(result, dtype=np.int16)


class Model:
    """
    Model class is responsible for creating the grid
    according to user specification and create
    a dictionary of input and calculated properties
    """

    def __init__(
        self,
        nMatrixX,
        nMatrixY,
        nz,
        dx,
        dy,
        dz,
        streak_k,
        streak_dz,
        streak_nz,
        streak_rect,
        fractureThickness,
        fracture_cell_count,
        fracture_at_boundary,
        top,
        radius_x,
        radius_y,
        radius_z,
        tilt,
        centroid_x=0.5,
        centroid_y=0.5,
        origin_x=0.0,
        origin_y=0.0,
        rotation=0.0,
        origin_x_pos=0.0,
        origin_y_pos=0.0,
        origin_top=0.0,
        fracture_length_x=1.0,
        fracture_offset_x=0.0,
        fracture_height_x=1.0,
        fracture_zoffset_x=0.0,
        fracture_length_y=1.0,
        fracture_offset_y=0.0,
        fracture_height_y=1.0,
        fracture_zoffset_y=0.0,
        seed=12345,
    ):
        """
        Initialize the model
        """
        self._eclipse_output_float = "12.8f"
        self._eclipse_output_float_compact = ".8f"
        self._eclipse_output_int = "8d"
        self._eclipse_output_per_line = 6

        streak_dz = listify(streak_dz, len(streak_k), float)
        assert len(streak_dz) == len(
            streak_k
        ), "Number of streak k-index is differs from number of streak dz"

        streak_nz = listify(streak_nz, len(streak_k), int)
        assert len(streak_nz) == len(
            streak_k
        ), "Number of streak k-index is differs from number of streak cell count (nz)"

        if isinstance(streak_rect, list) and len(streak_rect) > 0:
            if isinstance(streak_rect[0], list) and len(streak_rect) > 1:
                assert len(streak_rect) == len(
                    streak_k
                ), "Number of streak k-index is differs from number of streak box"
            elif isinstance(streak_rect[0], list):
                streak_rect = [streak_rect[0]] * len(streak_k)
            else:
                streak_rect = streak_rect * len(streak_k)
        else:
            streak_rect = [None] * len(streak_k)

        prts = [-1] * nz
        if streak_k is not None:
            for idx, (_k, _nz) in enumerate(zip(streak_k, streak_nz)):
                if _nz > 0:
                    if _k - 1 < 0 or _k + _nz - 1 > nz:
                        print(
                            TERMINALCOLORS["WARNING"]
                            + f"Warning: Streak #{idx + 1} is outside "
                            "background matrix.\n"
                            "The streak will be ignored." + TERMINALCOLORS["ENDC"]
                        )
                    else:
                        prts[_k - 1 : _k + _nz - 1] = [idx] * _nz

        layer_nz = []
        layer_dz = []
        layer_prt = []  # PRT of the layer, -1 for background matrix
        for key, group in itertools.groupby(prts):
            layer_nz.append(len(list(group)))
            layer_prt.append(key)
            if key < 0:
                layer_dz.append(dz)
            else:
                layer_dz.append(streak_dz[key])

        self.dict_info = {}
        self._matrix_x_arr = nMatrixX
        self._matrix_y_arr = nMatrixY
        self._matrix_x_count = len(nMatrixX)
        self._matrix_y_count = len(nMatrixY)
        self._nz = nz
        self._dx = dx
        self._dy = dy
        self._dz = dz

        self._streak_k = streak_k
        self._streak_dz = streak_dz
        self._streak_nz = streak_nz
        self._streak_rect = streak_rect

        self._fracture_thickness = fractureThickness
        self._fracture_cell_count = fracture_cell_count
        self._fracture_at_boundary = fracture_at_boundary
        self._top = top
        self._a = radius_x
        self._b = radius_y
        self._c = radius_z
        self._tilt = tilt
        self._centroid_x = centroid_x
        self._centroid_y = centroid_y
        self._seed_nr = seed
        self._origin_x = origin_x
        self._origin_y = origin_y
        self._rotation = rotation
        self._origin_x_pos = origin_x_pos
        self._origin_y_pos = origin_y_pos
        self._origin_top = origin_top

        self._n_faults_x = self._matrix_x_count + (1 if fracture_at_boundary else -1)
        self._n_faults_y = self._matrix_y_count + (1 if fracture_at_boundary else -1)

        self._fracture_length_x = listify(fracture_length_x, self._n_faults_y, float)
        self._fracture_offset_x = listify(fracture_offset_x, self._n_faults_y, float)
        self._fracture_height_x = listify(fracture_height_x, self._n_faults_y, float)
        self._fracture_zoffset_x = listify(fracture_zoffset_x, self._n_faults_y, float)
        for idx, (var, title) in enumerate(
            zip(
                [
                    self._fracture_length_x,
                    self._fracture_offset_x,
                    self._fracture_height_x,
                    self._fracture_zoffset_x,
                ],
                [
                    "fracture length",
                    "fracture offset",
                    "fracture height",
                    "fracture vertical offset",
                ],
            )
        ):
            if len(var) != self._n_faults_y:
                raise ValueError(
                    f"Number of specified X-dir {title} ({len(var)}) "
                    "is not equals to number of "
                    f"fracture in Y-direction ({self._n_faults_y})"
                )

        self._fracture_length_y = listify(fracture_length_y, self._n_faults_x, float)
        self._fracture_offset_y = listify(fracture_offset_y, self._n_faults_x, float)
        self._fracture_height_y = listify(fracture_height_y, self._n_faults_x, float)
        self._fracture_zoffset_y = listify(fracture_zoffset_y, self._n_faults_x, float)
        for idx, (var, title) in enumerate(
            zip(
                [
                    self._fracture_length_y,
                    self._fracture_offset_y,
                    self._fracture_height_y,
                    self._fracture_zoffset_y,
                ],
                [
                    "fracture length",
                    "fracture offset",
                    "fracture height",
                    "fracture vertical offset",
                ],
            )
        ):
            if len(var) != self._n_faults_x:
                raise ValueError(
                    f"Number of specified Y-dir {title} ({len(var)}) "
                    "is not equals to number of "
                    f"fracture in X-direction ({self._n_faults_x})"
                )

        self._total_nx = int(
            sum(self._matrix_x_arr) + self._fracture_cell_count * self._n_faults_x
        )
        self._total_ny = int(
            sum(self._matrix_y_arr) + self._fracture_cell_count * self._n_faults_y
        )
        self._total_nz = self._nz
        self._total_cells = self._total_nx * self._total_ny * self._total_nz
        self._total_matrix_cells = (
            sum(self._matrix_x_arr) * sum(self._matrix_y_arr) * self._nz
        )
        self._total_fracture_cells = self._total_cells - self._total_matrix_cells
        self._matrix_element_count = self._matrix_x_count * self._matrix_y_count

        self._lx = (
            sum(self._matrix_x_arr) * dx
            + self._fracture_cell_count * self._n_faults_x * self._fracture_thickness
        )
        self._ly = (
            sum(self._matrix_y_arr) * dy
            + self._fracture_cell_count * self._n_faults_y * self._fracture_thickness
        )
        self._lz = sum(np.multiply(layer_nz, layer_dz))

        self._fracture_i = fracture_idx(
            self._matrix_x_arr, self._fracture_cell_count, self._fracture_at_boundary
        )
        self._fracture_j = fracture_idx(
            self._matrix_y_arr, self._fracture_cell_count, self._fracture_at_boundary
        )

        self._matrix_i = self._fracture_i + self._fracture_cell_count
        self._matrix_j = self._fracture_j + self._fracture_cell_count
        if self._fracture_at_boundary:
            self._matrix_i = self._matrix_i[:-1]
            self._matrix_j = self._matrix_j[:-1]
        else:
            self._matrix_i = np.insert(self._matrix_i, 0, 0)
            self._matrix_j = np.insert(self._matrix_j, 0, 0)

        self._fracture_props = {
            "PORO": 0.0,
            "PERMX": [0.0] * self._n_faults_x,
            "PERMY": [0.0] * self._n_faults_y,
            "MULTX": 1.0,
            "MULTY": 1.0,
            "MULTPV": 1.0,
        }

        # Streak index : -1 for background index
        self._streak_idx = np.full((self._total_nx, self._total_ny, self._total_nz), -1)
        offset = 0
        streak_idx = -1
        for idx, (_prt, _nz) in enumerate(zip(layer_prt, layer_nz)):
            if _prt >= 0:
                # Streak
                streak_idx += 1
                _rect = streak_rect[_prt]
                if _rect is None or len(_rect) == 0:
                    box_i1 = 0
                    box_i2 = self._total_nx - 1
                    box_j1 = 0
                    box_j2 = self._total_ny - 1
                else:
                    box_i1 = max(0, _rect[0] - 1)
                    box_i2 = min(self._total_nx - 1, _rect[1] - 1)
                    box_j1 = max(0, _rect[2] - 1)
                    box_j2 = min(self._total_ny - 1, _rect[3] - 1)
                self._streak_rect[streak_idx] = [box_i1, box_i2, box_j1, box_j2]
                self._streak_idx[
                    box_i1 : box_i2 + 1, box_j1 : box_j2 + 1, offset : offset + _nz
                ] = _prt
            offset += _nz

        # Layer Index
        self._layer_idx = np.empty(
            (self._total_nx, self._total_ny, self._total_nz), dtype=np.int16
        )
        self._layer_dz = np.zeros(self._total_nz)
        # self._layer_nz = layer_nz
        offset = 0
        for idx, _layer_nz in enumerate(layer_nz):
            self._layer_idx[:, :, offset : offset + _layer_nz] = idx
            self._layer_dz[offset : offset + _layer_nz] = layer_dz[idx]
            offset += _layer_nz

        self._matrix_props = {
            "PORO": 0.0,
            "PERM": 0.0,
            "MULTX": 1.0,
            "MULTY": 1.0,
            "MULTPV": 1.0,
        }

        self._streak_props = {
            "PORO": [0.0] * len(self._streak_k),
            "PERM": [0.0] * len(self._streak_k),
            "MULTX": 1.0,
            "MULTY": 1.0,
            "MULTPV": 1.0,
        }

        self._vug_idx = np.zeros(
            (self._total_nx, self._total_ny, self._total_nz), dtype=np.int8
        )
        self._vug_props = {
            "PORO": [None, None],
            "PERM": [None, None],
            "MULTX": [-1.0, -1.0],
            "MULTY": [-1.0, -1.0],
            "MULTPV": [-1.0, -1.0],
        }

        self._porosity, self._permeability = np.zeros(
            (2, self._total_nx, self._total_ny, self._total_nz)
        )
        self._calc_porosity = False
        self._calc_permeability = False

        self._cell_volume = np.zeros((self._total_nx, self._total_ny, self._total_nz))

        self._throws = []

        print(
            f"""
Initializing model
  LX x LY x LZ: {self._lx} x {self._ly} x {self._lz}
  NX x NY x NZ: {self._total_nx} x {self._total_ny} x {self._total_nz}
  dx x dy x dz: {dx} x {dy} x {dz}
  Matrix Element in X-direction: {nMatrixY}
  Matrix Element in Y-direction: {nMatrixX}
  Layers: {nz}
  Shape Factor: {radius_x} (a), {radius_y} (b), {radius_z} (c)
  Top geometry: {top}
  Model origin top: {origin_top}
  Model origin: {origin_x}, {origin_y} at {origin_x_pos}, {origin_y_pos}
  Model coordinate rotation: {rotation}°
  Tilting: {tilt}
  Fracture:
    Thickness: {fractureThickness}
    Cell Count: {fracture_cell_count}
    At Boundary: {fracture_at_boundary}
    X-dir fractures:
      Length: {fracture_length_x}
      Offset: {fracture_offset_x}
      Height: {fracture_height_x}
      Z-offset: {fracture_zoffset_x}
    Y-dir fractures:
      Length: {fracture_length_y}
      Offset: {fracture_offset_y}
      Height: {fracture_height_y}
      Z-offset: {fracture_zoffset_y}
"""
        )
        self.dict_info["nx"] = self._total_nx
        self.dict_info["ny"] = self._total_ny
        self.dict_info["nz"] = self._total_nz
        self.dict_info["lx"] = self._lx
        self.dict_info["ly"] = self._ly
        self.dict_info["lz"] = self._lz
        self.dict_info["dx"] = self._dx
        self.dict_info["dy"] = self._dy
        self.dict_info["dz"] = self._dz
        self.dict_info["ft"] = self._fracture_thickness
        self.dict_info["mex"] = self._matrix_x_count
        self.dict_info["mey"] = self._matrix_y_count
        self.dict_info["matrixElements"] = self._matrix_element_count
        self.dict_info["fracPerMeterX"] = round(self._n_faults_x / self._lx * 1000.0, 2)
        self.dict_info["fracPerMeterY"] = round(self._n_faults_y / self._ly * 1000.0, 2)
        self.dict_info["nMatrixCellsTot"] = self._total_matrix_cells
        self.dict_info["nFracCells"] = self._total_fracture_cells
        self.dict_info["nCells"] = self._total_cells
        self.dict_info["originX"] = self._origin_x
        self.dict_info["originY"] = self._origin_y
        self.dict_info["rotation"] = self._rotation
        (
            self.dict_info["geometryFacX"],
            self.dict_info["geometryFacY"],
        ) = self._calculate_geometry_factor()

        self._build_grid()

        # Fracture Index
        # > 1 for fracture in i direction
        # < 1 for fracture in j direction
        # 0 for non-fracture
        self._fracture_idx = np.zeros(
            (self._total_nx, self._total_ny, self._total_nz), dtype=np.int16
        )
        # Use length instead of number of cells
        for _i, idx in enumerate(self._fracture_i):
            fracture_length = max(0.0, min(1.0, self._fracture_length_y[_i])) * self._ly
            start_fracture = (
                min(self._fracture_offset_y[_i], 1.0 - self._fracture_length_y[_i])
                * self._ly
            )
            start_fracture_idx = np.abs(self._y - start_fracture).argmin()
            end_fracture_idx = np.abs(
                self._y - (start_fracture + fracture_length)
            ).argmin()

            fracture_height = max(0.0, min(1.0, self._fracture_height_y[_i])) * self._lz
            start_fracture_vert = (
                min(self._fracture_zoffset_y[_i], 1.0 - self._fracture_height_y[_i])
                * self._lz
            )
            start_fracture_k = np.abs(self._z - start_fracture_vert).argmin()
            end_fracture_k = np.abs(
                self._z - (start_fracture_vert + fracture_height)
            ).argmin()

            self._fracture_idx[
                idx : idx + self._fracture_cell_count,
                start_fracture_idx:end_fracture_idx,
                start_fracture_k : end_fracture_k + 1,
            ] = _i + 1

        for _i, idx in enumerate(self._fracture_j):
            fracture_length = max(0.0, min(1.0, self._fracture_length_x[_i])) * self._lx
            start_fracture = (
                min(self._fracture_offset_x[_i], 1.0 - self._fracture_length_x[_i])
                * self._lx
            )
            start_fracture_idx = np.abs(self._x - start_fracture).argmin()
            end_fracture_idx = np.abs(
                self._x - (start_fracture + fracture_length)
            ).argmin()

            fracture_height = max(0.0, min(1.0, self._fracture_height_x[_i])) * self._lz
            start_fracture_vert = (
                min(self._fracture_zoffset_x[_i], 1.0 - self._fracture_height_x[_i])
                * self._lz
            )
            start_fracture_k = np.abs(self._z - start_fracture_vert).argmin()
            end_fracture_k = np.abs(
                self._z - (start_fracture_vert + fracture_height)
            ).argmin()
            self._fracture_idx[
                start_fracture_idx:end_fracture_idx,
                idx : idx + self._fracture_cell_count,
                start_fracture_k : end_fracture_k + 1,
            ] = -(_i + 1)

    def _build_grid(self):
        """Create the mesh xv, yv and zv"""
        if self._a * self._b * self._c == 0.0:
            self.dict_info["ModelDescription"] = f"Slab with tilting angle {self._tilt}"
        else:
            self.dict_info["ModelDescription"] = (
                "Dome structure with radius (x, y, z) : {:.2f}m, {:.2f}m, {:.2f}m"
            )

        x_mid = self._centroid_x * self._lx
        y_mid = self._centroid_y * self._ly

        rotation = np.radians(self._rotation)

        origin_x_base = self._origin_x_pos * self._lx
        origin_y_base = self._origin_y_pos * self._ly

        origin_x_turn = (
            math.cos(rotation) * origin_x_base + math.sin(rotation) * origin_y_base
        )
        origin_y_turn = (
            -math.sin(rotation) * origin_x_base + math.cos(rotation) * origin_y_base
        )

        cell_dx = np.full((self._total_nx, self._total_ny, self._total_nz), self._dx)
        cell_dy = np.full((self._total_nx, self._total_ny, self._total_nz), self._dy)
        cell_dz = np.empty((self._total_nx, self._total_ny, self._total_nz))

        for idx in self._fracture_i:
            cell_dx[idx : idx + self._fracture_cell_count, :, :] = (
                self._fracture_thickness
            )
        for idx in self._fracture_j:
            cell_dy[:, idx : idx + self._fracture_cell_count, :] = (
                self._fracture_thickness
            )
        for idx in range(self._nz):
            cell_dz[:, :, idx] = self._layer_dz[idx]
        self._cell_volume = cell_dx * cell_dy * cell_dz

        self._x = np.insert(np.cumsum(cell_dx[:, 0, 0]), 0, 0)
        self._y = np.insert(np.cumsum(cell_dy[0, :, 0]), 0, 0)
        self._z = np.insert(np.cumsum(cell_dz[0, 0, :]), 0, 0)

        self._xv, self._yv = np.meshgrid(self._x, self._y)
        if self._a * self._b * self._c != 0.0:
            origin_z = -self._c * np.sqrt(
                np.clip(
                    1.0
                    - (origin_x_base - x_mid) ** 2 / self._a**2
                    - (origin_y_base - y_mid) ** 2 / self._b**2,
                    0,
                    None,
                )
            ) + (origin_x_base - x_mid) * math.tan(math.radians(self._tilt))
            self._zv = -self._c * np.sqrt(
                np.clip(
                    1.0
                    - (self._xv - x_mid) ** 2 / self._a**2
                    - (self._yv - y_mid) ** 2 / self._b**2,
                    0,
                    None,
                )
            ) + (self._xv - x_mid) * math.tan(math.radians(self._tilt))
        else:
            origin_z = (origin_x_base - x_mid) * math.tan(math.radians(self._tilt))
            self._zv = (self._xv - x_mid) * math.tan(math.radians(self._tilt))

        rotationMatrix = np.array(
            [
                [np.cos(rotation), np.sin(rotation)],
                [-np.sin(rotation), np.cos(rotation)],
            ]
        )
        self._xv, self._yv = np.einsum(
            "ji, mni -> jmn", rotationMatrix, np.dstack([self._xv, self._yv])
        )

        self._xv += self._origin_x - origin_x_turn
        self._yv += self._origin_y - origin_y_turn

        if self._origin_top > 0:
            self._zv += self._origin_top - origin_z
        else:
            self._zv += self._top - self._zv.min()

    def distribute_property(self):
        """
        Calculate porosity and permeability for each cell
        """
        self._porosity = self._create_property(
            "Porosity",
            self._matrix_props["PORO"],
            self._streak_props["PORO"],
            self._fracture_props["PORO"],
            self._vug_props["PORO"],
        )
        self._permeability = self._create_anisotropy_property(
            "Permeability",
            self._matrix_props["PERM"],
            self._streak_props["PERM"],
            self._fracture_props["PERMX"],
            self._fracture_props["PERMY"],
            self._vug_props["PERM"],
        )

        pore_volume = self._porosity * self._cell_volume
        total_pore_volume = np.sum(pore_volume)
        self.dict_info["PoreVolume"] = round(total_pore_volume, 4)
        self.dict_info["avgPoro"] = round(
            total_pore_volume / np.sum(self._cell_volume), 4
        )

        self.dict_info["avgPermx"] = round(
            np.sum(pore_volume * self._permeability) / total_pore_volume, 3
        )

        self.dict_info["permxf"] = self._fracture_props["PERMX"]
        self.dict_info["permyf"] = self._fracture_props["PERMY"]
        self.dict_info["permxm"] = self._matrix_props["PERM"]
        self.dict_info["permxstreak"] = self._streak_props["PERM"]
        self.dict_info["porof"] = self._fracture_props["PORO"]
        self.dict_info["porom"] = self._matrix_props["PORO"]
        self.dict_info["porostreak"] = self._streak_props["PORO"]

    def calculate_avg_prop(
        self, matrix_property, streak_property, fracture_property, vug_property
    ):
        """Calculate the average properties"""
        props = self._create_property(
            "", matrix_property, streak_property, fracture_property, vug_property
        )
        pore_volume = self._porosity * self._cell_volume
        return round(np.sum(pore_volume * props) / np.sum(pore_volume), 4)

    def _create_property(
        self, keyword, matrix_property, streak_property, fracture_property, vug_property
    ):
        # pylint: disable=too-many-arguments
        streak_property = listify(streak_property, len(self._streak_k))
        assert len(streak_property) == len(
            self._streak_k
        ), f"Number of input {keyword} is not equal to number of streak"
        data_type = np.int16 if isinstance(fracture_property, int) else float
        props = np.empty(
            (self._total_nx, self._total_ny, self._total_nz), dtype=data_type
        )

        props[self._streak_idx == -1] = matrix_property

        for idx, prop in enumerate(streak_property):
            props[self._streak_idx == idx] = prop

        for idx, prop in enumerate(vug_property):
            props[self._vug_idx == idx + 1] = prop
        props[self._fracture_idx != 0] = fracture_property
        return props

    def _create_anisotropy_property(
        self,
        keyword,
        matrix_property,
        streak_property,
        fracture_x_property,
        fracture_y_property,
        vug_property,
    ):
        # pylint: disable=too-many-arguments
        """Distribute property in the cell with anisotropy in fracture property"""
        streak_property = listify(streak_property, len(self._streak_k))
        assert len(streak_property) == len(self._streak_k), (
            "Number of input " + keyword + " is not equal to number of streaks"
        )
        fracture_x_property = listify(fracture_x_property, self._n_faults_x)
        assert len(fracture_x_property) == self._n_faults_x, (
            "Number of input "
            + keyword
            + " is not equal to number fault in X- direction"
        )
        fracture_y_property = listify(fracture_y_property, self._n_faults_y)
        assert len(fracture_y_property) == self._n_faults_y, (
            "Number of input "
            + keyword
            + " is not equal to number fault in Y- direction"
        )
        data_type = np.int16 if isinstance(fracture_x_property, int) else float
        props = np.empty(
            (self._total_nx, self._total_ny, self._total_nz), dtype=data_type
        )
        props[self._streak_idx == -1] = matrix_property
        for idx, prop in enumerate(streak_property):
            props[self._streak_idx == idx] = prop
        for idx, prop in enumerate(vug_property):
            props[self._vug_idx == idx + 1] = prop
        for idx in range(self._n_faults_x):
            props[self._fracture_idx == (idx + 1)] = fracture_x_property[idx]
        for idx in range(self._n_faults_y):
            props[self._fracture_idx == -(idx + 1)] = fracture_y_property[idx]
        return props

    def set_layers_property(self, keyword, matrix_property, streak_property):
        """Store matrix and streak property"""
        streak_property = listify(streak_property, len(self._streak_k))
        assert len(streak_property) == len(
            self._streak_k
        ), f"Number of input {keyword} is not equal to number of streaks"
        keyword = keyword.upper()
        self._streak_props[keyword] = streak_property
        self._matrix_props[keyword] = matrix_property

    def set_fracture_property(self, keyword, value):
        """Store fracture property"""
        keyword = keyword.upper()
        self._fracture_props[keyword] = value

    def set_fracture_anisotropy_property(self, keyword, values_x, values_y):
        """Store fracture anisotropy property"""
        values_x = listify(values_x, self._n_faults_x)
        values_y = listify(values_y, self._n_faults_y)
        assert len(values_x) == self._n_faults_x, (
            f"Please specify correct number of fracture {keyword} for x-faults.\n"
            f"You need {self._n_faults_y} values"
        )
        assert len(values_y) == self._n_faults_y, (
            f"Please specify correct number of fracture {keyword} for y-faults.\n"
            f"You need {self._n_faults_y} values"
        )
        self._fracture_props[keyword + "X"] = values_x
        self._fracture_props[keyword + "Y"] = values_y

    def set_throws(self, throws):
        """Store throws information"""
        self._throws = throws

    def clear_throws(self):
        """Clear throws information"""
        self._throws = []

    def export_props(
        self, filename, keyword, matrix_prop, streak_prop, frac_props, vug_prop
    ):
        # pylint: disable=too-many-arguments
        """Print out grid property to Eclipse format file"""
        buffer_ = io.StringIO()
        print(
            "-- Property file generated using CaseGenerator "
            + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p"),
            file=buffer_,
        )
        print(f"-- Matrix property : {matrix_prop}", file=buffer_)
        print(f"-- Streak property : {streak_prop}", file=buffer_)
        print(f"-- Fracture property : {frac_props}", file=buffer_)
        print(f"-- Vug property : {vug_prop}", file=buffer_)
        self._print_property(
            buffer_,
            keyword,
            self._create_property(
                keyword, matrix_prop, streak_prop, frac_props, vug_prop
            ),
        )
        with open(filename, "w", encoding="utf8") as file_handle:
            file_handle.write(buffer_.getvalue())
        buffer_.close()

    def _get_surface_idx(self, _i, _j):
        """Return cell index of the surface"""
        offset = (_i - 1) * 2 + (_j - 1) * (4 * self._total_nx)
        return [
            offset,
            offset + 1,
            offset + 2 * self._total_nx,
            offset + 2 * self._total_nx + 1,
        ]

    def export_grdecl(self, filename):
        """Print out COORD, ZCORN, MULTX, MULTY and MULTPV to GRDECL file"""
        surface = np.repeat(self._zv[0], 2)[1:-1]
        for idx in range(1, self._total_ny + 1):
            surface = np.append(
                surface,
                np.tile(
                    np.repeat(self._zv[idx], 2)[1:-1], 2 if idx < self._total_ny else 1
                ),
            )
        n_surface_points = surface.size

        for throw in self._throws:
            surface[
                np.concatenate(
                    [
                        self._get_surface_idx(idx[0], idx[1])
                        for idx in list(
                            product(
                                list(range(throw[0], throw[1] + 1)),
                                list(range(throw[2], throw[3] + 1)),
                            )
                        )
                    ]
                )
            ] += throw[4]

        zcorn = np.zeros(8 * self._total_cells)
        zcorn[0:n_surface_points] = surface
        zcorn[n_surface_points : 2 * n_surface_points] = (
            zcorn[0:n_surface_points] + self._layer_dz[0]
        )

        for idx in range(1, self._total_nz):
            zcorn[n_surface_points * 2 * idx : n_surface_points * (2 * idx + 1)] = (
                zcorn[n_surface_points * (2 * idx - 1) : n_surface_points * (2 * idx)]
            )
            zcorn[
                n_surface_points * (2 * idx + 1) : 2 * n_surface_points * (idx + 1)
            ] = (
                zcorn[2 * n_surface_points * idx : n_surface_points * (2 * idx + 1)]
                + self._layer_dz[idx]
            )
        self.dict_info["top"] = zcorn.min()
        self.dict_info["bottom"] = zcorn.max()

        buffer_ = io.StringIO()
        print(
            "-- GRID generated using CaseGenerator "
            + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p"),
            file=buffer_,
        )
        print(
            f"-- {self._total_nx} x {self._total_ny} x {self._total_nz}",
            file=buffer_,
        )
        print("-- " + self.dict_info["ModelDescription"], file=buffer_)
        print("SPECGRID", file=buffer_)
        print(
            f"  {self._total_nx}  {self._total_ny}  {self._total_nz}  1  F",
            file=buffer_,
        )
        print("/", file=buffer_)

        print("COORD", file=buffer_)
        for _i in range(self._xv.shape[0]):
            for _j in range(self._xv.shape[1]):
                print(
                    # pylint: disable=consider-using-f-string
                    "{{x:{0}}} {{y:{0}}} {{z:{0}}} "
                    "{{x:{0}}} {{y:{0}}} {{z:{0}}}".format(
                        self._eclipse_output_float
                    ).format(x=self._xv[_i, _j], y=self._yv[_i, _j], z=0.0),
                    file=buffer_,
                )
        print("/", file=buffer_)
        self._print_property(buffer_, "ZCORN", zcorn)
        self._print_property(buffer_, "PORO", self._porosity)
        self._print_property(buffer_, "PERMX", self._permeability)

        for keyword in ["MULTX", "MULTY", "MULTPV"]:
            self._print_property(
                buffer_,
                keyword,
                self._create_property(
                    keyword,
                    self._matrix_props[keyword],
                    self._streak_props[keyword],
                    self._fracture_props[keyword],
                    self._vug_props[keyword],
                ),
            )
        with open(filename, "w", encoding="utf8") as file_handle:
            file_handle.write(buffer_.getvalue())
        buffer_.close()

    def _print_property(self, stream, keyword, array_value):
        props = array_value.reshape(array_value.size, order="f")
        if array_value.dtype.str[1] in ["i", "u"]:
            value_format = ""
        else:
            value_format = self._eclipse_output_float_compact

        print(keyword, file=stream)
        list_value = [props[0]]
        list_count = [1]
        for idx in range(1, len(props)):
            if props[idx] == list_value[-1]:
                list_count[-1] += 1
            else:
                list_value.append(props[idx])
                list_count.append(1)
        string_buffer = ""
        for idx, (count, value) in enumerate(zip(list_count, list_value)):
            string_new = (
                (" {0}*{1:" + value_format + "}").format(count, value)
                if count > 1
                else (" {:" + value_format + "}").format(value)
            )
            if len(string_buffer) + len(string_new) > 132:
                print(string_buffer, file=stream)
                string_buffer = string_new
            else:
                string_buffer += string_new
        print(string_buffer, file=stream)
        print("/", file=stream)
        print("", file=stream)

    def remove_vug(self):
        """
        Remove all vug distribution
        :return: None
        """
        self._vug_idx.fill(0)

    def bounded_box(self, i_1, i_2, j_1, j_2, k_1, k_2):
        # pylint: disable=too-many-arguments
        """Make sure the box is within model domain"""
        return [
            max(i_1, 0),
            min(i_2, self._total_nx - 1),
            max(j_1, 0),
            min(j_2, self._total_ny - 1),
            max(k_1, 0),
            min(k_2, self._total_nz - 1),
        ]

    def grow_box(self, box, growth):
        """
        Grow the box (i1, i2, j1, j2, k1, k2) outward by value of growth
        and make sure it is still within boundary
        """
        return self.bounded_box(
            box[0] - growth,
            box[1] + growth,
            box[2] - growth,
            box[3] + growth,
            box[4] - growth,
            box[5] + growth,
        )

    def set_vug(
        self,
        near_fracture_vug_fraction_dist,
        near_fracture_vug_permeability_dist,
        near_fracture_vug_porosity_dist,
        near_fracture_vug_distance_to_fracture,
        near_fracture_vug_multx,
        near_fracture_vug_multy,
        near_fracture_vug_multpv,
        near_fracture_vug_dispersion_factor,
        random_vug_fraction_dist,
        random_vug_permeability_dist,
        random_vug_porosity_dist,
        random_vug_multx,
        random_vug_multy,
        random_vug_multpv,
        near_streak_vug_fraction_dist,
        near_streak_vug_permeability_dist,
        near_streak_vug_porosity_dist,
        near_streak_vug_distance_to_streak,
        near_streak_vug_multx,
        near_streak_vug_multy,
        near_streak_vug_multpv,
        near_streak_vug_dispersion_factor,
    ):
        """Distribute all three types of vugs"""
        if (
            near_fracture_vug_fraction_dist[1]
            + random_vug_fraction_dist[1]
            + near_streak_vug_fraction_dist[1]
            == 0
        ):
            return

        self._vug_idx.fill(0)
        np.random.seed(self._seed_nr + 1)

        total_near_fracture_vug_cells = 0
        total_random_vug_cells = 0
        total_near_streak_vug_cells = 0

        # Near fracture vug distribution
        if near_fracture_vug_fraction_dist[1] > 0:
            vug_domain_flag = np.zeros(
                (self._total_nx, self._total_ny, self._total_nz), dtype=bool
            )
            total_near_fracture_vug_cells = int(
                np.rint(
                    np.random.uniform(
                        low=near_fracture_vug_fraction_dist[0],
                        high=near_fracture_vug_fraction_dist[1],
                        size=1,
                    )[0]
                    * self._total_matrix_cells
                )
            )
            thickness = 0
            while True:
                thickness += 1
                for cell_x in self._fracture_i:
                    x_min = max(
                        0, cell_x - near_fracture_vug_distance_to_fracture - thickness
                    )
                    x_max = min(
                        self._total_nx - 1,
                        cell_x + near_fracture_vug_distance_to_fracture + thickness,
                    )
                    vug_domain_flag[x_min, :, :] = True
                    vug_domain_flag[x_max, :, :] = True
                for cell_y in self._fracture_j:
                    y_min = max(
                        0, cell_y - near_fracture_vug_distance_to_fracture - thickness
                    )
                    y_max = min(
                        self._total_ny - 1,
                        cell_y + near_fracture_vug_distance_to_fracture + thickness,
                    )
                    vug_domain_flag[:, y_min, :] = True
                    vug_domain_flag[:, y_max, :] = True
                vug_domain_flag[self._fracture_idx != 0] = False
                vug_domain_flag[self._streak_idx != -1] = False
                for cell_x in self._fracture_i:
                    x_min = max(0, cell_x - near_fracture_vug_distance_to_fracture)
                    x_max = min(
                        self._total_nx - 1,
                        cell_x + near_fracture_vug_distance_to_fracture,
                    )
                    vug_domain_flag[x_min:x_max, :, :] = False

                for cell_y in self._fracture_j:
                    y_min = max(0, cell_y - near_fracture_vug_distance_to_fracture)
                    y_max = min(
                        self._total_ny - 1,
                        cell_y + near_fracture_vug_distance_to_fracture,
                    )
                    vug_domain_flag[:, y_min:y_max, :] = False

                vug_domain_size = np.count_nonzero(vug_domain_flag)
                if (
                    vug_domain_size / total_near_fracture_vug_cells
                    >= near_fracture_vug_dispersion_factor
                ):
                    break
            vug_flag = np.zeros(vug_domain_size)
            vug_flag[:total_near_fracture_vug_cells] = 1
            np.random.shuffle(vug_flag)
            self._vug_idx[:, :, :][vug_domain_flag] = vug_flag

        # Distribute vugs near streaks
        if len(self._streak_k) > 0 and near_streak_vug_fraction_dist[1] > 0:
            vug_domain_flag = np.zeros(
                (self._total_nx, self._total_ny, self._total_nz), dtype=bool
            )
            streak_domain_flag = np.zeros(
                (self._total_nx, self._total_ny, self._total_nz), dtype=bool
            )
            total_near_streak_vug_cells = int(
                np.rint(
                    np.random.uniform(
                        low=near_streak_vug_fraction_dist[0],
                        high=near_streak_vug_fraction_dist[1],
                        size=1,
                    )[0]
                    * self._total_matrix_cells
                )
            )
            streak_box = []
            for _k, nz_size, rect in zip(
                self._streak_k, self._streak_nz, self._streak_rect
            ):
                _k -= 1
                box = self.bounded_box(
                    rect[0] - near_streak_vug_distance_to_streak,
                    rect[1] + near_streak_vug_distance_to_streak,
                    rect[2] - near_streak_vug_distance_to_streak,
                    rect[3] + near_streak_vug_distance_to_streak,
                    _k - near_streak_vug_distance_to_streak,
                    _k + nz_size - 1 + near_streak_vug_distance_to_streak,
                )
                streak_box.append(box)
                streak_domain_flag[
                    box[0] : box[1] + 1, box[2] : box[3] + 1, box[4] : box[5] + 1
                ] = True
            thickness = 0
            while True:
                thickness += 1
                for box in streak_box:
                    vug_box = self.grow_box(box, thickness)
                    vug_domain_flag[
                        vug_box[0] : vug_box[1] + 1,
                        vug_box[2] : vug_box[3] + 1,
                        vug_box[4] : vug_box[5] + 1,
                    ] = True

                vug_domain_flag[self._fracture_idx != 0] = False
                vug_domain_flag[streak_domain_flag] = False

                vug_domain_size = np.count_nonzero(vug_domain_flag)
                if (
                    vug_domain_size
                    >= near_streak_vug_dispersion_factor * total_near_streak_vug_cells
                ):
                    break
            vugs_flag = np.zeros(vug_domain_size)
            vugs_flag[:total_near_streak_vug_cells] = 3
            np.random.shuffle(vugs_flag)
            self._vug_idx[vug_domain_flag] = vugs_flag

        # Random vug
        if random_vug_fraction_dist[1] > 0:
            vug_domain_flag = np.ones(
                (self._total_nx, self._total_ny, self._total_nz), dtype=bool
            )
            total_random_vug_cells = int(
                np.rint(
                    np.random.uniform(
                        low=random_vug_fraction_dist[0],
                        high=random_vug_fraction_dist[1],
                        size=1,
                    )[0]
                    * self._total_matrix_cells
                )
            )
            vug_domain_flag[self._vug_idx != 0] = False
            vug_domain_flag[self._streak_idx != -1] = False
            vug_domain_flag[self._fracture_idx != 0] = False
            vug_flag = np.zeros(np.count_nonzero(vug_domain_flag))
            vug_flag[:total_random_vug_cells] = 2
            np.random.shuffle(vug_flag)
            self._vug_idx[vug_domain_flag] = vug_flag

        final_near_fracture_vug_cells = np.count_nonzero(self._vug_idx == 1)
        if total_near_fracture_vug_cells != final_near_fracture_vug_cells:
            total_fraction = (
                float(total_near_fracture_vug_cells) / self._total_matrix_cells
            )
            final_fraction = (
                float(final_near_fracture_vug_cells) / self._total_matrix_cells
            )
            print(
                TERMINALCOLORS["WARNING"]
                + "Warning: Near fracture vugs fraction is reduced from "
                + f" {total_fraction:.2%} to {final_fraction:.2%} "
                + "as they overlaps with near streak vugs"
                + TERMINALCOLORS["ENDC"]
            )
            total_near_fracture_vug_cells = final_near_fracture_vug_cells

        self._vug_props["PORO"] = [
            uniform_dist(
                near_fracture_vug_porosity_dist[0],
                near_fracture_vug_porosity_dist[1],
                total_near_fracture_vug_cells,
                self._seed_nr + 2,
            ),
            uniform_dist(
                random_vug_porosity_dist[0],
                random_vug_porosity_dist[1],
                total_random_vug_cells,
                self._seed_nr + 3,
            ),
            uniform_dist(
                near_streak_vug_porosity_dist[0],
                near_streak_vug_porosity_dist[1],
                total_near_streak_vug_cells,
                self._seed_nr + 101,
            ),
        ]

        self._vug_props["PERM"] = [
            uniform_dist(
                near_fracture_vug_permeability_dist[0],
                near_fracture_vug_permeability_dist[1],
                total_near_fracture_vug_cells,
                self._seed_nr + 4,
            ),
            uniform_dist(
                random_vug_permeability_dist[0],
                random_vug_permeability_dist[1],
                total_random_vug_cells,
                self._seed_nr + 5,
            ),
            uniform_dist(
                near_streak_vug_permeability_dist[0],
                near_streak_vug_permeability_dist[1],
                total_near_streak_vug_cells,
                self._seed_nr + 102,
            ),
        ]

        self._vug_props["MULTPV"] = [
            near_fracture_vug_multpv,
            random_vug_multpv,
            near_streak_vug_multpv,
        ]
        self._vug_props["MULTX"] = [
            near_fracture_vug_multx,
            random_vug_multx,
            near_streak_vug_multx,
        ]
        self._vug_props["MULTY"] = [
            near_fracture_vug_multy,
            random_vug_multy,
            near_streak_vug_multy,
        ]

        self._vug_props["MULTY"] = [
            near_fracture_vug_multy,
            random_vug_multy,
            near_streak_vug_multy,
        ]
        self._vug_props["MULTY"] = [
            near_fracture_vug_multy,
            random_vug_multy,
            near_streak_vug_multy,
        ]

    def _calculate_geometry_factor(self):
        """
        Calculate geometry factor which describes size-relationship between
        center-blocks and north/south or east/west blocks
            1   : all matrix blocks equal size
            > 1 : N/S- or E/W- blocks are larger than center blocks
            < 1 : center blocks are larger than N/S- or E/W- blocks
        """
        result = [0] * 2
        for idx, val in enumerate([self._matrix_x_arr, self._matrix_y_arr]):
            if len(val) < 3:
                result[idx] = 0.0
            else:
                idx_start = int(round(len(val) / 3.0))
                idx_end = int(round(len(val) * 2.0 / 3.0))
                center_block = sum(val[idx_start:idx_end])
                result[idx] = 0.5 * (sum(val) - center_block - 1)
        return result[0], result[1]
