"""
Reactive Reality Machine Learning Config System - Usage example
(project- specific Configuration sub-class)
Copyright (C) 2022  Reactive Reality

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import random

from yaecs import Configuration


def check_model_type(model_type):
    assert model_type in ["linear", "polynomial"]
    return model_type


def check_params(param):
    if param is None:
        return None
    if param == "random":
        return random.random()
    assert isinstance(param, (int, float))
    return param


# This is literally the copy/pasted template given in
# framework/config/default_config_template
# There is however a few pre-processing functions added to provide with
# further guidance as to how to modify this class
class ProjectSpecificConfiguration(Configuration):
    """Default configuration template."""

    @staticmethod
    def get_default_config_path():
        return "./configs/default/main_config.yaml"

    def parameters_pre_processing(self):
        return {"model.type": check_model_type,
                "model.param*": check_params,
                "*_variation": self.register_as_config_variations,
                "grid": self.register_as_grid,
                "*path_to_config": self.register_as_additional_config_file,
                "*paths_to_configs": lambda x: [
                    self.register_as_additional_config_file(path)
                    for path in x]}
