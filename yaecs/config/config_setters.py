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
from functools import partial
import logging
from typing import Any, Callable, Dict, TYPE_CHECKING

from ..yaecs_utils import TypeHint
if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigSettersMixin:
    """ Setters Mixin class for YAECS configurations. """

    _main_config: 'Configuration'
    _pre_postprocessing_values: Dict[str, Any]
    _type_hints: Dict[str, TypeHint]

    def add_processing_function(self, param_name: str, function_to_add: Callable, processing_type: str) -> None:
        """
        If given parameter does not already have a post-processing function with the same name, adds given function as
        a post-processing function to parameters with the given name.
        :param param_name: parameter(s) to which to add a postprocessing function
        :param function_to_add: postprocessing function to add, using the generic name "function" if it has no name
        :param processing_type: choose between 'pre' to add a pre-processing function or 'post' to add a post-processing
        function
        """
        function_name = function_to_add.__name__ if hasattr(function_to_add, "__name__") else "function"
        method = f"parameters_{processing_type}_processing"
        current_processing = object.__getattribute__(self._main_config, method)()
        param_matches = self.match_params(param_name)
        if not any((all(i in self._main_config.match_params(k) for i in param_matches) and v.__name__ == function_name)
                   for k, v in current_processing.items()):
            if param_name in current_processing:
                def _composition(x, processing_dict, name, func):
                    return processing_dict[name](func(x))
                _composition = partial(_composition,
                                       processing_dict=current_processing, name=param_name, func=function_to_add)
                _composition.__name__ = "function_name"
                del current_processing[param_name]
                new_processing = {param_name: _composition, **current_processing}
            else:
                new_processing = {param_name: function_to_add, **current_processing}
            object.__setattr__(self._main_config.__class__, method, lambda x: new_processing)
        else:
            YAECS_LOGGER.warning(f"WARNING : Parameter '{param_name}' already has a post-processing function with the "
                                 f"name '{function_name}'. Processing function will not be added again.")

    def add_type_hint(self, name: str, type_hint: TypeHint) -> None:
        """
        Adds a type hint for a parameter to the list of type hints for automatic type checks.
        :param name: full path of the param in the main config
        :param type_hint: type of the param
        """
        self._type_hints[name] = type_hint

    def remove_type_hint(self, param_name: str) -> None:
        """
        Removes a registered type hint from a param with given name
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
