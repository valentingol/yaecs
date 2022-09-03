"""
Reactive Reality Machine Learning Config System - Configuration object
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
from typing import Callable, Dict, List, Optional, Type, Union

from .config import ConfigDeclarator, Configuration


def get_template_class(
    default_config_path: Optional[ConfigDeclarator] = None,
    pre_processing_dict: Optional[Dict[str, Callable]] = None,
    post_processing_dict: Optional[Dict[str, Callable]] = None,
    additional_configs_suffix: Optional[str] = None,
    additional_configs_prefix: Optional[str] = None,
    variations_suffix: Optional[str] = None,
    variations_prefix: Optional[str] = None,
    grids_suffix: Optional[str] = None, grids_prefix: Optional[str] = None,
) -> Type[Configuration]:
    """
    Creates a template Configuration subclass to use in a small project
    where little customization is needed.
    :param default_config_path: path to the default config to use for
    the template
    :param pre_processing_dict: pre-processing dict to use for
    the template. If this gets large, consider implementing the subclass
    yourself as this will be clearer and more flexible.
    :param post_processing_dict: post-processing dict to use for
    the template. If this gets large, consider implementing the subclass
    yourself as this will be clearer and more flexible.
    :param additional_configs_suffix: automatically adds relevant
    pre-processing rules to consider parameter names ending with
    'additional_configs_suffix' as paths to additional config files
    :param additional_configs_prefix: automatically adds relevant
    pre-processing rules to consider parameter names starting with
    'additional_configs_prefix' as paths to additional config files
    :param variations_suffix: automatically adds relevant pre-processing
    rules to consider parameter names ending with 'variations_suffix'
    as config variations
    :param variations_prefix: automatically adds relevant pre-processing
    rules to consider parameter names starting with 'variations_prefix'
    as config variations
    :param grids_suffix: automatically adds relevant pre-processing
    rules to consider parameter names ending with 'grids_suffix'
    as grids
    :param grids_prefix: automatically adds relevant pre-processing
    rules to consider parameter names starting with 'grids_prefix'
    as grids
    :return: a template Configuration subclass
    """

    class Template(Configuration):
        """Template class."""

        @staticmethod
        def get_default_config_path():
            if default_config_path is not None:
                return default_config_path
            raise ValueError(
                "You are using a template class with no default config path. "
                "It can only be used with constructors which do not require "
                "access to a default config. "
                "Such constructors include :\n"
                " - build_from_configs\n"
                " - __init__ when config_path_or_dictionary is specified\n"
                " - any of load_config or build_from_argv when a default "
                "config is specified.")

        def parameters_pre_processing(self):
            to_ret = {} if pre_processing_dict is None else pre_processing_dict
            if additional_configs_suffix is not None:
                to_ret[f"*{additional_configs_suffix}"
                       ] = self.register_as_additional_config_file
            if additional_configs_prefix is not None:
                to_ret[f"{additional_configs_prefix}*"
                       ] = self.register_as_additional_config_file
            if variations_suffix is not None:
                to_ret[f"*{variations_suffix}"
                       ] = self.register_as_config_variations
            if variations_prefix is not None:
                to_ret[f"{variations_prefix}*"
                       ] = self.register_as_config_variations
            if grids_suffix is not None:
                to_ret[f"*{grids_suffix}"] = self.register_as_grid
            if grids_prefix is not None:
                to_ret[f"{grids_prefix}*"] = self.register_as_grid
            return to_ret

        def parameters_post_processing(self):
            return {} if post_processing_dict is None else post_processing_dict

    return Template


def make_config(*configs: Union[ConfigDeclarator, List[ConfigDeclarator]],
                config_class: Optional[Type[Configuration]] = None,
                pre_processing_dict: Optional[Dict[str, Callable]] = None,
                post_processing_dict: Optional[Dict[str, Callable]] = None,
                additional_configs_suffix: Optional[str] = None,
                additional_configs_prefix: Optional[str] = None,
                variations_suffix: Optional[str] = None,
                variations_prefix: Optional[str] = None,
                grids_suffix: Optional[str] = None,
                grids_prefix: Optional[str] = None, **class_building_kwargs,
                ) -> Configuration:
    """
    One-liner wrapper to create a config from dicts/strings without
    the need for declaring a subclass. Useful for scripts or jupyter
    notebooks. Impractical/hacky for larger projects.
    :param configs: dicts and strings defining a config
    :param config_class: class to use to build the configuration:
    If not provided, use a template instead.
    :param pre_processing_dict: pre-processing dict to use
    for the template. If this gets large, consider implementing
    the subclass yourself as this will be clearer and more flexible.
    Only used if config_class is not provided.
    :param post_processing_dict: post-processing dict to use
    for the template. If this gets large, consider implementing
    the subclass yourself as this will be clearer and more flexible.
    :param additional_configs_suffix: automatically adds relevant
    pre-processing rules to consider parameter names ending with
    'additional_configs_suffix' as paths to additional config files.
    Only used if config_class is not provided.
    :param additional_configs_prefix: automatically adds relevant
    pre-processing rules to consider parameter names starting with
    'additional_configs_prefix' as paths to additional config files
    :param variations_suffix: automatically adds relevant pre-processing
    rules to consider parameter names ending with 'variations_suffix'
    as config variations
    :param variations_prefix: automatically adds relevant pre-processing
    rules to consider parameter names starting with 'variations_prefix'
    as config variations
    :param grids_suffix: automatically adds relevant pre-processing
    rules to consider parameter names ending with 'grids_suffix'
    as grids
    :param grids_prefix: automatically adds relevant pre-processing
    rules to consider parameter names starting with 'grids_prefix'
    as grids
    :param class_building_kwargs: same kwargs as those used in all
    Configuration constructors
    :return: config object
    """
    if config_class is None:
        config_class = get_template_class(
            pre_processing_dict=pre_processing_dict,
            post_processing_dict=post_processing_dict,
            additional_configs_suffix=additional_configs_suffix,
            additional_configs_prefix=additional_configs_prefix,
            variations_suffix=variations_suffix,
            variations_prefix=variations_prefix, grids_suffix=grids_suffix,
            grids_prefix=grids_prefix,
        )
    elif (pre_processing_dict is not None
          or additional_configs_suffix is not None):
        print(
            "WARNING : 'pre_processing_dict' and 'additional_configs_suffix' "
            "are not used if config_class is given.")
    return config_class.build_from_configs(*configs, **class_building_kwargs)
