"""
Reactive Reality Machine Learning Config System - Usage example
(various utility functions and classes)
Copyright (C) 2022  Reactive Reality

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Lesser Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os

import numpy as np
from scipy import stats


class Metrics:
    """Metrics class utilities."""

    @staticmethod
    def exponential_l2(ground_truth, predictions):
        return ((np.exp(ground_truth) - predictions)**2).mean()

    @staticmethod
    def square_root_l2(ground_truth, predictions):
        return ((np.sqrt(1 + ground_truth) - predictions)**2).mean()


def create_data(data_config):
    mu = data_config.generation.mean  # pylint: disable=invalid-name
    sigma = data_config.generation.variance
    train = stats.truncnorm((-1 - mu) / sigma, (1-mu) / sigma, loc=mu,
                            scale=sigma).rvs(data_config.train.size)
    test = stats.truncnorm((-1 - mu) / sigma, (1-mu) / sigma, loc=mu,
                           scale=sigma).rvs(data_config.test.size)
    return train, test


def create_and_train_model(model_config, train_samples):

    def model(x):
        if model_config.type == "linear":
            return (1 + x * model_config.param1 + x * model_config.param2
                    + x * model_config.param3)
        if model_config.type == "polynomial":
            return (1 + x * model_config.param1
                    + np.power(x, 2) * model_config.param2
                    + np.power(x, 3) * model_config.param3)
        return None

    # Added train samples for reference, but they're not actually used here
    _ = train_samples
    return model


def test_model_and_return_metrics(model, test_samples, metrics):
    predictions = model(test_samples)
    return {
        metric: getattr(Metrics, metrics[metric])(test_samples, predictions)
        for metric in metrics
    }


def log_experiment(config, metrics):
    exp_dir = os.path.join("log", config.name)
    if not os.path.exists(exp_dir):
        os.makedirs(exp_dir)
    run_dir = os.path.join(exp_dir, f"run_{len(os.listdir(exp_dir))}")
    os.makedirs(run_dir)
    config.save(os.path.join(run_dir, "config_save.yaml"))
    with open(os.path.join(run_dir, "metrics.json"), 'w',
              encoding='utf-8') as fil:
        json.dump(metrics, fil)
