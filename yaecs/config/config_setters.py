"""
Reactive Reality Machine Learning Config System - ConfigSettersMixin object
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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union

from ..yaecs_utils import TypeHint, are_same_sub_configs

if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigSettersMixin:
    """ Setters Mixin class for YAECS configurations. """

    _main_config: 'Configuration'
    _pre_postprocessing_values: Dict[str, Any]
    _sub_configs_list: List['Configuration']
    _type_hints: Dict[str, TypeHint]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_processing_function(self, param_name: str, function_to_add: Union[str, Callable], processing_type: str
                                ) -> None:
        """ If given parameter does not already have a post-processing function with the same name, adds given function
        as a post-processing function to parameters with the given name. """
        attribute = f"_{processing_type}_processing_functions"
        current_processing = object.__getattribute__(self, attribute)
        set_name = param_name
        while set_name in current_processing:
            set_name = set_name + " "
        new_processing = {set_name: function_to_add, **current_processing}
        object.__setattr__(self, attribute, new_processing)

    def add_processing_function_all(self, param_name: str, function_to_add: Union[str, Callable], processing_type: str
                                    ) -> None:
        """
        Triggers add_processing_function on the main config and all defined and future sub-configs.

        :param param_name: parameter(s) to which to add a postprocessing function. Expects paths with respect to the
            main config.
        :param function_to_add: postprocessing function to add, using the generic name "function" if it has no name
        :param processing_type: choose between 'pre' to add a pre-processing function or 'post' to add a post-processing
            function
        """
        if isinstance(function_to_add, str):
            check_function = self._assigned_as_yaml_tags[function_to_add[len("_tagged_method_"):]][0]
        else:
            check_function = function_to_add
        if hasattr(check_function, "assigned_yaml_tag"):
            if check_function.assigned_yaml_tag[1] != processing_type:
                name = "unknown_function" if not hasattr(check_function, "__name__") else check_function.__name__
                YAECS_LOGGER.warning(f"WARNING : processing function {name} is recommended to use "
                                     f"as {check_function.assigned_yaml_tag[1]}-processing function, "
                                     f"but was declared as {processing_type}-processing function.")
        current_added_processing_name = f"_added_{processing_type}_processing"
        current_added_processing = getattr(self, current_added_processing_name)()
        current_processing_name = f"_{processing_type}_processing_functions"
        current_processing = getattr(self, current_processing_name)
        set_name = param_name
        while set_name in current_processing or set_name in current_added_processing:
            set_name = set_name + " "
        if not any(v == function_to_add if isinstance(function_to_add, str) else v.__name__ == function_to_add.__name__
                   for k, v in current_added_processing.items()
                   if set_name.strip(" ") == k.strip(" ")):
            # Add to main config
            self._main_config.add_processing_function(param_name, function_to_add, processing_type)
            # Add to current sub-configs
            for subconfig in self.get_all_sub_configs():
                subconfig.add_processing_function(param_name, function_to_add, processing_type)
            # Add to future sub-configs
            new_processing = {set_name: function_to_add, **current_added_processing}
            setattr(self.__class__, current_added_processing_name, lambda self: new_processing)

    def add_type_hint(self, name: str, type_hint: TypeHint) -> None:
        """
        Adds a type hint for a parameter to the list of type hints for automatic type checks.

        :param name: full path of the param in the main config
        :param type_hint: type of the param
        """
        self._type_hints[name] = type_hint

    def set_sub_config(self, sub_config: 'Configuration') -> None:
        """
        Registers a new sub-config to the main config.

        :param sub_config: sub-config to register
        """
        if are_same_sub_configs(self, self._main_config):
            if all(not are_same_sub_configs(i, sub_config) for i in self.get_all_sub_configs()):
                self._sub_configs_list.append(sub_config)
        else:
            self._main_config.set_sub_config(sub_config)

    def remove_value_before_postprocessing(self, name: str) -> None:
        """
        Function used for bookkeeping : it remove a parameter from the pre-post-processing archive.

        :param name: name of the parameter using the dot convention
        """
        if name in self._pre_postprocessing_values:
            del self._pre_postprocessing_values[name]

    def remove_type_hint(self, param_name: str) -> None:
        """
        Removes a registered type hint from a param with given name.

        :param param_name: param from which to remove the type hint
        """
        if param_name in self._type_hints:
            del self._type_hints[param_name]

    def save_value_before_postprocessing(self, name: str, value: Any) -> None:
        """
        Function used for bookkeeping : it saves the value a parameter had before its post-processing.

        :param name: name of the parameter using the dot convention
        :param value: value of the parameter before post-processing
        """
        if name not in self._pre_postprocessing_values:
            self._pre_postprocessing_values[name] = value

    def set_post_processing(self, value: bool = True) -> None:
        """
        Sets the state of the master switch for pre-processing across the entire config object. Calling this for a
        sub-config will also affect the main config and all other sub-configs.

        :param value: value to set the pre-processing to
        """
        object.__setattr__(self._main_config, "_post_process_master_switch", value)

    def set_pre_processing(self, value: bool = True) -> None:
        """
        Sets the state of the master switch for pre-processing across the entire config object. Calling this for a
        sub-config will also affect the main config and all other sub-configs.

        :param value: value to set the pre-processing to
        """
        object.__setattr__(self._main_config, "_pre_process_master_switch", value)

    def unset_sub_config(self, sub_config: 'Configuration') -> None:
        """
        Registers a new sub-config to the main config.

        :param sub_config: sub-config to register
        """
        if are_same_sub_configs(self, self._main_config):
            self._sub_configs_list = [c for c in self.get_all_sub_configs() if not are_same_sub_configs(c, sub_config)]
        else:
            self._main_config.unset_sub_config(sub_config)
