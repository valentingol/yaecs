"""
Reactive Reality Machine Learning Config System - _ConfigurationBase object
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
import logging
import os
import sys
from collections.abc import Iterable
from numbers import Real
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

import yaml

from ..yaecs_utils import (ConfigDeclarator, NoValue,
                           check_type, compare_string_pattern, compose, format_str, get_quasi_bash_sys_argv, get_order,
                           is_dict_type_hint, is_type_valid, parse_type, recursive_set_attribute,
                           set_function_attribute, update_state)
from .config_convenience import ConfigConvenienceMixin
from .config_getters import ConfigGettersMixin
from .config_hooks import ConfigHooksMixin
from .config_processing_functions import ConfigProcessingFunctionsMixin
from .config_setters import ConfigSettersMixin
from .yaml_scanner import YAMLScanner

if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class _ConfigurationBase(ConfigHooksMixin, ConfigGettersMixin, ConfigSettersMixin, ConfigConvenienceMixin,
                         ConfigProcessingFunctionsMixin):
    """ Base class for YAECS configurations. Defines its basic behaviour, such as creation and merging operations,
    including processing- and type checking-related logic, but not its constructors (see Configuration class for those,
    and its docstring for more details about the composition of the Configuration superclass). """

    add_processing_function: Callable[[str, Callable, str], None]
    add_processing_function_all: Callable[[str, Callable, str], None]
    config_metadata: dict
    parameters_pre_processing: Callable[[], Dict[str, Callable]]
    parameters_post_processing: Callable[[], Dict[str, Callable]]
    _get_instance: Callable
    _get_tagged_methods_info: Callable[[], List[Tuple[Union[str, Callable]]]]
    _main_config: 'Configuration'
    _methods: List[str]
    _nesting_hierarchy: List[str]
    _operating_creation_or_merging: bool
    _protected_attributes: List[str]
    _state: List[str]
    _verbose: bool

    def __init__(self, from_argv: str = "", do_not_pre_process: bool = False, do_not_post_process: bool = False):
        """
        Should never be called directly by the user. Please use one of the constructors defined for the Configuration
        class instead, or the utils.make_config convenience function.

        :param from_argv: pattern used to find the config in the command line arguments, or "" if not applicable
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        :raises ValueError: if the overwriting regime is not valid
        :return: none
        """

        # PROTECTED ATTRIBUTES
        self._assigned_as_yaml_tags = self._get_tagged_methods_info()
        self._former_saving_time = None
        self._from_argv = from_argv
        self._modified_buffer = []
        self._post_process_master_switch = not do_not_post_process
        self._pre_process_master_switch = not do_not_pre_process
        for process_type in ["pre", "post"]:
            setattr(self, f"_{process_type}_processing_functions", {})
            self._prepare_processing_functions(process_type)
        self._pre_postprocessing_values = {}
        self._reference_folder = None
        self._sub_configs_list = []
        self._type_hints = {}
        self._was_last_saved_as = None
        super().__init__()

    def __getitem__(self, item) -> Any:
        if "." in item and "*" not in item:
            sub_config_name = ("___"
                               + item.split(".")[0] if item.split(".")[0] in self._methods else item.split(".")[0])
            sub_config = getattr(self, sub_config_name)
            if not isinstance(sub_config, _ConfigurationBase):
                did_you_mean_message = self._did_you_mean(sub_config_name, filter_type=self.__class__)
                raise TypeError(f"As the parameter '{sub_config_name}' is not a sub-config"
                                f", it cannot be accessed.\n{did_you_mean_message}")
            return sub_config[item.split(".", 1)[1]]
        return getattr(self, "___" + item if item in self._methods else item)

    def __setattr__(self, key, value) -> None:
        if (self.is_in_operation() or self._main_config.is_in_operation()
                or self.config_metadata["overwriting_regime"] == "unsafe"):
            object.__setattr__(self, key, value)
        elif self.config_metadata["overwriting_regime"] == "auto-save":
            self._manual_merge({key: value}, source='code')
        elif self.config_metadata["overwriting_regime"] == "locked":
            raise RuntimeError("Overwriting params in locked configs "
                               "is not allowed.")
        else:
            raise ValueError(f"No behaviour determined for value '"
                             f"{self.config_metadata['overwriting_regime']}' of "
                             f"parameter 'overwriting_regime'.")

    def __getattribute__(self, item) -> Any:
        try:
            return object.__getattribute__(self, item)
        except AttributeError as exception:
            if not item.startswith("_") and not any(state.startswith("setup") for state in self._state):
                raise AttributeError(f"Unknown parameter of the configuration : '{item}'.\n"
                                     f"{self._did_you_mean(item)}") from exception
            raise AttributeError from exception

    def __iter__(self):
        return iter(self._get_user_defined_attributes())

    @update_state("init_from_config;_name")
    def init_from_config(self, config_path_or_dict: ConfigDeclarator) -> None:
        """
        Entrypoint for all methods trying to get any value from outside the config to inside the config. This
        includes creating new parameters when creating the config or merging existing parameters after the creation.
        Users should only use this to merge or create parameters during a creation or merge operation (for instance in a
        processing function). If you want to merge parameters in your main code, outside a constructor or other
        operation, please use self.merge.

        :param config_path_or_dict: path or dictionary for the config to merge
        """
        if config_path_or_dict is None:
            config_path_or_dict = {}
        if isinstance(config_path_or_dict, str):
            config_path_or_dict = self._scan_yaml_files(config_path_or_dict)

        for item in config_path_or_dict.items():
            self._process_item_to_merge_or_add(item)

    def merge(self, config_path_or_dictionary: ConfigDeclarator, do_not_pre_process: bool = False,
              do_not_post_process: bool = False) -> None:
        """
        Merges provided config path of dictionary into the current config.

        :param config_path_or_dictionary: path or dictionary for the config to merge
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        """
        self._manual_merge(config_path_or_dictionary=config_path_or_dictionary, do_not_pre_process=do_not_pre_process,
                           do_not_post_process=do_not_post_process)

    def merge_from_command_line(self, to_merge: Optional[Union[List[str], str]] = None,
                                do_not_pre_process: bool = False, do_not_post_process: bool = False) -> None:
        """
        Formerly used to manually merge the command line arguments into the config, which is now done automatically and
        thus should no longer be done manually. Can still be used to manually merge a string emulating command line
        arguments.

        :param to_merge: if specified, merges this string or list of strings instead of the sys.argv list of strings
        :param do_not_pre_process: if true, pre-processing is deactivated in this initialization
        :param do_not_post_process: if true, post-processing is deactivated in this initialization
        """
        if self._verbose and to_merge is None:
            # TODO handle all warnings with a function _warn that logs and stores messages for future prints
            YAECS_LOGGER.warning("WARNING : merge_from_command_line is now deprecated and will automatically start "
                                 "after using any constructor.\nYou can remove the 'config.merge_from_command_line()' "
                                 "line from your code now :) it's redundant.")
        to_merge = self._gather_command_line_dict(to_merge)
        if to_merge:
            self._manual_merge(to_merge, do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process,
                               source='command line')

    @staticmethod
    def _added_pre_processing():
        """ Will contain pre-processing function added via self.add_processing_function_all. """
        return {}

    @staticmethod
    def _added_post_processing():
        """ Will contain post-processing function added via self.add_processing_function_all. """
        return {}

    def _find_path(self, path: str) -> str:
        """ Used to find a config from its (potentially relative) path, because it might be ambiguous relative to where
        it should be looked for. Probably very improvable. """
        def _get_path(path_to_check):
            if os.path.exists(path_to_check):
                return os.path.abspath(path_to_check)
            if path_to_check.endswith(".yaml") or path_to_check.endswith(".yml"):
                to_check = ".".join(path_to_check.split(".")[:-1])
            else:
                to_check = path_to_check
            there = [os.path.exists(to_check + ".yaml"), os.path.exists(to_check + ".yml"), os.path.exists(to_check)]
            if sum(there) == 0:
                return None
            if sum(there) == 1:
                return os.path.abspath([to_check + ".yaml", to_check + ".yml", to_check][there.index(True)])
            there.pop(there.index(False))
            raise RuntimeError(f"Ambiguity for provided path '{path_to_check}' : detected two possible paths :\n"
                               f"   - {there[0]}\n   - {there[1]}")

        # If the path is absolute, use it...
        if os.path.isabs(path):
            path = _get_path(path)
            if path is not None:
                self._reference_folder = str(Path(path).parents[0])
                return path

        # ... if not, search relatively to some reference folders.
        else:
            possibilities = []
            last_is_current = False

            # First check relatively to parent configs' directories...
            for config in reversed(self.config_metadata["config_hierarchy"]):
                if isinstance(config, str):
                    relative_path = os.path.join(Path(config).parents[0], path)
                    absolute_path = _get_path(relative_path)
                    if absolute_path is not None and absolute_path not in possibilities:
                        possibilities.append(absolute_path)

            # ... then also check the current reference folder since
            # the config hierarchy is not always up-to-date...
            if self._reference_folder is not None:
                relative_path = os.path.join(self._reference_folder, path)
                absolute_path = _get_path(relative_path)
                if absolute_path is not None and absolute_path not in possibilities:
                    possibilities.append(absolute_path)
            if self._main_config is not None and self._main_config.get_reference_folder() is not None:
                relative_path = os.path.join(self._main_config.get_reference_folder(), path)
                absolute_path = _get_path(relative_path)
                if absolute_path is not None and absolute_path not in possibilities:
                    possibilities.append(absolute_path)

            # ... and finally, check relatively to the current
            # working directory.
            absolute_path = _get_path(path)
            if absolute_path is not None and absolute_path not in possibilities:
                last_is_current = True
                possibilities.append(absolute_path)

            if len(possibilities) > 1:
                if path.endswith(".yaml"):
                    filtered = [p for p in possibilities if p.endswith(".yaml")]
                elif path.endswith(".yml"):
                    filtered = [p for p in possibilities if p.endswith(".yml")]
                else:
                    filtered = [p for p in possibilities if not p.endswith(".yaml") and not p.endswith(".yml")]
            else:
                filtered = possibilities

            if len(filtered) > 1:
                YAECS_LOGGER.warning(f"WARNING : Multiple matches for path {path}. '{filtered[0]}' will be used.\n"
                                     f"All matches : {filtered}.")
            if filtered:
                if last_is_current and filtered[0] == possibilities[-1]:
                    self._reference_folder = str(Path(absolute_path).parents[0])
                return filtered[0]

        raise FileNotFoundError(f"ERROR : path not found ({path}).")

    def _manual_merge(self, config_path_or_dictionary: ConfigDeclarator, do_not_pre_process: bool = False,
                      do_not_post_process: bool = False, source: str = 'config',
                      ) -> None:
        """ This method is called whenever a merge is done by the user, and not by the config creation process. It
        simply calls _merge with some additional bookkeeping. """
        self._merge(config_path_or_dictionary=config_path_or_dictionary, do_not_pre_process=do_not_pre_process,
                    do_not_post_process=do_not_post_process, source=source)
        self._post_process_modified_parameters()
        self.set_post_processing(True)
        if self.get_main_config().config_metadata["overwriting_regime"] == "auto-save":
            if self.get_main_config().get_save_file() is not None:
                self.get_main_config().save()

    @update_state("merging;_name")
    def _merge(self, config_path_or_dictionary: ConfigDeclarator, do_not_pre_process: bool = False,
               do_not_post_process: bool = False, source: str = 'config') -> None:
        """ Method handling all merging operations to call init_from_config with the proper bookkeeping. """
        if self._main_config == self:
            object.__setattr__(self, "_operating_creation_or_merging", True)
            if self._verbose:
                YAECS_LOGGER.info(f"Merging from {source} : {format_str(config_path_or_dictionary)}")
            self.set_post_processing(not do_not_post_process)
            self.set_pre_processing(not do_not_pre_process)
            self.init_from_config(config_path_or_dictionary)
            self.config_metadata["config_hierarchy"].append(config_path_or_dictionary)
            self.set_pre_processing(True)
            self._operating_creation_or_merging = False
        else:
            if isinstance(config_path_or_dictionary, str):
                config_path_or_dictionary = self._scan_yaml_files(config_path_or_dictionary)

            if config_path_or_dictionary is not None:
                config_path_or_dictionary = {self._get_full_path(a): b for a, b in config_path_or_dictionary.items()}

            self._main_config._merge(  # pylint: disable=protected-access
                config_path_or_dictionary=config_path_or_dictionary,
                do_not_pre_process=do_not_pre_process, do_not_post_process=do_not_post_process, source=source
            )

    @update_state("working_on;_name")
    def _process_item_to_merge_or_add(self, item: Tuple[str, Any]) -> None:
        """ Method called by init_from_config to merge or add a given key, value pair. """
        key, value = item

        # Process metadata. If there is metadata, treat the rest of the merge as "loading a saved file"... (which will
        # deactivate the parameter pre-processing for this merge).
        if key == "config_metadata":
            former_saving_time, regime, variation = self._parse_metadata(value)
            self._former_saving_time = former_saving_time
            self.config_metadata["overwriting_regime"] = regime
            self.set_variation_name(variation)
            self.set_pre_processing(False)
            return

        # ...do not accept other protected attributes to be merged...
        if key in self._protected_attributes:
            raise RuntimeError(f"Error : '{key}' is a protected name and cannot be used as a parameter name.")

        # ... otherwise, process the data normally :

        # If we are merging a parameter into a previously defined config...
        if not any(state.startswith("setup") for state in self._state):
            self._merge_item(key, value)

        # ... or if we are creating a config for the first time and are adding non-existing parameters to it
        else:
            self._add_item(key, value)

    def _merge_item(self, key: str, value: Any) -> None:
        """ Method called by _process_item_to_merge_or_add if the value should be merged and not added (ie., any time
        after the default config has been set up). This method ultimately performs all merges in the config. """

        if "*" in key:
            to_merge = {}
            for param in self.get_parameter_names(deep=True):
                if compare_string_pattern(param, key):
                    to_merge[param] = value
            if self._verbose:
                if not to_merge:
                    YAECS_LOGGER.warning(f"WARNING : parameter '{key}' will be ignored : it does not match any existing"
                                         " parameter.")
                else:
                    YAECS_LOGGER.info(f"Pattern parameter '{key}' will be merged into the following matched "
                                      f"parameters : {list(to_merge.keys())}.")
            self.init_from_config(to_merge)
            return

        name = key.split('.')[0]
        attribute_name = "___" + name if name in self._methods else name
        try:
            old_value = getattr(self, attribute_name)
        except AttributeError as exception:
            raise AttributeError(f"ERROR : parameter '{key}' cannot be merged : '{name}' is not in the default "
                                 f"'{self.get_name().upper()}' config.\n{self._did_you_mean(key)}") from exception

        if "." in key:
            if isinstance(old_value, _ConfigurationBase):
                old_value.init_from_config({key.split('.', 1)[1]: value})
            else:
                did_you_mean = self._did_you_mean(name, filter_type=self.__class__, suffix=key.split('.', 1)[1])
                raise TypeError(f"Failed to set parameter '{key}' : '{name}' is not a sub-config.\n{did_you_mean}")

        else:
            if isinstance(old_value, _ConfigurationBase):
                if isinstance(value, _ConfigurationBase):
                    value = value.get_dict(deep=False, pre_post_processing_values=False)
                if not isinstance(value, dict):
                    raise TypeError(f"Trying to set sub-config '{old_value.get_name()}'\n"
                                    f"with non-config element '{value}'.\nThis replacement cannot be performed.")
                old_value.init_from_config(value)
            else:
                if isinstance(value, _ConfigurationBase):
                    value = value.get_dict(deep=True, pre_post_processing_values=False)
                self._set_parameter(name, attribute_name, value, old_value)

    def _add_item(self, key: str, value: Any) -> None:
        """ Method called by _process_item_to_merge_or_add if the value should be added and not merged (ie., only while
        setting up the default config). This method ultimately performs all additions to the config. """
        if "*" in key:
            raise ValueError(f"The '*' character is not authorised in the default config ({key}).")

        name = key.split('.')[0]
        attribute_name = "___" + name if name in self._methods else name

        if "." in key:
            try:
                sub_config = getattr(self, attribute_name)
            except AttributeError:
                sub_config = self._set_sub_config(name, attribute_name)
            if isinstance(sub_config, _ConfigurationBase):
                sub_config.init_from_config({key.split(".", 1)[1]: value})
            else:
                did_you_mean = self._did_you_mean(name, filter_type=self.__class__, suffix=key.split(".", 1)[1])
                raise TypeError(f"Failed to set parameter '{key}' : '{name}' is not a sub-config.\n{did_you_mean}")

        else:
            try:
                _ = getattr(self, attribute_name)
                raise RuntimeError(f"ERROR : parameter '{name}' was set twice.")
            except AttributeError:
                if isinstance(value, _ConfigurationBase):
                    self._set_sub_config(name, attribute_name, {k: value[k] for k in value.get_parameter_names(False)})
                else:
                    self._set_parameter(name, attribute_name, value)

    def _set_parameter(self, name: str, attribute_name: str, value: Any, old_value: Any = NoValue()) -> None:
        """ Method called by _add_item and _merge_item to set a parameter in the config to a new value. Ultimately
        performs the setting of all parameters in the config. """
        if name != attribute_name and isinstance(old_value, NoValue) and self._verbose:
            YAECS_LOGGER.warning(f"WARNING : '{name}' is the name of a method in the Configuration object.\n"
                                 f"Your parameter was initialised anyways, under the name {attribute_name}. You can "
                                 f"access it via config.{attribute_name} or config['{name}'].")
        if self._verbose:
            old_value_message = "" if isinstance(old_value, NoValue) else f"old : '{old_value}'\n"
            YAECS_LOGGER.debug(f"Setting '{name}' : \n{old_value_message}new : '{value}'.")

        preprocessed_value = self._process_parameter(name, value, "pre")
        object.__setattr__(self, attribute_name, preprocessed_value)
        if name not in self._modified_buffer:
            self._modified_buffer.append(name)

    def _set_sub_config(self, name: str, attribute_name: str, content: Optional[dict] = None) -> 'Configuration':
        """ Method called by _add_item to add a sub-config to a config. First an empty config is created, then its
        values are added with its init_from_config method. """
        sub_config = self._get_instance(
            name=name,
            overwriting_regime=(self._main_config.config_metadata["overwriting_regime"]),
            config_path_or_dictionary={} if content is None else content,
            state=self._state,
            nesting_hierarchy=self._nesting_hierarchy + [attribute_name],
            main_config=self._main_config,
            verbose=self._verbose
        )
        object.__setattr__(self, attribute_name, sub_config)
        return sub_config

    def _gather_command_line_dict(self, to_merge: Optional[Union[List[str], str]] = None) -> Dict[str, Any]:
        """ Method called automatically at the end of each constructor to gather all parameters from the command line
        into a dictionary. This dictionary is then merged. """

        if to_merge is not None:
            if isinstance(to_merge, list):
                to_merge = " ".join(to_merge)
            list_to_merge = get_quasi_bash_sys_argv(to_merge)
        else:
            list_to_merge = sys.argv

        # Setting the config to operational mode in case this is called manually
        object.__setattr__(self, "_operating_creation_or_merging", True)

        # Gather parameters, their values and their types
        to_merge = {}  # {param_name: new_value, ...}
        found_config_path = not bool(self._from_argv)
        in_param = []
        un_matched_params = []
        for element in list_to_merge:
            if element.startswith("--") and (found_config_path or element.split("=", 1)[0] != self._from_argv):
                if "=" in element:
                    pattern, value = element[2:].split("=", 1)
                    value = value if value != "" else None
                else:
                    pattern, value = element[2:], None
                in_param = []
                for parameter in self.get_parameter_names(deep=True):
                    if compare_string_pattern(parameter, pattern):
                        in_param.append(parameter)
                        to_merge[parameter] = value
                if not in_param:
                    un_matched_params.append(pattern)
            elif element.startswith("--"):
                in_param = []
                found_config_path = True
            elif in_param and to_merge[in_param[0]] is None:
                for parameter in in_param:
                    to_merge[parameter] = element
            elif in_param:
                for parameter in in_param:
                    to_merge[parameter] = f"{to_merge[parameter]} {element}"

        if un_matched_params and self._verbose:
            YAECS_LOGGER.warning(f"WARNING : parameters {un_matched_params}, encountered while merging params from the "
                                 f"command line, do not match any param in the config. They will not be merged.")

        # Infer types, then return
        return {key: yaml.safe_load("true" if val is None else val) for key, val in to_merge.items()}

    def _post_process_modified_parameters(self) -> None:
        """ This method is called at the end of a config creation or merging operation. It applies post-processing to
        all parameters modified by this operation. If a parameter is converted into a non-native YAML type, also keeps
        its former value in memory for saving purposes. """
        modified = [self._get_full_path(self._modified_buffer.pop(0)) for _ in range(len(self._modified_buffer))]  # TODO keep in here after refactoring
        for subconfig in self.get_sub_configs(deep=True):  # TODO move to a unique buffer in the main config
            modified_buffer = subconfig.get_modified_buffer()
            for _ in range(len(modified_buffer)):
                modified.append(".".join(subconfig.get_nesting_hierarchy() + [modified_buffer.pop(0)]))
        processors = [(proc if isinstance(proc, Callable)
                       else getattr(self, self._assigned_as_yaml_tags[proc[len("_tagged_method_"):]]["name"]))
                      for proc in self._post_processing_functions.values()]
        orders = sorted(list({get_order(func) for func in processors}))
        splits = [name.split(".")[len(self._nesting_hierarchy):] for name in modified]  # TODO this won't be needed either, actually merging operations are all sent to the main config
        names = [(".".join(s), ".".join(s[:-1] + ["___" + s[-1]]) if s[-1] in self._methods else ".".join(s))
                 for s in splits]
        for order in orders:
            for name, set_name in names:
                recursive_set_attribute(self, set_name, self._process_parameter(name, self[name], "post", order))  # TODO keep the recursive set here after refactoring
        post_processed = [param for param in modified if param in self._pre_postprocessing_values]
        if post_processed and self._verbose:
            YAECS_LOGGER.info(f"Performed post-processing for modified parameters {post_processed}.")

    def _prepare_processing_functions(self, processing_type: str) -> None:
        """ Sets self._pre/post_processing_functions from the user-provided functions. """
        processing_functions = {**getattr(self, f"parameters_{processing_type}_processing")(),
                                **getattr(self, f"_added_{processing_type}_processing")()}  # TODO keep in here after refactoring
        for key, value in processing_functions.items():

            if not isinstance(value, (Callable, Iterable)):
                raise TypeError(f"Invalid {processing_type}-processing functions defined for param '{key}' : "
                                "the function should be declared as either a function or an iterable of functions, "
                                "optionally containing one order value.")

            if isinstance(value, Iterable) and not (isinstance(value, str) and value.startswith("_tagged_method_")):
                if any(not isinstance(element, (Callable, Real)) for element in value):
                    raise TypeError(f"Invalid {processing_type}-processing functions defined for param '{key}' : "
                                    "if function is declared as iterable, only functions and one order value can "
                                    "be provided.")
                order = [i for i in value if isinstance(i, Real)]
                if len(order) > 1:
                    raise ValueError(f"Ambiguous order for {processing_type}-processing functions defined for param "
                                     f"'{key}' : multiple orders defined ({order}).")
                processing_function = compose(*[i for i in value if isinstance(i, Callable)])
                order = order[0] if order else get_order(processing_function)
                set_function_attribute(processing_function, "order", order)

            else:
                processing_function = value

            self.add_processing_function(key, processing_function, processing_type)

    @update_state("processing;_name")
    def _process_parameter(self, name: str, parameter: Any, processing_type: str, order: Optional[Real] = None) -> Any:
        """ This method checks if a processing function has been defined for given name, then returns the processed
        value when that is the case. """
        if processing_type not in ["pre", "post"]:
            raise ValueError(f"Unknown processing_type : '{processing_type}'. Valid types are 'pre' or 'post'.")
        total_name = self._get_full_path(name)
        main = self.get_main_config()
        processors = [proc for key, proc in getattr(self, f"_{processing_type}_processing_functions").items()
                      if compare_string_pattern(total_name, key)]
        processors = [(proc if isinstance(proc, Callable)
                       else getattr(self, self._assigned_as_yaml_tags[proc[len("_tagged_method_"):]]["name"]))
                      for proc in processors]
        processors = sorted([p for p in processors if order is None or get_order(p) == order], key=get_order)
        if processing_type == "pre":
            main.remove_value_before_postprocessing(total_name)  # TODO keep in here after refactoring
        if main.get_master_switch(processing_type):
            old_value = None
            if processing_type == "pre":
                check_type(main.get_type_hint(total_name), total_name)(parameter)
            else:
                old_value = copy.deepcopy(parameter)  # TODO keep in here after refactoring
            was_processed = bool(processors)
            for processor in processors:
                try:
                    parameter = processor(parameter)
                except Exception:
                    YAECS_LOGGER.error(f"ERROR while {processing_type}-processing param '{total_name}'.")
                    raise
            if processing_type == "pre" and not is_type_valid(parameter, _ConfigurationBase):
                raise RuntimeError(f"ERROR while pre-processing param '{total_name}' : pre-processing functions that "
                                   "change the type of a param to a non-native YAML type are forbidden because they "
                                   "cannot be saved. Please use a parameter post-processing instead.")
            if processing_type == "post" and was_processed:
                main.save_value_before_postprocessing(self._get_full_path(name), old_value)  # TODO keep in here after refactoring
        return parameter

    def _parse_metadata(self, metadata: str) -> Tuple[str, str]:
        """ Parses metadata string to get the saving time, regime and variation name if there is one. """
        pattern = "Saving time : * (*) ; Regime : *"
        if not isinstance(metadata, str) or not compare_string_pattern(metadata, pattern):
            raise RuntimeError("'config_metadata' is a special parameter. Please do not edit or set it.")
        if metadata.count(";") == 1:
            time_chunk, regime_chunk = metadata.split(";")
            variation_chunk = None
        else:
            time_chunk, regime_chunk, variation_chunk = metadata.split(";")
        former_saving_time = float(time_chunk.split("(")[-1].split(")")[0].strip())
        regime = regime_chunk.split(":")[1].strip()
        if regime == "unsafe" and self._verbose:
            YAECS_LOGGER.warning("WARNING : YOU ARE LOADING AN UNSAFE CONFIG FILE. Reproducibility with "
                                 "corresponding experiment is not ensured.")
        elif regime not in ["auto-save", "locked"]:
            raise ValueError("'overwriting_regime' is a special parameter. It can only be set to 'auto-save'"
                             "(default), 'locked' or 'unsafe'.")
        variation = None if variation_chunk is None else variation_chunk.split(":")[1].strip()
        return former_saving_time, regime, variation

    def _scan_yaml_files(self, path: str) -> List[str]:
        """ Scans a YAML file for its parameters, gathers and adds type hints and processing functions. """
        path = self._find_path(path)
        scanner = YAMLScanner(path)

        if not any(state.startswith("setup") for state in self._state):
            ignored_hints = [param for param, type_hint in scanner.type_hints.items()
                             if not is_dict_type_hint(type_hint)]
            if ignored_hints and self._verbose:
                YAECS_LOGGER.warning("WARNING : type-hinting only has effect in the default config (except for dict "
                                     f"type hints). The type hints {ignored_hints} in file '{path}' will be ignored.")
            ignored_processors = list(scanner.processing_functions.keys())
            if ignored_processors and self._verbose:
                YAECS_LOGGER.warning("WARNING : registering processing functions only has effect in the default config."
                                     f" The functions {ignored_processors} in file '{path}' will be ignored.")
        processors_in_hints = {param: type_hint.split(",") for param, type_hint in scanner.type_hints.items()
                               if all(method in self._assigned_as_yaml_tags for method in type_hint.split(","))}
        if processors_in_hints and self._verbose:
            YAECS_LOGGER.warning("WARNING : registering processing functions using !type:<method_name> is deprecated. "
                                 "It will still work until the next release, but you should switch to using "
                                 f"!<method_name> instead (detected in tags '{processors_in_hints}' in file '{path}').")

        type_hints = {param: type_hint for param, type_hint in scanner.type_hints.items()
                      if ((any(state.startswith("setup") for state in self._state) or is_dict_type_hint(type_hint))
                      and any(method not in self._assigned_as_yaml_tags for method in type_hint.split(",")))}
        for param, type_hint in type_hints.items():
            self.add_type_hint(param, parse_type(type_hint))

        processors = {param: methods for param, methods in scanner.processing_functions.items()
                      if any(state.startswith("setup") for state in self._state)
                      and all(method in self._assigned_as_yaml_tags for method in methods)}
        processors = {**processors, **processors_in_hints}
        for param, methods in processors.items():
            if all(method in self._assigned_as_yaml_tags for method in methods):
                type_hint = None
                lowest_priority = min(self._assigned_as_yaml_tags[method].get("order", 0) for method in methods)
                for method in methods:
                    if self.get_variation_name() is None:
                        self.add_processing_function_all(self._get_full_path(param),
                                                         f"_tagged_method_{method}",
                                                         self._assigned_as_yaml_tags[method]["processing_type"])
                    if type_hint is None and self._assigned_as_yaml_tags[method].get("order", 0) == lowest_priority:
                        type_hint = self._assigned_as_yaml_tags[method]["input_type"]
                self.add_type_hint(param, parse_type(type_hint))
            else:
                raise ValueError(f"Some processing functions in {methods} for parameter '{param}' in file '{path}' "
                                 "do not match any registered processing function. Valid processing functions "
                                 f"are : {list(self._assigned_as_yaml_tags.keys())}.")

        return scanner.params
