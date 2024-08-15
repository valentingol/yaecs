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
import logging
from typing import Callable, Dict, List, Optional, Type, Union

from .config.config import Configuration
from .yaecs_utils import ConfigInput, ConfigDeclarator, TqdmLogger, get_config_from_argv, is_config_in_argv

YAECS_LOGGER = logging.getLogger(__name__)


def tqdm_file():
    """
    Utility function which returns a file to which users can log their TQDM bars to make them YAECS-friendly.

    :return: TQDM file
    """
    return TqdmLogger(logging.getLogger("yaecs.print_catcher"))


def get_template_class(default_config_path: Optional[ConfigDeclarator] = None,
                       pre_processing_dict: Optional[Dict[str, Callable]] = None,
                       post_processing_dict: Optional[Dict[str, Callable]] = None,
                       experiment_path: str = None, tracker_config: str = None,
                       additional_configs_suffix: Optional[str] = None,
                       additional_configs_prefix: Optional[str] = None,
                       variations_suffix: Optional[str] = None, variations_prefix: Optional[str] = None,
                       grids_suffix: Optional[str] = None, grids_prefix: Optional[str] = None) -> Type[Configuration]:
    """
    Creates a template Configuration subclass to use in a small project where little customisation is needed.

    :param default_config_path: path to the default config to use for the template
    :param pre_processing_dict: pre-processing dict to use for the template. If this gets large, consider implementing
        the subclass yourself as this will be clearer and more flexible.
    :param post_processing_dict: post-processing dict to use for the template. If this gets large, consider implementing
        the subclass yourself as this will be clearer and more flexible.
    :param experiment_path: automatically adds relevant pre-processing rules to consider given parameter name the
        experiment path
    :param tracker_config: automatically adds relevant pre-processing rules to consider given parameter name the tracker
        config
    :param additional_configs_suffix: automatically adds relevant pre-processing rules to consider parameter names
        ending with 'additional_configs_suffix' as paths to additional config files
    :param additional_configs_prefix: automatically adds relevant pre-processing rules to consider parameter names
        starting with 'additional_configs_prefix' as paths to additional config files
    :param variations_suffix: automatically adds relevant pre-processing rules to consider parameter names ending with
        'variations_suffix' as config variations
    :param variations_prefix: automatically adds relevant pre-processing rules to consider parameter names starting with
        'variations_prefix' as config variations
    :param grids_suffix: automatically adds relevant pre-processing rules to consider parameter names ending with
        'grids_suffix' as grids
    :param grids_prefix: automatically adds relevant pre-processing rules to consider parameter names starting with
        'grids_prefix' as grids
    :return: a template Configuration subclass
    """

    class Template(Configuration):
        """Template class."""

        @staticmethod
        def get_default_config_path() -> str:
            if default_config_path is not None:
                return default_config_path
            raise ValueError(
                "You are using a template class with no default config path. It can only be used with constructors "
                "which do not require access to a default config. Such constructors include :\n"
                " - build_from_configs\n"
                " - __init__ when config_path_or_dictionary is specified\n"
                " - any of load_config or build_from_argv when a default config is specified.")

        def parameters_pre_processing(self) -> Dict[str, Callable]:
            to_ret = {} if pre_processing_dict is None else pre_processing_dict
            if additional_configs_suffix is not None:
                to_ret[f"*{additional_configs_suffix}"] = self.register_as_additional_config_file
            if additional_configs_prefix is not None:
                to_ret[f"{additional_configs_prefix}*"] = self.register_as_additional_config_file
            if variations_suffix is not None:
                to_ret[f"*{variations_suffix}"] = self.register_as_config_variations
            if variations_prefix is not None:
                to_ret[f"{variations_prefix}*"] = self.register_as_config_variations
            if grids_suffix is not None:
                to_ret[f"*{grids_suffix}"] = self.register_as_grid
            if grids_prefix is not None:
                to_ret[f"{grids_prefix}*"] = self.register_as_grid
            if tracker_config is not None:
                to_ret[f"{tracker_config}"] = self.register_as_tracker_config
            return to_ret

        def parameters_post_processing(self) -> Dict[str, Callable]:
            to_ret = {} if post_processing_dict is None else post_processing_dict
            if experiment_path is not None:
                to_ret[f"{experiment_path}"] = self.register_as_experiment_path
            return to_ret

    return Template


