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
import sys
import time
from typing import Callable, Dict, List, Optional

from ..yaecs_utils import ConfigInput, ConfigDeclarator, format_str, get_config_from_argv
from .config_base import _ConfigurationBase

YAECS_LOGGER = logging.getLogger(__name__)


class Configuration(_ConfigurationBase):
    """
    Superclass for YAECS configurations. The superclass implements constructors, while the behaviour is spread
    across the parent classes in the following way :

    * _ConfigurationBase implements the most basic functionalities such as creation and merging operations. It inherits
      from all other parent classes as Mixins ;
    * ConfigHooksMixin implements processing functions whose name start with `register_as_` and are decorated by the
      yaecs_utils.hook decorator. Users can use those processing either as pre- or post-processing functions, which will
      have the added effect of tagging the processed parameters as playing a certain pre-defined role in the config ;
    * ConfigGettersMixin implements public getters to access some private attributes as well as other values which
      require boilerplate code to be rigorously queried, such as user-defined parameters ;
    * ConfigSettersMixin implements a few setters which the config uses internally to manipulate private attributes of
      other Configuration instances (such as sub-configs) ;
    * ConfigConvenienceMixin implements all functions which are not of central importance to the behaviour of the config
      but wrap convenient functionalities which can be used either internally of by the user.

    """

    def __init__(self, name: str = "main", overwriting_regime: str = "auto-save",
                 config_path_or_dictionary: Optional[ConfigDeclarator] = None,
                 nesting_hierarchy: Optional[List[str]] = None, state: Optional[List[str]] = None,
                 main_config: Optional['Configuration'] = None, variation: Optional[str] = None,
                 do_not_pre_process: bool = False, do_not_post_process: bool = False, verbose: bool = True,
                 **kwargs):
        """
        Should never be called directly by the user. Please use one of the constructors instead (load_config,
        build_from_configs, build_from_argv), or the utils.make_config convenience function.

        :param name: name for the config or sub-config
        :param overwriting_regime: can be "auto-save" (default, when a param is overwritten it is merged instead and the
            config is saved automatically if it had been saved previously), "locked" (params can't be overwritten except
            using merge explicitly) or "unsafe" (params can be freely overwritten but reproducibility
            is not guaranteed).
        :param config_path_or_dictionary: path or dictionary to create the config from
        :param nesting_hierarchy: list containing the names of all the configs in the sub-config chain leading to this
            config
        :param state: processing state used for state tracking and debugging
        :param main_config: main config corresponding to this sub-config, or None if this config is the main config
        :param variation: the name of the variation being created
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        :param verbose: if set to false, message logging by this config will be deactivated
        :raises ValueError: if the overwriting regime is not valid
        :return: none
        """

        # PROTECTED ATTRIBUTES
        object.__setattr__(self, "_operating_creation_or_merging", True)
        self._state = [] if state is None else state
        self._main_config = self if main_config is None else main_config
        self._methods = [name for name in dir(self)
                         if name not in ["_operating_creation_or_merging", "_main_config", "_state"]]
        self._configuration_variations = []
        self._configuration_variations_names = []
        self._grids = []
        self._name = name
        self._nesting_hierarchy = ([] if nesting_hierarchy is None else list(nesting_hierarchy))
        self._variation_name = (variation if main_config is None else main_config.get_variation_name())
        self._verbose = verbose
        kwargs = {"do_not_pre_process": do_not_pre_process, "do_not_post_process": do_not_post_process, **kwargs}
        super().__init__(**kwargs)
        self._protected_attributes = list(self.__dict__) + ["_protected_attributes"]

        # SPECIAL ATTRIBUTES
        self.config_metadata = {
            "saving_time": time.time(),
            "config_hierarchy": [],
            "overwriting_regime": (overwriting_regime if main_config is None
                                   else main_config.config_metadata["overwriting_regime"]),
        }
        if self.config_metadata["overwriting_regime"] not in ["unsafe", "auto-save", "locked"]:
            raise ValueError("'overwriting_regime' needs to be either 'auto-save', "
                             "'locked' or 'unsafe'.")

        # INITIALISATION
        self._state.append(f"setup;{self._name}")
        config_path_or_dictionary = (self.get_default_config_path()
                                     if config_path_or_dictionary is None else config_path_or_dictionary)
        self.init_from_config(config_path_or_dictionary)
        self.config_metadata["config_hierarchy"] = ([] if not self._nesting_hierarchy else list(
            main_config.get('.'.join(self._nesting_hierarchy[:-1]), main_config).config_metadata['config_hierarchy']))
        self.config_metadata["config_hierarchy"] += [config_path_or_dictionary]
        if not self._nesting_hierarchy:
            self._check_for_unlinked_sub_configs()
        if main_config is None:
            self.set_pre_processing(True)
        self._state.pop(-1)
        self._operating_creation_or_merging = False

    @classmethod
    def load_config(cls, *configs: ConfigInput, default_config_path: Optional[ConfigDeclarator] = None,
                    overwriting_regime: str = "auto-save", do_not_merge_command_line: bool = False,
                    do_not_pre_process: bool = False, do_not_post_process: bool = False,
                    **kwargs) -> 'Configuration':
        """
        First creates a config using the default config, then merges config_path into it. If config_path is a list,
        successively merges all configs in the list instead from index 0 to the last.

        :param configs: config's path or dictionary, or list of default config's paths or dictionaries to merge
        :param default_config_path: default config's path or dictionary
        :param overwriting_regime: can be "auto-save" (default, when a param is overwritten it is merged instead and the
            config is saved automatically if it had been saved previously), "locked" (params can't be overwritten except
            using merge explicitly) or "unsafe" (params can be freely overwritten but reproducibility
            is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to merge the command line parameters
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        :param kwargs: additional parameters to pass to Configuration
        :return: instance of Configuration object containing the desired config
        """
        # This needs to access protected members of the Configuration class several times to prepare the config
        # pylint: disable=protected-access
        default_config_path = (cls.get_default_config_path() if default_config_path is None else default_config_path)
        if kwargs.get("verbose", True):
            YAECS_LOGGER.info(f"Building config from default : {format_str(default_config_path)}")
        config = cls(config_path_or_dictionary=default_config_path, overwriting_regime=overwriting_regime,
                     do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process, **kwargs)
        if configs and isinstance(configs[0], list):
            configs = configs[0]
        for path in configs:
            config._merge(path, do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process)
        if not do_not_merge_command_line:
            to_merge = config._gather_command_line_dict()
            if to_merge:
                config._merge(to_merge, do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process,
                              source="command line")
        config._post_process_modified_parameters()
        config.set_post_processing(True)
        return config

    @classmethod
    def build_from_configs(cls, *configs: ConfigInput, overwriting_regime: str = "auto-save",
                           do_not_merge_command_line: bool = False, do_not_pre_process: bool = False,
                           do_not_post_process: bool = False, **kwargs) -> 'Configuration':
        """
        First creates a config using the first config provided (or the first config in the provided list), then merges
        the subsequent configs into it from index 1 to the last.

        :param configs: config's path or dictionary, or list of default config's paths or dictionaries to merge
        :param overwriting_regime: can be "auto-save" (default, when a param is overwritten it is merged instead and the
            config is saved automatically if it had been saved previously), "locked" (params can't be overwritten except
            using merge explicitly) or "unsafe" (params can be freely overwritten but reproducibility
            is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to merge the command line parameters
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        :param kwargs: additional parameters to pass to Configuration
        :raises TypeError: if configs is invalid
        :return: instance of Configuration object containing the desired config
        """
        if not configs or (isinstance(configs[0], list) and not configs[0]):
            raise TypeError("build_from_configs needs to be called with "
                            "at least one config.")
        if isinstance(configs[0], list) and len(configs) == 1:
            configs = configs[0]
        elif isinstance(configs[0], list):
            raise TypeError(f"Invalid argument : '{configs}'\n"
                            "please use build_from_configs([cfg1, cfg2, ...]) or "
                            "build_from_configs(cfg1, cfg2, ...)")
        return cls.load_config(list(configs[1:]), default_config_path=configs[0], overwriting_regime=overwriting_regime,
                               do_not_merge_command_line=do_not_merge_command_line,
                               do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process, **kwargs)

    @classmethod
    def build_from_argv(cls, *configs: ConfigInput, fallback: Optional[ConfigInput] = None, pattern: str = "--config",
                        default_config_path: Optional[ConfigDeclarator] = None, overwriting_regime: str = "auto-save",
                        do_not_merge_command_line: bool = False, do_not_pre_process: bool = False,
                        do_not_post_process: bool = False, **kwargs) -> 'Configuration':
        """
        Assumes a pattern of the form '--config <path_to_config>' or '--config [<path1>,<path2>,...]' in sys.argv (the
        brackets are optional), and builds a config from the specified paths by merging them into the default config in
        the specified order.

        :param configs: config's path or dictionary, or list of config paths or dictionaries to merge. Those will be
            merged to the default config before the config from the command line.
        :param fallback: config path or dictionary, or list of config paths or dictionaries to fall back to if no config
            was detected in the argv
        :param pattern: pattern to look for in sys.argv
        :param default_config_path: default config's path or dictionary
        :param overwriting_regime: can be "auto-save" (default, when a param is overwritten it is merged instead and the
            config is saved automatically if it had been saved previously), "locked" (params can't be overwritten except
            using merge explicitly) or "unsafe" (params can be freely overwritten but reproducibility
            is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to merge the command line parameters
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        :param kwargs: additional parameters to pass to Configuration
        :raises TypeError: if --config is not found and no fallback
        :return: instance of Configuration object containing the desired config
        """
        configs_from_argv: List[ConfigDeclarator] = get_config_from_argv(pattern=pattern, fallback=fallback)

        return cls.load_config(*configs, *configs_from_argv, default_config_path=default_config_path,
                               overwriting_regime=overwriting_regime,
                               do_not_merge_command_line=do_not_merge_command_line,
                               do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process,
                               from_argv=pattern if pattern in sys.argv else "", **kwargs)

    def create_variations(self) -> List['Configuration']:
        """
        Creates a list of configs that are derived from the current config using the internally tracked variations and
        grids registered via the corresponding functions (register_as_config_variations and register_as_grid).

        :raises TypeError: if grid dimension is empty or not registered
        :return: the list of configs corresponding to the tracked variations
        """
        variations_names_to_use = [i[0] for i in self._configuration_variations]
        variations_names_to_use_changing = [i[0] for i in self._configuration_variations]
        variations_to_use = [i[1] for i in self._configuration_variations]
        variations_to_use_changing = [i[1] for i in self._configuration_variations]
        variations = []
        variations_names = []

        def _add_new_names(new_names, dim, var_ind: int):
            for vari_name in self._configuration_variations_names:
                if vari_name[0] == dim:
                    new_names.append(names_to_add[var_ind] + "+" + vari_name[0] + "_" + vari_name[1][index])
            return new_names

        # Adding grids
        for grid in self._grids:
            grid_to_add = []
            names_to_add = []
            for dimension in grid:
                if dimension not in variations_names_to_use:
                    raise TypeError(f"Grid element '{dimension}' is an empty list or "
                                    "not a registered variation configuration.")
                if dimension in variations_names_to_use_changing:
                    index = variations_names_to_use_changing.index(dimension)
                    variations_names_to_use_changing.pop(index)
                    variations_to_use_changing.pop(index)
                if not grid_to_add:
                    grid_to_add = [[i] for i in variations_to_use[variations_names_to_use.index(dimension)]]
                    for var_name in self._configuration_variations_names:
                        if var_name[0] == dimension:
                            names_to_add = [var_name[0] + "_" + i for i in var_name[1]]
                else:
                    new_grid_to_add = []
                    new_names_to_add = []
                    for var_index, current_variation in enumerate(grid_to_add):
                        for index in range(len(variations_to_use[variations_names_to_use.index(dimension)])):
                            new_grid_to_add.append(
                                current_variation
                                + [variations_to_use[variations_names_to_use.index(dimension)][index]])
                            new_names_to_add = _add_new_names(new_names_to_add, dimension, var_index)
                    grid_to_add = [list(var) for var in new_grid_to_add]
                    names_to_add = list(new_names_to_add)
            variations = variations + grid_to_add
            variations_names = variations_names + names_to_add

        # Adding remaining non-grid variations
        for var_idx, remaining_variations in enumerate(variations_to_use_changing):
            for variation_index, variation in enumerate(remaining_variations):
                variations.append([variation])
                name = variations_names_to_use_changing[var_idx]
                for var_name in self._configuration_variations_names:
                    if var_name[0] == name:
                        variations_names.append(name + "_" + var_name[1][variation_index])

        # Creating configs
        variation_configs = []
        for variation_index, variation in enumerate(variations):
            variation_configs.append(
                self.__class__.load_config(self.config_metadata["config_hierarchy"][1:] + variation,
                                           default_config_path=self.config_metadata["config_hierarchy"][0],
                                           overwriting_regime=self.config_metadata["overwriting_regime"],
                                           do_not_merge_command_line=True, variation=variations_names[variation_index],
                                           verbose=False))
            variation_configs[-1].set_variation_name(variations_names[variation_index], deep=True)
        if not variation_configs:
            variation_configs = [self]
        elif self._verbose:
            YAECS_LOGGER.info(f"Created {len(variation_configs)} variation{'s' if len(variation_configs) > 1 else ''} "
                              f"from registered variation parameters.")
        return variation_configs

    @staticmethod
    def get_default_config_path() -> str:
        """
        Returns the path to the default config of the project. This function must be implemented at project-level.

        :return: string corresponding to the path to the default config of the project
        """
        raise NotImplementedError

    def parameters_pre_processing(self) -> Dict[str, Callable]:
        """
        Returns a dictionary where the keys are parameter names (supporting the '*' character as a replacement for any
        number of characters) and the items are functions. The pre-processing functions need to take a single argument
        and return the new value of the parameter after pre-processing. During pre-processing, all parameters
        corresponding to the parameter name are passed to the corresponding function and their value is replaced by the
        value returned by the corresponding function. This function must be implemented at project-level.

        Using this is advised when an action needs to  happen during the ongoing creation or merging operation, such as
        the register_as_additional_config_file processing function, or when a parameter is stored on disk using a format
        that you would prefer to not be used within the config, as the pre-processing function will be performed before
        the parameter even enters the Configuration object.

        Conversions to non-YAML-readable types are forbidden using pre-processing. Please use post-processing for those
        functions.

        :return: dictionary of the pre-processing functions
        """
        raise NotImplementedError

    def parameters_post_processing(self) -> Dict[str, Callable]:
        """
        Returns a dictionary where the keys are parameter names (supporting the '*' character as a replacement for any
        number of characters) and the values are functions. The post-processing functions need to take a single argument
        and return the new value of the parameter after post-processing. After any creation or merging operation,
        parameters which were modified by said operation get post-processed according to the specified functions. This
        function can be implemented at project-level.

        Using this is advised for type-changing processing functions or processing functions which have consequences
        beyond the value of that parameter (for example if they rely on another parameter being initialised, or if they
        would create directories). A notable exception to this rule of thumb is the register_as_additional_config_file
        processing function, which should almost always be called as a pre-processing function. Since the value of the
        parameter should no longer change after post-processing, you can also use post-processing to check if the value
        of the parameter has the correct type or is in the correct range.

        :return: dictionary of the post-processing functions
        """
        raise NotImplementedError

    def set_variation_name(self, name: str, deep: bool = False) -> None:
        """
        Sets the variation index of the config. This function is not intended to be used by the user.

        :param name: index to set the variation index with
        :param deep: whether to also recursively set the variation name of all sub-configs
        """
        object.__setattr__(self, "_variation_name", name)
        if deep:
            for subconfig in self.get_all_sub_configs():
                subconfig.set_variation_name(name, deep=True)

    @classmethod
    def _get_instance(cls, name: str = "main", overwriting_regime: str = "auto-save",
                      config_path_or_dictionary: Optional[ConfigDeclarator] = None,
                      nesting_hierarchy: Optional[List[str]] = None, state: Optional[List[str]] = None,
                      main_config: Optional['Configuration'] = None, variation: Optional[str] = None,
                      do_not_pre_process: bool = False, do_not_post_process: bool = False, verbose: bool = True,
                      **kwargs) -> 'Configuration':
        """ Used by parent classes to spawn new instances of the superclass. """
        return cls(name=name, overwriting_regime=overwriting_regime,
                   config_path_or_dictionary=config_path_or_dictionary, nesting_hierarchy=nesting_hierarchy,
                   state=state, main_config=main_config, variation=variation, do_not_pre_process=do_not_pre_process,
                   do_not_post_process=do_not_post_process, verbose=verbose, **kwargs)
