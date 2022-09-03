"""
Reactive Reality Machine Learning Config System - unit tests
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

from yaecs.user_utils import get_template_class, make_config


def load_config(*configs, default_config=None, preprocessing=None,
                postprocessing=None):
    return make_config(default_config, *configs,
                       pre_processing_dict=preprocessing,
                       post_processing_dict=postprocessing,
                       additional_configs_suffix="_path",
                       variations_suffix="var*", grids_suffix="grid",
                       do_not_merge_command_line=True)


def template(default_config=None):
    return get_template_class(default_config_path=default_config,
                              additional_configs_suffix="_path",
                              variations_suffix="var*", grids_suffix="grid")
