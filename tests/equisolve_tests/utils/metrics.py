# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
#
# Copyright (c) 2023 Authors and contributors
# (see the AUTHORS.rst file for the full list of names)
#
# Released under the BSD 3-Clause "New" or "Revised" License
# SPDX-License-Identifier: BSD-3-Clause
import equistore
import numpy as np
from equistore import Labels, TensorBlock, TensorMap
from numpy.testing import assert_allclose, assert_equal

from equisolve.utils import rmse


class Testrmse:
    def test_values(self):
        """Test RMSE for the values in two TensorMaps."""
        y_true_data = np.array([[0.5, 1], [-1, 1], [7, -6]])[:, :, np.newaxis]
        y_pred_data = np.array([[0, 2], [-1, 2], [8, -5]])[:, :, np.newaxis]

        y_true = TensorMap(
            Labels.range("key", end=3),
            [equistore.block_from_array(y) for y in y_true_data],
        )
        y_pred = TensorMap(
            Labels.range("key", end=3),
            [equistore.block_from_array(y) for y in y_pred_data],
        )

        assert_allclose(
            rmse(y_true, y_pred, parameter_key="values"),
            [0.790569, 0.707107, 1.0],
            rtol=1e-6,
        )

    def test_gradients(self):
        """Test RMSE for the position gradients in two TensorMaps."""
        # Create training data

        num_properties = 5
        num_targets = 10
        mean = 3.3

        X_arr = np.random.normal(mean, 1, size=(4 * num_targets, num_properties))

        # Create training data
        X_values = X_arr[:num_targets]
        X_block = equistore.block_from_array(X_values)

        X_gradient_values = X_arr[num_targets:].reshape(num_targets, 3, num_properties)

        position_gradient_samples = Labels(
            ["sample", "structure", "atom"],
            np.array([[s, 1, 1] for s in range(num_targets)]),
        )

        gradient = TensorBlock(
            values=X_gradient_values,
            samples=position_gradient_samples,
            components=[Labels(["direction"], np.arange(3).reshape(-1, 1))],
            properties=X_block.properties,
        )
        X_block.add_gradient("positions", gradient)

        X = TensorMap(Labels.single(), [X_block])

        assert_equal(rmse(X, X, parameter_key="positions"), [0.0])
