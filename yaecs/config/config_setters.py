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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigSettersMixin:
    """ Setters Mixin class for YAECS configurations. """

    _main_config: 'Configuration'
    _pre_postprocessing_values: Dict[str, Any]
    _sub_configs_list: List['Configuration']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_processing_function(self, param_name: str, function_to_add: Union[str, Callable], processing_type: str,
                                source: Optional[str] = None, no_duplicates: bool = True) -> None:
        """
        Adds a processing function for a param pattern.

        :param param_name: parameter(s) to which to add a postprocessing function. Expects paths with respect to the
            main config.
        :param function_to_add: postprocessing function to add, using the generic name "function" if it has no name
        :param processing_type: choose between 'pre' to add a pre-processing function or 'post' to add a post-processing
            function
        :param source: name of the source of the function
        :param no_duplicates: if True, the function will not be added if it is already in the list of processing
        """
        self.get_setter().add_processor(processor=function_to_add, pattern=param_name, container=self,
                                        processing_type=processing_type, source=source, no_duplicates=no_duplicates)

    def remove_value_before_postprocessing(self, name: str) -> None:
        """
        Function used for bookkeeping : it remove a parameter from the pre-post-processing archive.

        :param name: name of the parameter using the dot convention
        """
        if name in self._pre_postprocessing_values:
            del self._pre_postprocessing_values[name]

    def save_value_before_postprocessing(self, name: str, value: Any) -> None:
        """
        Function used for bookkeeping : it saves the value a parameter had before its post-processing.

        :param name: name of the parameter using the dot convention
        :param value: value of the parameter before post-processing
        """
        if name not in self._pre_postprocessing_values:
            self._pre_postprocessing_values[name] = value

    def set_variation_name(self, value: Optional[str]) -> None:
        """
        Sets the variation name across the entire config object. Calling this for a sub-config will also affect the main
        config and all other sub-configs.

        :param value: value of the new variation name
        """
        object.__setattr__(self._main_config, "_variation_name", value)
        for subconfig in self._main_config.get_sub_configs(deep=True):
            object.__setattr__(subconfig, "_variation_name", value)