def make_config(*configs: Union[ConfigDeclarator, List[ConfigDeclarator]],
                config_class: Optional[Type[Configuration]] = None,
                pre_processing_dict: Optional[Dict[str, Callable]] = None,
                post_processing_dict: Optional[Dict[str, Callable]] = None,
                experiment_path: str = None, tracker_config: str = None,
                additional_configs_suffix: Optional[str] = None, additional_configs_prefix: Optional[str] = None,
                variations_suffix: Optional[str] = None, variations_prefix: Optional[str] = None,
                grids_suffix: Optional[str] = None, grids_prefix: Optional[str] = None,
                fallback: Optional[ConfigInput] = "{}", pattern: str = "--config",
                **class_building_kwargs) -> Configuration:
    """
    One-liner wrapper to create a config from dicts/strings without the need for declaring a subclass. Useful for
    scripts or jupyter notebooks. Impractical/hacky for larger projects.

    :param configs: dicts and strings defining a config
    :param config_class: class to use to build the configuration. If not provided, use a template instead.
    :param pre_processing_dict: pre-processing dict to use for the template.
        If this gets large, consider implementing the subclass yourself as this will be clearer and more flexible.
        Only used if config_class is not provided.
    :param post_processing_dict: post-processing dict to use for the template.
        If this gets large, consider implementing the subclass yourself as this will be clearer and more flexible.
    :param experiment_path: automatically adds relevant pre-processing rules to consider given parameter name the
        experiment path.
        Only used if config_class is not provided.
    :param tracker_config: automatically adds relevant pre-processing rules to consider given parameter name the tracker
        config.
        Only used if config_class is not provided.
    :param additional_configs_suffix: automatically adds relevant pre-processing rules to consider parameter names
        ending with 'additional_configs_suffix' as paths to additional config files.
        Only used if config_class is not provided.
    :param additional_configs_prefix: automatically adds relevant pre-processing rules to consider parameter names
        starting with 'additional_configs_prefix' as paths to additional config files.
        Only used if config_class is not provided.
    :param variations_suffix: automatically adds relevant pre-processing rules to consider parameter names ending with
        'variations_suffix' as config variations.
        Only used if config_class is not provided.
    :param variations_prefix: automatically adds relevant pre-processing rules to consider parameter names starting with
        'variations_prefix' as config variations.
        Only used if config_class is not provided.
    :param grids_suffix: automatically adds relevant pre-processing rules to consider parameter names ending with
        'grids_suffix' as grids.
        Only used if config_class is not provided.
    :param grids_prefix: automatically adds relevant pre-processing rules to consider parameter names starting with
        'grids_prefix' as grids.
        Only used if config_class is not provided.
    :param fallback: if provided, use this as a fallback when no config is provided in argv. The default value "{}"
        stands for "by default do not merge anything if no merge pattern is found in argv"
    :param pattern: pattern to use to find the config in argv.
    :param class_building_kwargs: same kwargs as those used in all Configuration constructors.
        Only used if config_class is not provided.
    :return: config object
    """

    # Prepare class
    class_args = {
        "pre_processing_dict": pre_processing_dict, "post_processing_dict": post_processing_dict,
        "experiment_path": experiment_path, "tracker_config": tracker_config,
        "additional_configs_suffix": additional_configs_suffix, "additional_configs_prefix": additional_configs_prefix,
        "variations_suffix": variations_suffix, "variations_prefix": variations_prefix,
        "grids_suffix": grids_suffix, "grids_prefix": grids_prefix,
    }
    if config_class is None:
        config_class = get_template_class(**class_args)
    elif any(arg is not None for arg in class_args.values()):
        YAECS_LOGGER.warning("WARNING : The following arguments are not used if config_class is provided :\n"
                             f"{list(class_args.keys())}.")

    # Get configs from argv
    configs_from_argv = get_config_from_argv(pattern=pattern, fallback={} if fallback == "{}" else fallback)
    class_building_kwargs["from_argv"] = pattern if is_config_in_argv(pattern=pattern) else ""
    if all(c == {} for c in configs_from_argv):
        configs_from_argv = []
        class_building_kwargs["from_argv"] = ""

    return config_class.build_from_configs(*configs, *configs_from_argv, **class_building_kwargs)
