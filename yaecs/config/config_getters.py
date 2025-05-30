"""
Reactive Reality Machine Learning Config System - ConfigGettersMixin object
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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

from ..yaecs_utils import get_param_as_parsable_string

if TYPE_CHECKING:
    from .config import Configuration
    from .setter import Setter

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigGettersMixin:
    """ Getters Mixin class for YAECS configurations. """

    __getattribute__: Callable[[str], Any]
    _main_config: 'Configuration'
    _methods: List[str]
    _modified_buffer: List[str]
    _name: str
    _nesting_hierarchy: List[str]
    _operating_creation_or_merging: bool
    _pre_post_processing_values: Dict[str, Any]
    _protected_attributes: List[str]
    _reference_folder: Optional[str]
    _state: List[str]
    _sub_configs_list: List['Configuration']
    _variation_name: str
    _was_last_saved_as: Optional[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def get_sub_configs(self, deep: bool = True) -> List['Configuration']:
        """
        Returns the list of all sub-configs, including sub-configs of other sub-configs

        :return: list corresponding to the sub-configs
        """
        all_sub_configs = []
        for i in self._get_user_defined_attributes():
            object_to_scan = getattr(self, "___" + i if i in self._methods else i)
            if isinstance(object_to_scan, ConfigGettersMixin):
                all_sub_configs += [object_to_scan] + (object_to_scan.get_sub_configs(deep=True) if deep else [])
        return all_sub_configs

    def get_command_line_argument(self, deep: bool = True, do_return_string: bool = False) -> Union[List[str], str]:
        """
        Returns a list of command line parameters that can be used in a bash shell to re-create this exact config
        from the default. Can alternatively return the string itself with do_return_string=True.

        :param deep: whether to also take the sub-config parameters into account
        :param do_return_string: whether to return a string (True) or a list of strings (False, default)
        :return: list or string containing the parameters
        """
        to_return = []
        for param in self.get_parameter_names(deep=deep):
            if not isinstance(self[param], ConfigGettersMixin):
                full_name = self._get_full_path(param)
                value = get_param_as_parsable_string(
                    self[param] if full_name not in self._main_config.get_pre_post_processing_values() else
                    self._main_config.get_pre_post_processing_values()[full_name],
                )
                to_return.append(f"--{param} {value}")

        return " ".join(to_return) if do_return_string else to_return

    def get_dict(self, deep: bool = True, pre_post_processing_values: bool = False) -> dict:
        """
        Returns a dictionary corresponding to the config.

        :param deep: whether to recursively turn sub-configs into dicts or keep them as sub-configs
        :param pre_post_processing_values: whether to return the values before the post-processing step
        :return: dictionary corresponding to the config
        """
        to_return = {}
        for key in self._get_user_defined_attributes():
            if deep and isinstance(self[key], ConfigGettersMixin):
                to_return[key] = self[key].get_dict(deep=True, pre_post_processing_values=pre_post_processing_values)
            else:
                full_name = self._get_full_path(key)
                to_return[key] = (self._main_config.get_pre_post_processing_values().get(full_name, self[key])
                                  if pre_post_processing_values else self[key])
        return to_return

    def get_main_config(self) -> 'Configuration':
        """
        Getter for the main config corresponding to this config or sub-config. Using this is often hacky.

        :return: the main config
        """
        return self._main_config

    def get_modified_buffer(self) -> List[str]:
        """
        Getter for the buffer of modified parameters corresponding to this config or sub-config. This gets filled during
        a creation or merging operation to keep track of all the parameters modified by this operation. Then, it is
        emptied as all modified parameters get post-processed before the end of the operation.

        :return: the buffer of modified elements
        """
        if self._is_main_config():
            return self._modified_buffer
        return self._main_config.get_modified_buffer()

    def get_name(self) -> str:
        """
        Returns the name of the config. It is composed of a specified part (or 'main' when unspecified) and an indicator
        of its index in the list of variations of its parent if it is a variation of a config. This indicator is
        prefixed by '_VARIATION_'.

        :return: string corresponding to the name
        """
        variation_suffix = ("_VARIATION_" + self._variation_name if self._variation_name is not None else "")
        return self._name + variation_suffix

    def get_nesting_hierarchy(self) -> List[str]:
        """
        Returns the nesting hierarchy of the config

        :return: list corresponding to the nesting hierarchy
        """
        return self._nesting_hierarchy

    def get_parameter_names(self, deep: bool = True, no_sub_config: bool = False) -> List[str]:
        """
        Returns the list of the names all parameters in this config. If deep is true, also returns the names of the
        parameters in the sub-configs using the dot convention.

        :param deep: whether to also return the names of the parameters in the sub-configs
        :param no_sub_config: if True, exclude names of sub-configs and only return real parameters
        :return: the list of the names of all parameters
        """
        complete_list = self._get_user_defined_attributes(no_sub_config=no_sub_config)
        if deep:
            order = len(self.get_nesting_hierarchy())
            for subconfig in self.get_sub_configs(deep=True):
                complete_list += [".".join(subconfig.get_nesting_hierarchy()[order:] + [param])
                                  for param in subconfig.get_parameter_names(deep=False, no_sub_config=no_sub_config)]
        return complete_list

    def get_pre_post_processing_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary containing :

        * as keys : all the names of the parameters which have been post-processed
        * as values : the values those parameters had before the post-processing operation

        In particular, those values are the ones used when saving the config.

        :return: dictionary of values before post-processing
        """
        return self._pre_postprocessing_values

    def get_processed_param_name(self, full_path: bool = True) -> str:
        """
        When used in a processing function, returns the full path to that param in the config, or its path in self if
        full_path is False.

        :param full_path: if True, returns the path to the param in the main config, otherwise the path to the param in
            self.
        """
        full_path = self._get_param_name_from_state()
        if full_path:
            return full_path
        config_path = ".".join(self._nesting_hierarchy)
        if not full_path.startswith(config_path):
            raise ValueError("Attempting to get the path of a param relative to a config that it's not a sub-param of.")
        return full_path[len(config_path)+1:]

    def get_setter(self) -> 'Setter':
        """
        Returns the Setter object of the main config.

        :return: the Setter object
        """
        if self._is_main_config():
            return self._setter
        return self._main_config.get_setter()

    def get_save_file(self) -> Optional[str]:
        """
        If the config was saved previously, returns the path to this save. Otherwise, returns None.

        :return: the path to the save if it exists, None otherwise
        """
        return self._was_last_saved_as

    def get_reference_folder(self) -> Optional[str]:
        """
        If a reference folder has been registered, returns it. Otherwise, returns None.

        :return: the reference folder if it exists, None otherwise
        """
        return self._reference_folder

    def get_variation_name(self) -> str:
        """
        Returns the variation name of the config

        :return: variation name
        """
        return self._variation_name

    def is_in_operation(self) -> bool:
        """
        Returns whether the config is currently in a creation or merging process.

        :return: True if the config is in a creation or merging process, False otherwise
        """
        return self._operating_creation_or_merging

    def _get_full_path(self, param_name: str) -> str:
        """ Get the full name of given param in the main config """
        return ".".join(self._nesting_hierarchy + [param_name])

    def _get_param_name_from_state(self) -> str:
        """ If there is a param processing in the state stack, returns the name of the param. """
        name = None
        for state in self._state[::-1]:
            if state.startswith("processing"):
                if state.count(";arg0=") > 1:
                    raise ValueError("How did you even manage to raise this ?")
                name = state.split(";arg0=")[-1]
                break
        if name is None:
            raise RuntimeError("Processing function was called outside a processing phase.")
        return name

    def _get_tagged_methods_info(self) -> List[Tuple[Union[str, Callable]]]:
        """ Returns a list of info on the methods which were assigned a YAML tag. """
        to_return = {}
        for method in [getattr(self, name) for name in self._methods]:
            if hasattr(method, "yaecs_metadata"):
                metadata = getattr(method, "yaecs_metadata")
                if "tag" in metadata and metadata["tag"] in self._methods and metadata["tag"] != metadata["name"]:
                    raise ValueError(f"YAML tag '{metadata['tag']}' of method '{metadata['name']}' is ambiguous with "
                                     "the name of another method. Please choose a different tag.")
                metadata["tag"] = metadata["tag"] if "tag" in metadata else metadata["name"]
                if metadata["tag"] in to_return:
                    raise ValueError(f"The name of method '{metadata['name']}' is ambiguous with the tag of method "
                                     f"'{to_return[metadata['tag']]['name']}'. Please choose a different tag or name.")
                to_return[metadata["tag"]] = metadata
        return to_return

    def _get_user_defined_attributes(self, no_sub_config: bool = False) -> List[str]:
        """ Frequently used to get a list of the names of all the parameters that were in the user's config. """
        return [
            i[3:] if i.startswith("___") else i
            for i in self.__dict__
            if (i not in self._protected_attributes + ["config_metadata"]
                and not (no_sub_config and isinstance(self[i], ConfigGettersMixin)))
        ]
