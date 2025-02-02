# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
#
# Copyright (c) 2023 Authors and contributors
# (see the AUTHORS.rst file for the full list of names)
#
# Released under the BSD 3-Clause "New" or "Revised" License
# SPDX-License-Identifier: BSD-3-Clause

"""Functions for converting instances into an :class:`equistore.TensorMap`."""

from typing import List

import ase
import numpy as np
from equistore import Labels, TensorBlock, TensorMap


def ase_to_tensormap(
    frames: List[ase.Atoms], energy: str = None, forces: str = None, stress: str = None
) -> TensorMap:
    """Store informations from :class:`ase.Atoms`
    in a :class:`equistore.TensorMap`.

    :param frames:
        ase.Atoms or list of ase.Atoms
    :param energy:
        key for extracting energy per structure
    :param forces:
        key for extracting atomic forces
    :param stress:
        key for extracting stress per structure

    :returns:
        TensorMap containing the given information
    """
    if not isinstance(frames, list):
        frames = [frames]

    if energy is not None:
        values = [f.info[energy] for f in frames]
    else:
        energy = "energy"
        values = [f.get_potential_energy() for f in frames]

    if forces is not None:
        positions_gradients = [-f.arrays[forces] for f in frames]
    else:
        if (frames[0].get_calculator() is not None) and ("forces" in frames[0].get_calculator().implemented_properties):
            positions_gradients = [-f.get_forces() if (f.get_calculator() is not None) and ("forces" in f.get_calculator().implemented_properties)
                                                   else raise AttributeError(f"First frame has calculator with forces, so assumed all frames have forces but frame {i} does not have forces. Please add or remove forces as property everywhere.")
                                      for i, f in enumerate(frames)]
        else:
               positions_gradients = None
          

    if stress is not None:
        cell_gradients = [-f.info[stress] for f in frames]
    else:
        try:
            cell_gradients = [-f.get_stress(voigt=False) for f in frames]
        except ase.ase.calculators.calculator.PropertyNotImplementedError:
            cell_gradients = None

    return properties_to_tensormap(
        values, positions_gradients, cell_gradients, property_name=energy
    )


def properties_to_tensormap(
    values: List[float],
    positions_gradients: List[np.ndarray] = None,
    cell_gradients: List[np.ndarray] = None,
    is_structure_property: bool = True,
    property_name: str = "property",
) -> TensorMap:
    """Create a :class:`equistore.TensorMap` from array like properties.

    :param values:
        array like object of dimension N, for example the energies for each structure
    :param positions_gradients:
        list of length N with each entry i containing an array like objects with
        dimension (M_i, 3), for example the negative forces for each atom for all
        structures)
    :param cell_gradients:
        array like objects of dimension (N, 3, 3), for example the virial stress of
        a structure
    :param is_structure_property:
        boolean that determines if values correspond to a structure or atomic property,
        this property is not implemented yet.

    :raises ValueError:
        if the length of `values`, `positions_gradients` or `cell_gradients` is not the
        same.
    :raises ValueError:
        if each element in `positions_gradients` does not have 3 columns
    :raises ValueError:
        if each element in `cell_gradients` is not a 3x3 matrix.

    :returns:
        TensorMap containing the given properties
    """

    if not (is_structure_property):
        raise NotImplementedError(
            "Support for environment properties has not been implemented yet."
        )

    n_structures = len(values)

    block = TensorBlock(
        values=np.asarray(values).reshape(-1, 1),
        samples=Labels(["structure"], np.arange(n_structures).reshape(-1, 1)),
        components=[],
        properties=Labels([property_name], np.array([(0,)])),
    )

    if positions_gradients is not None:
        if n_structures != len(positions_gradients):
            raise ValueError(
                f"given {n_structures} values but "
                f"{len(positions_gradients)} positions_gradients values"
            )

        gradient_values = np.concatenate(positions_gradients, axis=0)

        if gradient_values.shape[1] != 3:
            raise ValueError(
                "positions_gradient must have 3 columns but have "
                f"{gradient_values.shape[1]}"
            )

        # The `"sample"` label refers to the index of the corresponding value in the
        # block. Here, the number of values is the same as the number of structures so
        # we can keep `"sample"` and `"structure"` the same.
        position_gradient_samples = Labels(
            ["sample", "structure", "atom"],
            np.array(
                [
                    [s, s, a]
                    for s in range(n_structures)
                    for a in range(len(positions_gradients[s]))
                ]
            ),
        )

        positions_gradient = TensorBlock(
            values=gradient_values.reshape(-1, 3, 1),
            samples=position_gradient_samples,
            components=[Labels(["direction"], np.arange(3).reshape(-1, 1))],
            properties=block.properties,
        )
        block.add_gradient("positions", positions_gradient)

    if cell_gradients is not None:
        if n_structures != len(cell_gradients):
            raise ValueError(
                f"given {n_structures} values but "
                f"{len(cell_gradients)} cell_gradients values"
            )

        gradient_values = np.asarray(cell_gradients)

        if gradient_values.shape[1:] != (3, 3):
            raise ValueError(
                "cell_gradient data must be a 3 x 3 matrix"
                f"but is {gradient_values.shape[1]} x {gradient_values.shape[2]}"
            )

        # the values of the sample labels are chosen in the same way as for the
        # positions_gradients. See comment above for a detailed explanation.
        cell_gradient_samples = Labels(
            ["sample"], np.array([[s] for s in range(n_structures)])
        )

        components = [
            Labels(["direction_1"], np.arange(3).reshape(-1, 1)),
            Labels(["direction_2"], np.arange(3).reshape(-1, 1)),
        ]

        cell_gradient = TensorBlock(
            values=gradient_values.reshape(-1, 3, 3, 1),
            samples=cell_gradient_samples,
            components=components,
            properties=block.properties,
        )
        block.add_gradient("cell", cell_gradient)

    return TensorMap(Labels.single(), [block])
