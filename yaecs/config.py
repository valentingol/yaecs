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

import copy
import os
import sys
import time
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import (Any, Callable, Dict, ItemsView, KeysView, List, Optional,
                    Tuple, Type, Union, ValuesView)

import yaml

from .config_utils import (adapt_to_type, are_same_sub_configs,
                           compare_string_pattern, dict_apply, escape_symbols,
                           get_param_as_parsable_string, is_type_valid,
                           recursive_set_attribute, update_state)

ConfigDeclarator = Union[str, dict]
VariationDeclarator = Union[List[ConfigDeclarator], Dict[str,
                                                         ConfigDeclarator]]


class Configuration:
    """Base class for YAECS configurations."""

    def __init__(self, name: str = "main",
                 overwriting_regime: str = "auto-save",
                 config_path_or_dictionary: Optional[ConfigDeclarator] = None,
                 nesting_hierarchy: Optional[List[str]] = None,
                 state: Optional[List[str]] = None,
                 main_config: Optional["Configuration"] = None,
                 from_argv: bool = False, do_not_pre_process: bool = False,
                 ):
        """
        Should never be called directly by the user. Please use one of
        the constructors instead (load_config, build_from_configs,
        build_from_argv), or the utils.make_config convenience function.
        :param name: name for the config or sub-config
        :param overwriting_regime: can be "auto-save" (default, when
        a param is overwritten it is merged instead and the config
        is saved automatically if it had been saved previously),
        "locked" (params can't be overwritten except using merge
        explicitly) or "unsafe" (params can be freely overwritten but
        reproducibility is not guaranteed).
        :param config_path_or_dictionary: path or dictionary to create
        the config from
        :param nesting_hierarchy: list containing the names of all the
        configs in the sub-config chain leading to this
        config
        :param state: processing state used for state tracking and
        debugging
        :param main_config: main config corresponding to this
        sub-config, or None if this config is the main config
        :param from_argv: whether the config was created with configs
        passed from the command line arguments
        :param do_not_pre_process: if true, pre-processing is
        deactivated in this initialization
        :raises ValueError: if the overwriting regime is not valid
        :return: none
        """
        config_path_or_dictionary = (self.get_default_config_path()
                                     if config_path_or_dictionary is None else
                                     config_path_or_dictionary)

        # PROTECTED ATTRIBUTES
        object.__setattr__(self, "_operating_creation_or_merging", True)
        self._state = [] if state is None else state
        self._main_config = self if main_config is None else main_config
        self._methods = [
            name for name in dir(self) if name not in
            ["_operating_creation_or_merging", "_state", "_main_config"]
        ]
        self._name = name
        self._pre_process_master_switch = not do_not_pre_process
        self._reference_folder = None
        self._was_last_saved_as = None
        self._modified_buffer = []
        self._pre_postprocessing_values = {}
        self._variation_name = (None if main_config is None else
                                main_config.get_variation_name())
        self._nesting_hierarchy = ([] if nesting_hierarchy is None else
                                   list(nesting_hierarchy))
        self._from_argv = from_argv
        self._configuration_variations = []
        self._configuration_variations_names = []
        self._grids = []
        self._sub_configs_list = []
        self._former_saving_time = None
        self._protected_attributes = list(
            self.__dict__) + ["_protected_attributes"]

        # SPECIAL ATTRIBUTES
        self.config_metadata = {
            "saving_time":
            time.time(),
            "config_hierarchy": [],
            "overwriting_regime":
            overwriting_regime if main_config is None else
            main_config.config_metadata["overwriting_regime"],
        }
        if self.config_metadata["overwriting_regime"] not in [
                "unsafe", "auto-save", "locked",
        ]:
            raise ValueError(
                "'overwriting_regime' needs to be either 'auto-save', "
                "'locked' or 'unsafe'.")

        # INITIALISATION
        self._state.append(f"setup;{self._name}")
        self._init_from_config(config_path_or_dictionary)
        self.config_metadata["config_hierarchy"] = (
            [] if not self._nesting_hierarchy else list(
                main_config.get(
                    '.'.join(self._nesting_hierarchy[:-1]),
                    main_config).config_metadata['config_hierarchy']))
        self.config_metadata["config_hierarchy"] += [config_path_or_dictionary]
        if not self._nesting_hierarchy:
            self._check_for_unlinked_sub_configs()
        if main_config is None:
            self.set_pre_processing(True)
        self._state.pop(-1)
        self._operating_creation_or_merging = False

    def __repr__(self):
        return "<Configuration:" + self.get_name() + ">"

    def __eq__(self, other):
        if not isinstance(other, Configuration):
            return False
        for param in self._get_user_defined_attributes():
            try:
                if self[param] != other[param]:
                    return False
            except AttributeError:
                return False
        for param in other._get_user_defined_attributes():
            try:
                _ = self[param]
            except AttributeError:
                return False
        return True

    def __hash__(self):
        return hash(repr(self.get_dict(deep=True)))

    def __getitem__(self, item):
        if "." in item and "*" not in item:
            sub_config_name = ("___" + item.split(".")[0] if item.split(".")[0]
                               in self._methods else item.split(".")[0])
            sub_config = getattr(self, sub_config_name)
            if not isinstance(sub_config, Configuration):
                did_you_mean_message = self._did_you_mean(
                    sub_config_name, filter_type=self.__class__)
                raise TypeError(
                    f"As the parameter '{sub_config_name}' is not a sub-config"
                    f", it cannot be accessed.\n{did_you_mean_message}")
            return sub_config[item.split(".", 1)[1]]
        return getattr(self, "___" + item if item in self._methods else item)

    def __setattr__(self, key, value):
        if (self._operating_creation_or_merging
                or self._main_config.is_in_operation()
                or self.config_metadata["overwriting_regime"] == "unsafe"):
            object.__setattr__(self, key, value)
        elif self.config_metadata["overwriting_regime"] == "auto-save":
            self._manual_merge({key: value}, verbose=True, source='code')
        elif self.config_metadata["overwriting_regime"] == "locked":
            raise RuntimeError("Overwriting params in locked configs "
                               "is not allowed.")
        else:
            raise ValueError(
                f"No behaviour determined for value '"
                f"{self.config_metadata['overwriting_regime']}' of "
                f"parameter 'overwriting_regime'.")

    def __getattribute__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError as exception:
            if not item.startswith("_"):
                raise AttributeError(
                    f"Unknown parameter of the configuration : '{item}'.\n"
                    f"{self._did_you_mean(item)}") from exception
            raise AttributeError from exception

    def __iter__(self):
        return iter(self._get_user_defined_attributes())

    @classmethod
    def load_config(cls, *configs: Union[List[ConfigDeclarator],
                                         ConfigDeclarator],
                    default_config_path: Optional[ConfigDeclarator] = None,
                    overwriting_regime: str = "auto-save",
                    do_not_merge_command_line: bool = False,
                    do_not_pre_process: bool = False, verbose: bool = True,
                    **kwargs,
                    ):
        """
        First creates a config using the default config, then merges
        config_path into it. If config_path is a list, successively
        merges all configs in the list instead from index 0 to the last.
        :param configs: config's path or dictionary, or list of default
        config's paths or dictionaries to merge
        :param default_config_path: default config's path or dictionary
        :param overwriting_regime: can be "auto-save" (default, when a
        param is overwritten it is merged instead and the config is
        saved automatically if it had been saved previously), "locked"
        (params can't be overwritten except using merge explicitly) or
        "unsafe" (params can be freely overwritten but reproducibility
        is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to
        merge the command line parameters
        :param do_not_pre_process: if true, pre-processing is
        deactivated in this initialization
        :param verbose: controls the verbose in the config creation
        process
        :param kwargs: additional parameters to pass to Configuration
        :return: instance of Configuration object containing the desired
        config
        """
        default_config_path = (cls.get_default_config_path()
                               if default_config_path is None else
                               default_config_path)
        if verbose:
            print("Building config from default : ", default_config_path)
        config = cls(config_path_or_dictionary=default_config_path,
                     overwriting_regime=overwriting_regime,
                     do_not_pre_process=do_not_pre_process, **kwargs,
                     )
        if configs and isinstance(configs[0], list):
            configs = configs[0]
        for path in configs:
            config._merge(path, do_not_pre_process=do_not_pre_process,
                          verbose=verbose)
        if not do_not_merge_command_line:
            to_merge = config._get_command_line_dict()
            if to_merge:
                config._merge(to_merge, do_not_pre_process=do_not_pre_process,
                              verbose=verbose)
        config._post_process_modified_parameters()
        return config

    @classmethod
    def build_from_configs(cls, *configs: Union[List[ConfigDeclarator],
                                                ConfigDeclarator],
                           overwriting_regime: str = "auto-save",
                           do_not_merge_command_line: bool = False,
                           do_not_pre_process: bool = False,
                           verbose: bool = True, **kwargs,
                           ):
        """
        First creates a config using the first config provided (or the
        first config in the provided list), then merges the subsequent
        configs into it from index 1 to the last.
        :param configs: config's path or dictionary, or list of default
        config's paths or dictionaries to merge
        :param overwriting_regime: can be "auto-save" (default, when a
        param is overwritten it is merged instead and the config is
        saved automatically if it had been saved previously), "locked"
        (params can't be overwritten except using merge explicitly) or
        "unsafe" (params can be freely overwritten but reproducibility
        is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to merge
        the command line parameters
        :param do_not_pre_process: if true, pre-processing is
        deactivated in this initialization
        :param verbose: controls the verbose in the config creation
        process
        :param kwargs: additional parameters to pass to Configuration
        :raises TypeError: if configs is invalid
        :return: instance of Configuration object containing the desired
        config
        """
        if not configs or (isinstance(configs[0], list) and not configs[0]):
            raise TypeError("build_from_configs needs to be called with "
                            "at least one config.")
        if isinstance(configs[0], list) and len(configs) == 1:
            configs = configs[0]
        elif isinstance(configs[0], list):
            raise TypeError(
                f"Invalid argument : '{configs}'\n"
                "please use build_from_configs([cfg1, cfg2, ...]) or "
                "build_from_configs(cfg1, cfg2, ...)")
        return cls.load_config(
            list(configs[1:]), default_config_path=configs[0],
            overwriting_regime=overwriting_regime,
            do_not_merge_command_line=do_not_merge_command_line,
            do_not_pre_process=do_not_pre_process, verbose=verbose, **kwargs,
        )

    @classmethod
    def build_from_argv(cls, fallback: Optional[str] = None,
                        default_config_path: Optional[ConfigDeclarator] = None,
                        overwriting_regime: str = "auto-save",
                        do_not_merge_command_line: bool = False,
                        do_not_pre_process: bool = False, verbose: bool = True,
                        **kwargs,
                        ):
        """
        Assumes a pattern of the form '--config <path_to_config>' or
        '--config [<path1>,<path2>,...]' in sys.argv (the brackets are
        optional), and builds a config from the specified paths by
        merging them into the default config in the specified order.
        :param fallback: config path or dictionary, or list of config
        paths or dictionaries to fall back to if no config was detected
        in the argv
        :param default_config_path: default config's path or dictionary
        :param overwriting_regime: can be "auto-save" (default, when a
        param is overwritten it is merged instead and the config is
        saved automatically if it had been saved previously), "locked"
        (params can't be overwritten except using merge explicitly) or
        "unsafe" (params can be freely overwritten but reproducibility
        is not guaranteed).
        :param do_not_merge_command_line: if True, does not try to merge
        the command line parameters
        :param do_not_pre_process: if true, pre-processing is
        deactivated in this initialization
        :param verbose: controls the verbose in the config creation
        process
        :param kwargs: additional parameters to pass to Configuration
        :raises TypeError: if --config is not found and no fallback
        :return: instance of Configuration object containing the desired
        config
        """
        if "--config" not in sys.argv and fallback is None:
            raise TypeError("The pattern '--config' was not detected "
                            "in sys.argv.")
        if "--config" in sys.argv:
            fallback = [
                cfg.strip(" ") for cfg in sys.argv[sys.argv.index("--config")
                                                   + 1].strip("[]").split(",")
            ]

        return cls.load_config(
            fallback, default_config_path=default_config_path,
            overwriting_regime=overwriting_regime,
            do_not_merge_command_line=do_not_merge_command_line,
            do_not_pre_process=do_not_pre_process, verbose=verbose,
            from_argv=True, **kwargs,
        )

    def compare(self, other: "Configuration",
                reduce: bool = False) -> List[Tuple[str, Optional[Any]]]:
        """
        Returns a list of tuples, where each tuple represents a
        parameter that is different between the "self" configuration and
        the "other" configuration. Tuples are written in the form :
        (parameter_name, parameter_value_in_other). If parameter_name
        does not exist in other, (parameter_name, None) is given
        instead.
        :param other: config to compare self with
        :param reduce: tries to reduce the size of the output text as
        much as possible
        :return: difference list
        """

        def _investigate_parameter(parameter_name, object_to_check):
            if reduce:
                name_path = parameter_name.split(".")
                to_display = name_path.pop(-1)
                while (len([
                        param for param in object_to_check.get_parameter_names(
                            deep=True)
                        if compare_string_pattern(param, "*." + to_display)
                ]) != 1 and name_path):
                    to_display = name_path.pop(-1) + "." + to_display
            else:
                to_display = parameter_name
            return (self.get(parameter_name,
                             None), other.get(parameter_name,
                                              None), to_display,
                    )

        def _get_to_ret(value_self, value_other):
            """Get values to retain in comparison."""
            to_ret = {}
            for key in value_self:
                if key not in value_other:
                    to_ret[key] = None
                elif value_self[key] != value_other[key]:
                    to_ret[key] = value_other[key]
            for key in value_in_other:
                if key not in value_self:
                    to_ret[key] = value_other[key]
            return to_ret

        differences = []
        for name in self.get_parameter_names():
            (value_in_self, value_in_other,
             displayed_name) = _investigate_parameter(name, self)
            if value_in_other != value_in_self:
                if not reduce:
                    differences.append((displayed_name, value_in_other))
                else:
                    if not isinstance(value_in_self, Configuration):
                        if (isinstance(value_in_self, dict)
                                and isinstance(value_in_other, dict)):
                            differences.append((displayed_name,
                                                _get_to_ret(value_in_self,
                                                            value_in_other)))
                        else:
                            differences.append(
                                (displayed_name, value_in_other))
        for name in other.get_parameter_names():
            _, value_in_other, displayed_name = _investigate_parameter(
                name, other)
            if (name not in self.get_parameter_names()
                    and value_in_other is not None):
                if reduce:
                    if not isinstance(value_in_other, Configuration):
                        differences.append((displayed_name, value_in_other))
                else:
                    differences.append((displayed_name, value_in_other))
        return differences

    def copy(self) -> "Configuration":
        """
        Returns a safe, independent copy of the config
        :return: instance of Configuration that is a deep copy of the config
        """
        return deepcopy(self)

    def create_variations(self) -> List["Configuration"]:
        """
        Creates a list of configs that are derived from the current
        config using the internally tracked variations and grids
        registered via the corresponding functions
        (register_as_config_variations and register_as_grid).
        :raises TypeError: if grid dimension is empty or not registered
        :return: the list of configs corresponding to the tracked
        variations
        """
        variations_names_to_use = [
            i[0] for i in self._configuration_variations
        ]
        variations_names_to_use_changing = [
            i[0] for i in self._configuration_variations
        ]
        variations_to_use = [i[1] for i in self._configuration_variations]
        variations_to_use_changing = [
            i[1] for i in self._configuration_variations
        ]
        variations = []
        variations_names = []

        def _add_new_names(new_names, dim, var_ind):
            for var_name in self._configuration_variations_names:
                if var_name[0] == dim:
                    new_names.append(names_to_add[var_ind] + "*"
                                     + var_name[0] + "_"
                                     + var_name[1][index])
            return new_names

        # Adding grids
        for grid in self._grids:
            grid_to_add = []
            names_to_add = []
            for dimension in grid:
                if dimension not in variations_names_to_use:
                    raise TypeError(
                        f"Grid element '{dimension}' is an empty list or "
                        "not a registered variation configuration.")
                if dimension in variations_names_to_use_changing:
                    index = variations_names_to_use_changing.index(dimension)
                    variations_names_to_use_changing.pop(index)
                    variations_to_use_changing.pop(index)
                if not grid_to_add:
                    grid_to_add = [[i] for i in variations_to_use[
                        variations_names_to_use.index(dimension)]]
                    for var_name in self._configuration_variations_names:
                        if var_name[0] == dimension:
                            names_to_add = [
                                var_name[0] + "_" + i for i in var_name[1]
                            ]
                else:
                    new_grid_to_add = []
                    new_names_to_add = []
                    for var_index, current_variation in enumerate(grid_to_add):
                        for index in range(
                                len(variations_to_use[variations_names_to_use
                                                      .index(dimension)])):
                            new_grid_to_add.append(current_variation + [
                                variations_to_use[variations_names_to_use
                                                  .index(dimension)][index]
                            ])
                            new_names_to_add = _add_new_names(
                                new_names_to_add, dimension, var_index)
                    grid_to_add = [list(var) for var in new_grid_to_add]
                    names_to_add = list(new_names_to_add)
            variations = variations + grid_to_add
            variations_names = variations_names + names_to_add

        # Adding remaining non-grid variations
        for var_idx, remaining_variations in enumerate(
                variations_to_use_changing):
            for variation_index, variation in enumerate(remaining_variations):
                variations.append([variation])
                name = variations_names_to_use_changing[var_idx]
                for var_name in self._configuration_variations_names:
                    if var_name[0] == name:
                        variations_names.append(name + "_"
                                                + var_name[1][variation_index])

        # Creating configs
        variation_configs = []
        for variation_index, variation in enumerate(variations):
            variation_configs.append(
                self.__class__.load_config(
                    self.config_metadata["config_hierarchy"][1:] + variation,
                    default_config_path=self
                    .config_metadata["config_hierarchy"][0],
                    overwriting_regime=self
                    .config_metadata["overwriting_regime"],
                    do_not_merge_command_line=True, verbose=False,
                ))
            variation_configs[-1].set_variation_name(
                variations_names[variation_index], deep=True)
        return variation_configs

    def details(self, show_only: Optional[Union[str, List[str]]] = None,
                expand_only: Optional[Union[str, List[str]]] = None,
                no_show: Optional[Union[str, List[str]]] = None,
                no_expand: Optional[Union[str, List[str]]] = None,
                ) -> str:
        """
        Creates and returns a string describing all the parameters
        in the config and its sub-configs.
        :param show_only: if not None, list of names referring
        to params. Only params in the list are displayed in the details.
        :param expand_only: if not None, list of names referring
        to sub-configs. Only sub-configs in the list are unrolled in
        the details.
        :param no_show: if not None, list of names referring to params.
        Params in the list are not displayed in the details.
        :param no_expand: if not None, list of names referring
        tp sub-configs. Sub-configs in the list are not unrolled in
        the details.
        :return: string containing the details
        """
        constraints = {
            "show_only": show_only,
            "expand_only": expand_only,
            "no_show": no_show,
            "no_expand": no_expand,
        }
        constraints = dict_apply(constraints, self.match_params)
        string_to_return = ("\n" + "\t" * len(self._nesting_hierarchy)
                            + self.get_name().upper() + " CONFIG :\n")
        if not self._nesting_hierarchy:
            string_to_return += "Configuration hierarchy :\n"
            for hierarchy_level in self.config_metadata["config_hierarchy"]:
                string_to_return += f"> {hierarchy_level}\n"
            string_to_return += "\n"
        to_print = [
            attribute for attribute in self._get_user_defined_attributes()
            if ((constraints["show_only"] is None
                 or attribute in constraints["show_only"]) and (
                     constraints["no_show"] is None
                     or attribute not in constraints["no_show"]))
        ]

        def _for_sub_config(names, attribute):
            new = (None if names is None else [
                ".".join(c.split(".")[1:])
                for c in names
                if (c.split(".")[0] == attribute and len(c.split(".")) > 1)
            ])
            return None if not new else new

        for attribute in to_print:
            string_to_return += ("\t" * len(self._nesting_hierarchy) + " - "
                                 + attribute + " : ")
            if isinstance(self[attribute], Configuration):
                if ((constraints["no_expand"] is None
                        or attribute not in constraints["no_expand"])
                        and (constraints["expand_only"] is None
                             or attribute in [
                                 cstr.split(".")[0]
                                 for cstr in constraints["expand_only"]])):
                    _for_sub_config_attr = partial(_for_sub_config,
                                                   attribute=attribute)
                    string_to_return += (self[attribute].details(
                        **(dict_apply(constraints, _for_sub_config_attr)))
                                         + "\n")
                else:
                    string_to_return += self[attribute].get_name().upper()
                    string_to_return += "\n"
            else:
                string_to_return += str(self[attribute]) + "\n"
        return string_to_return

    def get(self, parameter_name: str, default_value: Any) -> Any:
        """
        Behaves similarly to dict.get(parameter_name, default_value)
        :param parameter_name: parameter to query
        :param default_value: value to return if the parameter does not exist
        :return: queried value
        """
        try:
            return self[parameter_name]
        except (AttributeError, TypeError):
            return default_value

    def get_all_linked_sub_configs(self) -> List["Configuration"]:
        """
        Returns the list of all sub-configs that are directly linked
        to the root config by a chain of other sub-configs.
        For this to be the case, all of those sub-configs need to be
        contained directly in a parameter of another sub-config.
        For example, a sub-config stored in a list that is a parameter
        of a sub-config is not linked.
        :return: list corresponding to the linked sub-configs
        """
        all_linked_configs = []
        for i in self._get_user_defined_attributes():
            object_to_scan = getattr(self,
                                     "___" + i if i in self._methods else i)
            if isinstance(object_to_scan, Configuration):
                all_linked_configs = (
                    all_linked_configs + [object_to_scan]
                    + object_to_scan.get_all_linked_sub_configs())
        return all_linked_configs

    def get_all_sub_configs(self) -> List["Configuration"]:
        """
        Returns the list of all sub-configs, including sub-configs
        of other sub-configs
        :return: list corresponding to the sub-configs
        """
        all_configs = list(self._sub_configs_list)
        for i in self._sub_configs_list:
            all_configs = all_configs + i.get_all_sub_configs()
        return all_configs

    def is_in_operation(self) -> bool:
        return self._operating_creation_or_merging

    def get_command_line_argument(
        self, deep: bool = True, do_return_string: bool = False,
        ignore_unknown_types: bool = False,
    ) -> Union[List[str], str]:
        """
        Returns a list of command line parameters that can be used
        in the command line to re-create this exact config from
        the default. Can alternatively return the string itself with
        do_return_string=True.
        :param deep: whether to also take the sub-config parameters
        into account
        :param do_return_string: whether to return a string (True)
        or a list of strings (False, default)
        :param ignore_unknown_types: if False (default), types that
        cannot be parsed in YAML raise an error. Else, they are skipped
        when creating the list.
        :return: list or string containing the parameters
        """
        # pylint: disable=protected-access
        to_return = []
        for param in self.get_parameter_names(deep=deep):
            if not isinstance(self[param], Configuration):
                pair = get_param_as_parsable_string(
                    self[param] if ".".join(self.get_nesting_hierarchy()
                                            + [param])
                    not in self.get_main_config()._pre_postprocessing_values
                    else self.get_main_config()._pre_postprocessing_values[
                        ".".join(self.get_nesting_hierarchy() + [param])],
                    ignore_unknown_types=ignore_unknown_types,
                )
                if pair.count(" !"):
                    pair_as_list = pair.split(" !")
                    param_value, param_force = (" !".join(pair_as_list[:-1]),
                                                pair_as_list[-1],
                                                )
                    to_return.append(
                        escape_symbols(
                            f"--{param} '{param_value}' !{param_force}",
                            ["{", "}", "*"]))
                else:
                    to_return.append(
                        escape_symbols(f"--{param} {pair}", ["{", "}", "*"]))

        return " ".join(to_return) if do_return_string else to_return

    @staticmethod
    def get_default_config_path() -> str:
        """
        Returns the path to the default config of the project.
        This function must be implemented at project-level.
        :return: string corresponding to the path to the default config
        of the project
        """
        raise NotImplementedError

    def get_dict(self, deep: bool = True) -> dict:
        """
        Returns a dictionary corresponding to the config.
        :param deep: whether to recursively turn sub-configs into dicts
        or keep them as sub-configs
        :return: dictionary corresponding to the config
        """
        return {
            key:
            (self[key] if not deep or not isinstance(self[key], Configuration)
             else self[key].get_dict())
            for key in self._get_user_defined_attributes()
        }

    def get_main_config(self) -> "Configuration":
        """
        Getter for the main config corresponding to this config
        or sub-config. Using this is often hacky.
        :return: the main config
        """
        return self._main_config

    def get_name(self) -> str:
        """
        Returns the name of the config. It is composed of a specified
        part (or 'main' when unspecified) and an indicator of its index
        in the list of variations of its parent if it is a variation of
        a config. This indicator is prefixed by '_VARIATION_'.
        :return: string corresponding to the name
        """
        variation_suffix = ("_VARIATION_" + self._variation_name
                            if self._variation_name is not None else "")
        return self._name + variation_suffix

    def get_nesting_hierarchy(self) -> List[str]:
        """
        Returns the nesting hierarchy of the config
        :return: list corresponding to the nesting hierarchy
        """
        return self._nesting_hierarchy

    def get_parameter_names(self, deep: bool = True) -> List[str]:
        complete_list = self._get_user_defined_attributes()
        if deep:
            order = len(self.get_nesting_hierarchy())
            for subconfig in self.get_all_linked_sub_configs():
                complete_list += [
                    ".".join(subconfig.get_nesting_hierarchy()[order:]
                             + [param])
                    for param in subconfig.get_parameter_names(deep=False)
                ]
        return complete_list

    def get_variation_name(self) -> str:
        """
        Returns the variation name of the config
        :return: variation name
        """
        return self._variation_name

    def items(self, deep: bool = False) -> ItemsView:
        """
        Behaves as dict.items(). If deep is False, sub-configs remain
        sub-configs in the items. Otherwise, they are converted to dict.
        :param deep: how to return sub-configs that would appear among
        the items. If False, do not convert them, else recursively
        convert them to dict
        :return: the items of the config as in dict.items()
        """
        return self.get_dict(deep).items()

    def keys(self) -> KeysView:
        """
        Behaves as dict.keys(), returning a _dict_keys instance
        containing the names of the params of the config.
        :return: the keys if the config as in dict.keys()
        """
        return self.get_dict(deep=False).keys()

    def match_params(
            self,
            *patterns: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
        """
        For a string, a list of strings or several strings, returns
        all params matching at least one of the input strings.
        :param patterns: string, a list of strings or several strings
        :return: all params matching at least one of the input string
        """
        patterns = (patterns[0] if len(patterns) == 1
                    and isinstance(patterns[0], list) else patterns)
        if patterns is None or (len(patterns) == 1 and patterns[0] is None):
            return None
        new_names = [n for n in patterns if "*" not in n and n in self]
        for name in [n for n in patterns if "*" in n]:
            new_names = new_names + [
                p for p in self.get_parameter_names(deep=True)
                if compare_string_pattern(p, name)
            ]
        return new_names

    def merge(self, config_path_or_dictionary: ConfigDeclarator,
              do_not_pre_process: bool = False, verbose: bool = False,
              ) -> None:
        """
        Merges provided config path of dictionary into the current
        config.
        :param config_path_or_dictionary: path or dictionary for the
        config to merge
        :param do_not_pre_process: if true, pre-processing
        is deactivated in this initialization
        :param verbose: controls the verbose in the config creation
        and merging process
        """
        self._manual_merge(config_path_or_dictionary=config_path_or_dictionary,
                           do_not_pre_process=do_not_pre_process,
                           verbose=verbose)

    def merge_from_command_line(self, do_not_pre_process: bool = False,
                                string_to_merge: Optional[str] = None) -> None:
        """
        Deprecated function formerly used to manually merge the command
        line arguments into the config. This is now done automatically
        and thus should no longer be done manually.
        :param do_not_pre_process: if true, pre-processing
        is deactivated in this initialization
        :param string_to_merge: if specified, merges this string instead
        of the sys.argv string
        """
        print("WARNING: merge_from_command_line is now deprecated and "
              "will automatically start after using any constructor.\n"
              "You can remove the 'config.merge_from_command_line()' "
              "line from your code now :) it's redundant.")
        to_merge = self._get_command_line_dict(string_to_merge)
        if to_merge:
            self._manual_merge(to_merge, do_not_pre_process=do_not_pre_process)

    def parameters_pre_processing(self) -> Dict[str, Callable]:
        """
        Returns a dictionary where the keys are parameter names
        (supporting the '*' character as a replacement for any number
        of characters) and the items are functions. The pre-processing
        functions need to take a single argument and return the new
        value of the parameter after pre-processing.
        During pre-processing, all parameters corresponding to
        the parameter name are passed to the corresponding function
        and their value is replaced by the value returned by
        the corresponding function. This function must be implemented
        at project-level.

        Using this is advised when an action needs to  happen during
        the ongoing creation or merging operation, such as
        the register_as_additional_config_file processing function,
        or when a parameter is stored on disk using a format that you
        would prefer to not be used within the config, as
        the pre-processing function will be performed before
        the parameter even enters the Configuration object.

        Conversions to non-YAML-readable types are forbidden using
        pre-processing. Please use post-processing for those functions.

        :return: dictionary of the pre-processing functions
        """
        raise NotImplementedError

    def parameters_post_processing(self) -> Dict[str, Callable]:
        """

        Returns a dictionary where the keys are parameter names
        (supporting the '*' character as a replacement for any number
        of characters) and the values are functions. The post-processing
        functions need to take a single argument and return the new
        value of the parameter after post-processing. After any creation
        or merging operation, parameters which were modified by said
        operation get post-processed according to the specified
        functions. This function can be implemented at project-level.

        Using this is advised for type-changing processing functions or
        processing functions which have consequences beyond the value
        of that parameter (for example if they rely on another parameter
        being initialized, or if they would create directories).
        A notable exception to this rule of thumb is
        the register_as_additional_config_file processing function,
        which should almost always be called as a pre-processing
        function. Since the value of the parameter should no longer
        change after post-processing, you can also use post-processing
        to check if the value of the parameter has the correct type or
        is in the correct range.

        :return: dictionary of the post-processing functions
        """
        return {}

    def set_variation_name(self, name: str, deep: bool = False) -> None:
        """
        Sets the variation index of the config. This function is not
        intended to be used by the user.
        :param name: index to set the variation index with
        :param deep: whether to also recursively set the variation name
        of all sub-configs
        """
        object.__setattr__(self, "_variation_name", name)
        if deep:
            for subconfig in self._sub_configs_list:
                subconfig.set_variation_name(name, deep=True)

    def register_as_additional_config_file(
            self, path: Union[str, List[str]]) -> Union[str, List[str]]:
        """
        Pre-processing function used to register the corresponding
        parameter as a path to another config file. The new config file
        will then also be used to build the config currently being
        built.
        :param path: config's path or list of paths
        :return: the same path as the input once the parameters from
        the new config have been added
        """
        if isinstance(path, list):
            for individual_path in path:
                self._init_from_config(individual_path)
        else:
            self._init_from_config(path)
        return path

    def register_as_config_variations(
        self, variation_to_register: Optional[VariationDeclarator]
    ) -> Optional[VariationDeclarator]:
        """
        Pre-processing function used to register the corresponding
        parameter as a variation for the current config.
        Please note that config variations need to be declared in
        the root config.
        :param variation_to_register: list of configs
        :return: the same list of configs once the configs have been
        added to the internal variation tracker
        :raises ValueError: if ';arg0=' if found multiple times in the
        state
        :raises RuntimeError: register_as_config_variations is called
        outside _pre_process_parameter
        :raises RuntimeError: variation name invalid in sub-config
        :raises TypeError: type of variation is not list or dict
        of configs
        """
        name = None
        for state in self._state[::-1]:
            if state.startswith("processing"):
                if state.count(";arg0=") > 1:
                    raise ValueError("How did you even manage to raise this ?")
                name = state.split(";arg0=")[-1]
                break
        if name is None:
            raise RuntimeError(
                "register_as_config_variations was called outside "
                "_pre_process_parameter.")

        def _is_single_var(single):
            return isinstance(single, (str, dict))

        def _add_to_variations(variations, names=None):
            if variations:
                for index, variation in enumerate(
                        self._configuration_variations):
                    if variation[0] == name:
                        self._configuration_variations.pop(index)
                        break
                self._configuration_variations.append((name, variations))
                if names is None:
                    self._configuration_variations_names.append(
                        (name, [str(i) for i in list(range(len(variations)))],
                         ))
                else:
                    self._configuration_variations_names.append((name, names))

        if self._nesting_hierarchy:
            raise RuntimeError(
                f"Variations declared in sub-configs are invalid ({name}).\n"
                "Please declare all your variations in the main config.")
        if (isinstance(variation_to_register, dict) and all(
                _is_single_var(potential_single)
                for potential_single in variation_to_register.values())):
            _add_to_variations(list(variation_to_register.values()),
                               names=list(variation_to_register.keys()),
                               )
        elif (isinstance(variation_to_register, list) and all(
                _is_single_var(potential_single)
                for potential_single in variation_to_register)):
            _add_to_variations(variation_to_register)
        elif variation_to_register is not None:
            raise TypeError(
                "Variations parsing failed : variations parameters must "
                "be a list of configs or a dict containing only configs. "
                f"Instead, got : {variation_to_register}")

        return variation_to_register

    @staticmethod
    def register_as_experiment_path(path: str) -> str:
        """
        Pre-processing function used to register the corresponding
        parameter as the folder used for the current experiment.
        This will automatically create the relevant folder structure
        and append an experiment index at the end of the folder name
        to avoid any overwriting. The path needs to be either None or
        an empty string (in which case the pre-processing does not
        happen), or an absolute path, or a path relative to the current
        working directory.
        :param path: None, '', absolute path or path relative to
        the current working directory
        :return: the actual created path with its appended index
        """
        if not path:
            return path
        folder, experiment = (os.path.dirname(path), os.path.basename(path))
        os.makedirs(folder, exist_ok=True)
        experiments = [
            i for i in os.listdir(folder) if i.startswith(experiment)
        ]
        experiment_id = max([int(i.split("_")[-1])
                             for i in experiments] + [-1]) + 1
        path = os.path.join(folder, f"{experiment}_{experiment_id}")
        os.makedirs(path, exist_ok=True)
        return path

    def register_as_grid(
            self,
            list_to_register: Optional[List[str]]) -> Optional[List[str]]:
        """
        Pre-processing function used to register the corresponding
        parameter as a grid for the current config. Grids are made of
        several parameters registered as variations. Instead of adding
        the variations in those parameters to the list of variations for
        this config, a grid will be created and all its components will
        be added instead.
        :param list_to_register: list of parameters composing the grid
        :raises TypeError: list_to_register is not recognized as
        a valid grid
        :return: the same list of parameters once the grid has been
        added to the internal grid tracker
        """
        if (isinstance(list_to_register, list)
                and all(isinstance(param, str) for param in list_to_register)):
            self._grids.append(list_to_register)
        elif list_to_register is not None:
            raise TypeError(
                "Grid parsing failed : unrecognized grid declaration : "
                f"{list_to_register}")
        return list_to_register

    def save(self, filename: str = None, save_header: bool = True,
             save_hierarchy: str = True) -> None:
        """
        Saves the current config at the provided location. The saving
        format allows for a perfect recovery of the config by using :
        config = Configuration.load_config(filename). If no filename is
        given, overwrites the last save.
        :param filename: path to the saving location of the config
        :param save_header: whether to save the config metadata as
        the fist parameter. This will tag the saved file as a saved
        config in the eye of the config system when it gets merged,
        which will deactivate pre-processing.
        :param save_hierarchy: whether to save config hierarchy as a
        '*_hierarchy.yaml' file
        :raises RuntimeError: no file name is provided and there is no
        previous save to overwrite
        """
        # pylint: disable=protected-access
        if filename is None:
            if self._was_last_saved_as is None:
                raise RuntimeError(
                    "No filename was provided, but the config was never "
                    "saved before so there is no previous save to overwrite.")
            filename = self._was_last_saved_as
        self.config_metadata["creation_time"] = time.time()
        file_path, file_extension = os.path.splitext(filename)
        file_extension = file_extension if file_extension else ".yaml"
        config_dump_path = file_path + file_extension
        to_dump = {
            a: (getattr(self, "___" + a if a in self._methods else a) if
                (".".join(self._nesting_hierarchy + [a])
                 not in self.get_main_config()._pre_postprocessing_values) else
                self.get_main_config()._pre_postprocessing_values[".".join(
                    self._nesting_hierarchy + [a])])
            if a != "config_metadata" else self._format_metadata()
            for a in (["config_metadata"] if save_header else [])
            + self._get_user_defined_attributes()
        }
        with open(config_dump_path, "w", encoding='utf-8') as fil:
            yaml.dump(to_dump, fil, Dumper=self._get_yaml_dumper(),
                      sort_keys=False)

        if save_hierarchy:
            hierarchy_dump_path = f"{file_path}_hierarchy{file_extension}"
            to_dump = {
                "config_hierarchy": self.config_metadata["config_hierarchy"]
            }
            with open(hierarchy_dump_path, "w", encoding='utf-8') as fil:
                yaml.dump(to_dump, fil, Dumper=self._get_yaml_dumper())

        object.__setattr__(self, "_was_last_saved_as", config_dump_path)
        print(f"Configuration saved in : {os.path.abspath(config_dump_path)}")

    def save_value_before_postprocessing(self, name: str, value: Any) -> None:
        """
        Function used for bookkeeping : it saves the value a parameter
        had before its post-processing.
        :param name: name of the parameter using the dot convention
        :param value: value of the parameter before post-processing
        """
        self._pre_postprocessing_values[name] = value

    def set_pre_processing(self, value: bool = True) -> None:
        """
        Sets the state of the master switch for pre-processing across
        the entire config object. Calling this for a sub-config will
        also affect the main config and all other sub-configs.
        :param value: value to set the pre-processing to
        """
        object.__setattr__(self._main_config, "_pre_process_master_switch",
                           value)

    def values(self, deep: bool = False) -> ValuesView:
        """
        Behaves as dict.values(). If deep is False, sub-configs remain
        sub-configs in the values. Otherwise, they are converted
        to dict.
        :param deep: how to return sub-configs that would appear among
        the values. If False, do not convert them, else
        recursively convert them to dict
        :return: the values of the config as in dict.values()
        """
        return self.get_dict(deep).values()

    # ||||| PRIVATE METHODS |||||

    def _check_for_unlinked_sub_configs(self) -> None:
        """Used to raise an error when unlinked sub-configs are declared."""
        all_configs = self.get_all_sub_configs()
        linked_configs = self.get_all_linked_sub_configs()
        for i in all_configs:
            found_correspondence = False
            for j in linked_configs:
                if are_same_sub_configs(i, j):
                    found_correspondence = True
                    break
            if not found_correspondence:
                raise RuntimeError(
                    f"Sub-config '{i.get_name()}' is unlinked. Unlinked "
                    "sub-configs are not allowed.")

    def _did_you_mean(self, name: str, filter_type: Optional[type] = None,
                      suffix: str = "") -> str:
        """Used to propose suggestions when the user tries to access
        a parameter which does not exist."""
        params = {}
        name = f"*{name}*"
        for parameter in self.get_parameter_names(deep=True):
            if filter_type is None or isinstance(self[parameter], filter_type):
                for index in range(len(name)):
                    if compare_string_pattern(
                            parameter, name[:index] + "*" + name[index + 1:]):
                        if parameter in params:
                            params[parameter] += 1
                        else:
                            params[parameter] = 1
        if not params:
            return ""
        params_to_print = sorted(params.keys(), key=lambda x: params[x],
                                 reverse=True)
        to_return = "Perhaps what you actually meant is in this list :"
        for param in params_to_print:
            to_return += f"\n- {param}{suffix}"
        return to_return

    def _find_path(self, path: str) -> str:
        """Used to find a config from its (potentially relative) path,
        because it might be ambiguous relative to where it should be
        looked for. Probably very improvable."""
        # pylint: disable=protected-access
        # If the path is absolute, use it...
        if os.path.isabs(path):
            if os.path.exists(path):
                self._reference_folder = Path(path).parents[0]
                return path

        # ... if not, search relatively to some reference folders.
        else:

            # First check relatively to parent configs' directories...
            for config in reversed(self.config_metadata["config_hierarchy"]):
                if isinstance(config, str):
                    relative_path = os.path.join(Path(config).parents[0], path)
                    if os.path.exists(relative_path):
                        return os.path.abspath(relative_path)

            # ... then also check the current reference folder since
            # the config hierarchy is not always up-to-date...
            if self._reference_folder is not None:
                relative_path = os.path.join(self._reference_folder, path)
                if os.path.exists(relative_path):
                    return os.path.abspath(relative_path)
            if (self._main_config is not None
                    and self._main_config._reference_folder is not None):
                relative_path = os.path.join(
                    self._main_config._reference_folder, path)
                if os.path.exists(relative_path):
                    return os.path.abspath(relative_path)

            # ... and finally, check relatively to the current
            # working directory.
            if os.path.exists(path):
                path_to_return = os.path.abspath(path)
                self._reference_folder = Path(path_to_return).parents[0]
                return path_to_return
        raise FileNotFoundError(f"ERROR : path not found ({path}).")

    def _format_metadata(self) -> str:
        """Used to format the metadata for saving or printing."""
        return (
            f"Saving time : {time.ctime(self.config_metadata['saving_time'])} "
            f"({self.config_metadata['saving_time']}) ; "
            f"Regime : {self.config_metadata['overwriting_regime']}")

    def _get_yaml_loader(self) -> Type[yaml.FullLoader]:
        """Used to get a custom YAML loader capable of parsing config tags."""

        def generic_constructor(yaml_loader, tag, node):
            sub_config_name = tag[1:]
            self._nesting_hierarchy.append(sub_config_name)
            if yaml_loader.constructed_objects:
                dict_to_return = self.__class__(
                    name=sub_config_name,
                    config_path_or_dictionary=yaml_loader.construct_mapping(
                        node,
                        deep=True), nesting_hierarchy=self._nesting_hierarchy,
                    state=self._state, main_config=self._main_config,
                )
                if all(not are_same_sub_configs(i, dict_to_return)
                       for i in self._sub_configs_list):
                    self._sub_configs_list.append(dict_to_return)

            else:
                dict_to_return = {
                    sub_config_name:
                    self.__class__(
                        name=sub_config_name,
                        config_path_or_dictionary=yaml_loader
                        .construct_mapping(node, deep=True),
                        nesting_hierarchy=self._nesting_hierarchy,
                        state=self._state, main_config=self._main_config)
                }
                if all(not are_same_sub_configs(
                        i, dict_to_return[sub_config_name])
                       for i in self._sub_configs_list):
                    self._sub_configs_list.append(
                        dict_to_return[sub_config_name])
            self._nesting_hierarchy.pop(-1)
            return dict_to_return

        loader = yaml.FullLoader
        yaml.add_multi_constructor("", generic_constructor, Loader=loader)
        return loader

    def _get_yaml_dumper(self) -> Type[yaml.Dumper]:
        """Used to get a custom YAML dumper capable of writing config tags."""

        def config_representer(yaml_dumper, class_instance):
            # pylint: disable=protected-access
            return yaml_dumper.represent_mapping(
                "!" + class_instance.get_name(), {
                    a[3:] if a.startswith("___") else a:
                    self._format_metadata() if a == "config_metadata" else
                    (b if
                     ".".join(class_instance._nesting_hierarchy + [a]) not in
                      (self.get_main_config()._pre_postprocessing_values) else
                     (self.get_main_config()._pre_postprocessing_values[
                         ".".join(class_instance._nesting_hierarchy + [a])]))
                    for (a, b) in class_instance.__dict__.items()
                    if a not in self._protected_attributes
                    and not (class_instance.get_nesting_hierarchy()
                             and a in ["config_metadata"])
                },
            )

        dumper = yaml.Dumper
        dumper.add_representer(self.__class__, config_representer)
        return dumper

    def _get_user_defined_attributes(self) -> List[str]:
        """Frequently used to get a list of the names of all
        the parameters that were in the user's config."""
        return [
            i[3:] if i.startswith("___") else i
            for i in self.__dict__
            if i not in self._protected_attributes + ["config_metadata"]
        ]

    @update_state("_init_from_config;_name")
    def _init_from_config(self, config_path_or_dict: ConfigDeclarator,
                          verbose: bool = False) -> None:
        """Entrypoint for all methods trying to get any value from
        outside the config to inside the config. This includes creating
        new parameters when creating the config or merging existing
        parameters after the creation."""
        # pylint: disable=protected-access
        if config_path_or_dict is not None:
            if isinstance(config_path_or_dict, str):
                with open(self._find_path(config_path_or_dict),
                          encoding='utf-8') as yaml_file:
                    for dictionary_to_add in yaml.load_all(
                            yaml_file, Loader=self._get_yaml_loader()):
                        for item in dictionary_to_add.items():
                            self._process_item_to_merge_or_add(
                                item, verbose=verbose)
            else:
                for item in config_path_or_dict.items():
                    self._process_item_to_merge_or_add(item, verbose=verbose)

    def _manual_merge(self, config_path_or_dictionary: ConfigDeclarator,
                      do_not_pre_process: bool = False, source: str = 'config',
                      verbose: bool = False,
                      ) -> None:
        """This method is called whenever a merge is done by the user,
        and not by the config creation process. It simply
        calls _merge with some additional bookkeeping."""
        # pylint: disable=protected-access
        self._merge(config_path_or_dictionary=config_path_or_dictionary,
                    do_not_pre_process=do_not_pre_process, source=source,
                    verbose=verbose,
                    )
        self._post_process_modified_parameters()
        if (self.get_main_config().config_metadata["overwriting_regime"] ==
                "auto-save"):
            if self.get_main_config()._was_last_saved_as is not None:
                self.get_main_config().save()

    @update_state("merging;_name")
    def _merge(self, config_path_or_dictionary: ConfigDeclarator,
               do_not_pre_process: bool = False, source: str = 'config',
               verbose: bool = False,
               ) -> None:
        """Method handling all merging operations to call
        _init_from_config with the proper bookkeeping."""
        if self._main_config == self:
            object.__setattr__(self, "_operating_creation_or_merging", True)
            if verbose:
                to_print = str(config_path_or_dictionary)
                to_print = (to_print if len(to_print) < 200 else
                            f"{to_print[:97]} [...] {to_print[-97:]}")
                if source == 'code':
                    print(f"Merging from code : {to_print}")
                elif source == 'command_line':
                    print(f"Merging from command line : {to_print}")
                elif source == 'config':
                    print(f"Merging from new config : {to_print}")
                else:
                    raise ValueError(
                        "The source for a merge can only be 'config', "
                        f"'command_line' or 'code', not {source}.")
            self.set_pre_processing(not do_not_pre_process)
            self._init_from_config(config_path_or_dictionary)
            self.config_metadata["config_hierarchy"].append(
                config_path_or_dictionary)
            self._check_for_unlinked_sub_configs()
            self.set_pre_processing(True)
            self._operating_creation_or_merging = False
        else:
            dicts_to_merge = []
            if isinstance(config_path_or_dictionary, str):
                with open(self._find_path(config_path_or_dictionary),
                          encoding='utf-8') as yaml_file:
                    for dictionary_to_add in yaml.load_all(
                            yaml_file, Loader=self._get_yaml_loader()):
                        dicts_to_merge.append(dictionary_to_add)
                    yaml_file.close()
            else:
                dicts_to_merge.append(config_path_or_dictionary)
            for dictionary in dicts_to_merge:
                self._main_config._merge(  # pylint: disable=protected-access
                    {
                        ".".join(self._nesting_hierarchy + [a]): b
                        for a, b in dictionary.items()
                    },
                    do_not_pre_process=do_not_pre_process,
                    source=source,
                    verbose=verbose,
                )

    @update_state("working_on;_name")
    def _process_item_to_merge_or_add(self, item: Tuple[str, Any],
                                      verbose: bool = False) -> None:
        """Method called by _init_from_config to merge or add a given
        key, value pair."""
        key, value = item

        # Process metadata. If there is metadata, treat the rest of
        # the merge as "loading a saved file"... (which will deactivate
        # the parameter pre-processing for this merge)
        if key == "config_metadata":
            pattern = "Saving time : * (*) ; Regime : *"
            if (not isinstance(value, str)
                    or not compare_string_pattern(value, pattern)):
                raise RuntimeError("'config_metadata' is a special parameter. "
                                   "Please do not edit or set it.")

            regime = value.split(" : ")[-1]
            if regime == "unsafe":
                print("WARNING: YOU ARE LOADING AN UNSAFE CONFIG FILE. "
                      "Reproducibility with corresponding experiment is "
                      "not ensured")
            elif regime not in ["auto-save", "locked"]:
                raise ValueError(
                    "'overwriting_regime' is a special parameter. "
                    "It can only be set to 'auto-save'(default), "
                    "'locked' or 'unsafe'.")
            self.config_metadata["overwriting_regime"] = regime

            self._former_saving_time = float(
                value.split("(")[-1].split(")")[0])
            self.set_pre_processing(False)
            return

        # ...do not accept other protected attributes to be merged...
        if key in self._protected_attributes:
            raise RuntimeError(
                f"Error : '{key}' is a protected name and cannot "
                "be used as a parameter name.")

        # ... otherwise, process the data normally :

        # If we are merging a parameter into a previously defined config...
        if not any(state.startswith("setup") for state in self._state):
            self._merge_item(key, value, verbose=verbose)

        # ... or if we are creating a config for the first time and
        # are adding non-existing parameters to it
        else:
            self._add_item(key, value)

    def _merge_item(self, key: str, value: Any, verbose: bool = False) -> None:
        """Method called by _process_item_to_merge_or_add if the value
        should be merged and not added. This method
        ultimately performs all merges in the config."""
        # pylint: disable=protected-access
        if "*" in key:
            to_merge = {}
            for param in self.get_parameter_names(deep=True):
                if compare_string_pattern(param, key):
                    to_merge[param] = value
            if not to_merge:
                print(f"WARNING : parameter '{key}' will be ignored : "
                      "it does not match any existing parameter.")
            else:
                print(f"Pattern parameter '{key}' will be merged into "
                      "the following matched "
                      f"parameters : {list(to_merge.keys())}.")
            self._init_from_config(to_merge)
        elif "." in key:
            name, new_key = key.split(".", 1)
            try:
                sub_config = getattr(
                    self, "___" + name if name in self._methods else name)
            except AttributeError as exception:
                raise AttributeError(
                    f"ERROR : parameter '{key}' cannot be merged : "
                    f"it is not in the default '{self.get_name().upper()}' "
                    f"config.\n{self._did_you_mean(key)}") from exception

            if isinstance(sub_config, Configuration):
                sub_config._init_from_config({new_key: value})
            else:
                did_you_mean_message = self._did_you_mean(
                    key.split('.')[0], filter_type=self.__class__,
                    suffix=key.split('.', 1)[1])
                raise TypeError(
                    f"Failed to set parameter '{key}' : '{key.split('.')[0]}'"
                    f" is not a sub-config.\n{did_you_mean_message}")
        else:
            try:
                old_value = getattr(
                    self, "___" + key if key in self._methods else key)
            except AttributeError as exception:
                raise AttributeError(
                    f"ERROR : parameter '{key}' cannot be merged : "
                    f"it is not in the default '{self.get_name().upper()}' "
                    f"config.\n{self._did_you_mean(key)}") from exception
            if isinstance(old_value, Configuration):
                if isinstance(value, Configuration):
                    old_value._init_from_config(value.get_dict(deep=False))
                elif isinstance(value, dict):
                    old_value._init_from_config(value)
                else:
                    raise TypeError(
                        f"Trying to set sub-config '{old_value._name}'\n"
                        f"with non-config element '{value}'.\n"
                        "This replacement cannot be performed.")
            else:
                if verbose:
                    print(f"Setting '{key}' : \nold : '{old_value}' \n"
                          f"new : '{value}'.")
                object.__setattr__(
                    self, "___" + key if key in self._methods else key,
                    self._process_parameter(key, value, "pre"),
                )
                if key not in self._modified_buffer:
                    self._modified_buffer.append(key)

    def _add_item(self, key: str, value: Any) -> None:
        """Method called by _process_item_to_merge_or_add if the value
        should be added and not merged. This method ultimately performs
        all additions to the config."""
        # pylint: disable=protected-access
        if self._state[0].split(";")[0] == "setup" and "*" in key:
            raise ValueError(
                "The '*' character is not authorized in the default "
                f"config ({key}).")
        if "." in key and "*" not in key.split(".")[0]:
            name = key.split(".")[0]
            try:
                sub_config = getattr(
                    self, "___" + name if name in self._methods else name)
            except AttributeError:
                # This has to be performed in two steps, otherwise
                # the param inside the new sub-config does not get
                # pre-processed.
                object.__setattr__(
                    self, "___" + name if name in self._methods else name,
                    self.__class__(
                        name=name, overwriting_regime=self._main_config
                        .config_metadata["overwriting_regime"],
                        config_path_or_dictionary={}, state=self._state,
                        nesting_hierarchy=self._nesting_hierarchy + [name],
                        main_config=self._main_config,
                    ),
                )
                # Now, outside the nested "setup" state during __init__,
                # pre-processing is active
                dict_to_add = {key.split(".", 1)[1]: value}
                self[name]._init_from_config(dict_to_add)
                self[name].config_metadata["config_hierarchy"] += [dict_to_add]
            else:
                if isinstance(sub_config, Configuration):
                    sub_config._init_from_config({key.split(".", 1)[1]: value})
                else:
                    did_you_mean = self._did_you_mean(
                        key.split(".")[0], filter_type=self.__class__,
                        suffix=key.split(".", 1)[1],
                    )
                    raise TypeError("Failed to set parameter "
                                    f"'{key}' : '{key.split('.')[0]}' "
                                    f"is not a sub-config.\n{did_you_mean}")
        else:
            try:
                if key != "config_metadata":
                    _ = getattr(self,
                                "___" + key if key in self._methods else key)
                    raise RuntimeError(
                        f"ERROR : parameter '{key}' was set twice.")
            except AttributeError:
                if key in self._methods:
                    print(f"WARNING : '{key}' is the name of a method "
                          "in the Configuration object.")
                if isinstance(value, Configuration):
                    # This has to be performed in two steps, otherwise
                    # the param inside the new sub-config does
                    # not get pre-processed.
                    object.__setattr__(
                        self, "___" + key if key in self._methods else key,
                        self.__class__(
                            name=value._name, overwriting_regime=(
                                self._main_config
                                .config_metadata["overwriting_regime"]),
                            config_path_or_dictionary={}, state=self._state,
                            nesting_hierarchy=self._nesting_hierarchy
                            + ["___" + key if key in self._methods else key],
                            main_config=self._main_config,
                        ),
                    )
                    # Now, outside the nested "setup" state during __init__,
                    # pre-processing is active
                    dict_to_add = {
                        key: value[key]
                        for key in value._get_user_defined_attributes()
                    }
                    self[key]._init_from_config(dict_to_add)
                    self[key].config_metadata["config_hierarchy"] += [
                        dict_to_add
                    ]
                else:
                    if (self._state[0].split(";")[0] == "setup"
                            and [i.split(";")[0]
                                 for i in self._state].count("setup") < 2):
                        preprocessed_parameter = self._process_parameter(
                            key, value, "pre")
                    else:
                        preprocessed_parameter = value
                    object.__setattr__(
                        self, "___" + key if key in self._methods else key,
                        preprocessed_parameter,
                    )
                    if key not in self._modified_buffer:
                        self._modified_buffer.append(key)

    def _get_command_line_dict(
            self, string_to_merge: Optional[str] = None) -> Dict[str, Any]:
        """Method called automatically at the end of each constructor
        to gather all parameters from the command line into
        a dictionary. This dictionary is then merged."""
        # If a string is passed as input, process it as sys.argv would
        if string_to_merge is not None:
            list_to_merge = [""]
            in_quotes = []
            escaped = False
            for char in string_to_merge:
                if char == "\\" and not escaped:
                    escaped = True
                elif char in ['"', "'"] and not escaped:
                    if not in_quotes or in_quotes[-1] != char:
                        in_quotes.append(char)
                    else:
                        in_quotes.pop(-1)
                elif (char == " " and not in_quotes and list_to_merge[-1]
                      and not escaped):
                    list_to_merge.append("")
                else:
                    escaped = False
                    list_to_merge[-1] += char
            if in_quotes:
                raise ValueError(
                    "Could not parse args : open quotations were left "
                    f"unclosed : {in_quotes}.")
        else:
            list_to_merge = sys.argv

        # Setting the config to operational mode in case this
        # is called manually
        object.__setattr__(self, "_operating_creation_or_merging", True)

        # Gather parameters, their values and their types
        to_merge = {}  # {param: [former_value, new_value, type_forcing], ...}
        found_config_path = not self._from_argv
        in_param = []
        for element in list_to_merge:
            if element.startswith("--") and (found_config_path
                                             or element[2:] != "config"):
                if "=" in element:
                    pattern, value = element[2:].split("=", 1)
                    value = value if value != "" else None
                else:
                    pattern, value = element[2:], None
                in_param = []
                for parameter in self.get_parameter_names(deep=True):
                    if compare_string_pattern(parameter, pattern):
                        in_param.append(parameter)
                        to_merge[parameter] = [self[parameter], value, None]
                if not in_param:
                    print(
                        f"WARNING: parameter '{pattern}', encountered while "
                        "merging params from the command line, does not match"
                        " a param in the config. It will not be merged.")
            elif element.startswith("--"):
                in_param = []
                found_config_path = True
            elif in_param and to_merge[in_param[0]][1] is None:
                for parameter in in_param:
                    to_merge[parameter][1] = element
            elif in_param and element[0] == "!":
                if element[1:] in [
                        "int", "float", "str", "bool", "list", "dict"
                ]:
                    for parameter in in_param:
                        to_merge[parameter][2] = element[1:]
                    in_param = []
                else:
                    raise TypeError(
                        f"Unknown type '{element[1:]}', should be in "
                        "[int, float, str, bool, list, dict].")
            elif in_param:
                for parameter in in_param:
                    to_merge[parameter][1] += f" {element}"

        # Infer types, then return
        return {
            key: adapt_to_type(val[0], val[1], val[2], key)
            for key, val in to_merge.items()
        }

    def _post_process_modified_parameters(self) -> None:
        """This method is called at the end of a config creation
        or merging operation. It applies post-processing to all
        parameters modified by this operation. If a parameter
        is converted into a non-native YAML type, also keeps its former
        value in memory for saving purposes."""
        # pylint: disable=protected-access
        print("Performing post-processing for modified parameters...")
        modified = [
            ".".join(self.get_nesting_hierarchy()
                     + [self._modified_buffer.pop(0)])
            for _ in range(len(self._modified_buffer))
        ]
        for subconfig in self.get_all_linked_sub_configs():
            for _ in range(len(subconfig._modified_buffer)):
                modified.append(
                    ".".join(subconfig.get_nesting_hierarchy()
                             + [subconfig._modified_buffer.pop(0)]))
        for name in modified:
            split = name.split(".")[len(self._nesting_hierarchy):]
            name = ".".join(split)
            recursive_set_attribute(
                self, ".".join(split[:-1] + ["___" + split[-1]])
                if split[-1] in self._methods else name,
                self._process_parameter(name, self[name], "post"),
            )

    @update_state("processing;_name")
    def _process_parameter(self, name: str, parameter: Any,
                           processing_type: str) -> Any:
        """This method checks if a processing function has been defined
        for given name, then returns the processed value when that
        is the case."""
        # pylint: disable=protected-access
        if self._main_config._pre_process_master_switch:
            total_name = ".".join(self._nesting_hierarchy + [name])
            old_value = None
            if processing_type == "pre":
                transformation_dict = self.parameters_pre_processing()
            elif processing_type == "post":
                old_value = copy.deepcopy(parameter)
                transformation_dict = self.parameters_post_processing()
            else:
                raise ValueError(
                    f"Unknown processing_type : '{processing_type}'. "
                    "Valid types are 'pre', 'post', 'get'.")
            was_processed = False
            for key, item in transformation_dict.items():
                if compare_string_pattern(total_name, key):
                    was_processed = True
                    try:
                        parameter = item(parameter)
                    except Exception:
                        print(
                            f"ERROR while {processing_type}-processing param "
                            f"'{total_name}' :")
                        raise
            if processing_type == "pre" and not is_type_valid(
                    parameter, Configuration):
                raise RuntimeError(
                    f"ERROR while pre-processing param '{total_name}' : "
                    "pre-processing functions that change the type of a "
                    "param to a non-native YAML type are forbidden because "
                    "they cannot be saved. Please use a parameter "
                    "post-processing instead.")
            if processing_type == "post" and was_processed:
                self.get_main_config().save_value_before_postprocessing(
                    ".".join(self._nesting_hierarchy + [name]), old_value)
        return parameter
