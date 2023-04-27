"""
Reactive Reality Machine Learning Config System - ConfigConvenienceMixin object
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

from copy import deepcopy
import difflib
from functools import partial
import logging
import os
import time
from typing import (Any, Callable, Dict, ItemsView, KeysView, List, Optional, Tuple, Type, TYPE_CHECKING, Union,
                    ValuesView)
import yaml

from ..yaecs_utils import compare_string_pattern, dict_apply, format_str
if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigConvenienceMixin:
    """ Convenience functions Mixin class for YAECS configurations. """

    __getattribute__: Callable[[str], Any]
    config_metadata: dict
    get: Callable[[str, Any], Any]
    get_dict: Callable[[bool], dict]
    get_main_config: Callable[[], 'Configuration']
    get_name: Callable[[], str]
    get_parameter_names: Callable[[bool], List[str]]
    get_pre_post_processing_values: Callable[[], Dict[str, Any]]
    _get_full_path: Callable[[str], str]
    _get_user_defined_attributes: Callable[[], List[str]]
    _methods: List[str]
    _nesting_hierarchy: List[str]
    _protected_attributes: List[str]
    _verbose: bool
    _was_last_saved_as: Optional[str]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ConfigConvenienceMixin):
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

    def __hash__(self) -> int:
        return hash(repr(self.get_dict(True)))

    def __repr__(self) -> str:
        return "<Configuration:" + self.get_name() + ">"

    def compare(self, other: 'Configuration', reduce: bool = False) -> List[Tuple[str, Optional[Any]]]:
        """
        Returns a list of tuples, where each tuple represents a parameter that is different between the "self"
        configuration and the "other" configuration. Tuples are written in the form :
        (parameter_name, parameter_value_in_other). If parameter_name does not exist in other, (parameter_name, None) is
        given instead.
        :param other: config to compare self with
        :param reduce: tries to reduce the size of the output text as much as possible
        :return: difference list
        """

        def _investigate_parameter(parameter_name, object_to_check):
            """ Get name and values to display. """
            if reduce:
                name_path = parameter_name.split(".")
                to_display = name_path.pop(-1)
                while (len([
                        param for param in object_to_check.get_parameter_names(deep=True, no_sub_config=True)
                        if compare_string_pattern(param, "*." + to_display)
                ]) != 1 and name_path):
                    to_display = name_path.pop(-1) + "." + to_display
            else:
                to_display = parameter_name
            self_value = self.get_pre_post_processing_values().get(parameter_name, self.get(parameter_name, None))
            other_value = other.get_pre_post_processing_values().get(parameter_name, other.get(parameter_name, None))
            return self_value, other_value, to_display

        def _get_to_ret(value_self, value_other):
            """Get values to return in comparison."""
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
        self_parameter_names = self.get_parameter_names(deep=True, no_sub_config=True)
        for name in self_parameter_names:
            value_in_self, value_in_other, displayed_name = _investigate_parameter(name, self)
            if value_in_other != value_in_self:
                if not reduce:
                    differences.append((displayed_name, value_in_other))
                else:
                    if not isinstance(value_in_self, ConfigConvenienceMixin):
                        if isinstance(value_in_self, dict) and isinstance(value_in_other, dict):
                            differences.append((displayed_name, _get_to_ret(value_in_self, value_in_other)))
                        else:
                            differences.append((displayed_name, value_in_other))
        for name in other.get_parameter_names(deep=True, no_sub_config=True):
            _, value_in_other, displayed_name = _investigate_parameter(name, other)
            if name not in self_parameter_names and value_in_other is not None:
                if reduce:
                    if not isinstance(value_in_other, ConfigConvenienceMixin):
                        differences.append((displayed_name, value_in_other))
                else:
                    differences.append((displayed_name, value_in_other))
        return differences

    def copy(self) -> 'ConfigConvenienceMixin':
        """
        Returns a safe, independent copy of the config
        :return: instance of Configuration that is a deep copy of the config
        """
        return deepcopy(self)

    def details(self, show_only: Optional[Union[str, List[str]]] = None,
                expand_only: Optional[Union[str, List[str]]] = None, no_show: Optional[Union[str, List[str]]] = None,
                no_expand: Optional[Union[str, List[str]]] = None) -> str:
        """
        Creates and returns a string describing all the parameters in the config and its sub-configs.
        :param show_only: if not None, list of names referring to params. Only params in the list are displayed in the
        details.
        :param expand_only: if not None, list of names referring to sub-configs. Only sub-configs in the list are
        unrolled in the details.
        :param no_show: if not None, list of names referring to params. Params in the list are not displayed in the
        details.
        :param no_expand: if not None, list of names referring to sub-configs. Sub-configs in the list are not unrolled
        in the details.
        :return: string containing the details
        """
        constraints = {"show_only": show_only, "expand_only": expand_only, "no_show": no_show, "no_expand": no_expand}
        constraints = dict_apply(constraints, self.match_params)
        string_to_return = "\n" + "\t" * len(self._nesting_hierarchy) + self.get_name().upper() + " CONFIG :\n"
        if not self._nesting_hierarchy:
            string_to_return += "Configuration hierarchy :\n"
            for hierarchy_level in self.config_metadata["config_hierarchy"]:
                string_to_return += f"> {hierarchy_level}\n"
            string_to_return += "\n"
        to_print = [
            attribute for attribute in self._get_user_defined_attributes()
            if ((constraints["show_only"] is None or attribute in constraints["show_only"]) and (
                constraints["no_show"] is None or attribute not in constraints["no_show"]))
        ]

        def _for_sub_config(names, attribute):
            new = (None if names is None else [
                ".".join(c.split(".")[1:]) for c in names if (c.split(".")[0] == attribute and len(c.split(".")) > 1)
            ])
            return None if not new else new

        for attribute in to_print:
            string_to_return += ("\t" * len(self._nesting_hierarchy) + " - " + attribute + " : ")
            if isinstance(self[attribute], ConfigConvenienceMixin):
                if ((constraints["no_expand"] is None or attribute not in constraints["no_expand"])
                        and (constraints["expand_only"] is None
                             or attribute in [cstr.split(".")[0] for cstr in constraints["expand_only"]])):
                    _for_sub_config_attr = partial(_for_sub_config, attribute=attribute)
                    string_to_return += (self[attribute].details(**(dict_apply(constraints, _for_sub_config_attr)))
                                         + "\n")
                else:
                    string_to_return += self[attribute].get_name().upper()
                    string_to_return += "\n"
            else:
                string_to_return += str(self[attribute]) + "\n"
        return string_to_return

    def items(self, deep: bool = False) -> ItemsView:
        """
        Behaves as dict.items(). If deep is False, sub-configs remain sub-configs in the items. Otherwise, they are
        converted to dict.
        :param deep: how to return sub-configs that would appear among the items. If False, do not convert them, else
        recursively convert them to dict
        :return: the items of the config as in dict.items()
        """
        return self.get_dict(deep).items()

    def keys(self) -> KeysView:
        """
        Behaves as dict.keys(), returning a _dict_keys instance containing the names of the params of the config.
        :return: the keys if the config as in dict.keys()
        """
        return self.get_dict(False).keys()

    def match_params(self, *patterns: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
        """
        For a string, a list of strings or several strings, returns all params matching at least one of the input
        strings.
        :param patterns: string, a list of strings or several strings
        :return: all params matching at least one of the input string
        """
        patterns = (patterns[0] if len(patterns) == 1 and isinstance(patterns[0], list) else patterns)
        if patterns is None or (len(patterns) == 1 and patterns[0] is None):
            return None
        new_names = [n for n in patterns if "*" not in n and n in self.get_parameter_names(True)]
        for name in [n for n in patterns if "*" in n]:
            new_names = new_names + [p for p in self.get_parameter_names(True) if compare_string_pattern(p, name)]
        return new_names

    def save(self, filename: str = None, save_header: bool = True, save_hierarchy: str = True) -> None:
        """
        Saves the current config at the provided location. The saving format allows for a perfect recovery of the config
        by using : config = Configuration.load_config(filename). If no filename is given, overwrites the last save.
        :param filename: path to the saving location of the config
        :param save_header: whether to save the config metadata as the fist parameter. This will tag the saved file as a
        saved config in the eye of the config system when it gets merged, which will deactivate pre-processing
        :param save_hierarchy: whether to save config hierarchy as a '*_hierarchy.yaml' file
        :raises RuntimeError: no file name is provided and there is no previous save to overwrite
        """
        if filename is None:
            if self._was_last_saved_as is None:
                raise RuntimeError("No filename was provided, but the config was never "
                                   "saved before so there is no previous save to overwrite.")
            filename = self._was_last_saved_as
        self.config_metadata["creation_time"] = time.time()
        file_path, file_extension = os.path.splitext(filename)
        file_extension = file_extension if file_extension else ".yaml"
        config_dump_path = file_path + file_extension
        to_dump = {
            a: (getattr(self, "___" + a if a in self._methods else a) if
                (self._get_full_path(a) not in self.get_main_config().get_pre_post_processing_values()) else
                self.get_main_config().get_pre_post_processing_values()[self._get_full_path(a)]
                ) if a != "config_metadata" else self._format_metadata()
            for a in (["config_metadata"] if save_header else []) + self._get_user_defined_attributes()
        }
        with open(config_dump_path, "w", encoding='utf-8') as fil:
            yaml.dump(to_dump, fil, Dumper=self._get_yaml_dumper(), sort_keys=False, width=1000)

        if save_hierarchy:
            hierarchy_dump_path = f"{file_path}_hierarchy{file_extension}"
            to_dump = {"config_hierarchy": self.config_metadata["config_hierarchy"]}
            with open(hierarchy_dump_path, "w", encoding='utf-8') as fil:
                yaml.dump(to_dump, fil, Dumper=self._get_yaml_dumper(), width=1000)

        object.__setattr__(self, "_was_last_saved_as", config_dump_path)
        if self._verbose:
            YAECS_LOGGER.info(f"Configuration saved in : {format_str(os.path.abspath(config_dump_path))}.")

    def values(self, deep: bool = False) -> ValuesView:
        """
        Behaves as dict.values(). If deep is False, sub-configs remain sub-configs in the values. Otherwise, they are
        converted to dict.
        :param deep: how to return sub-configs that would appear among the values. If False, do not convert them, else
        recursively convert them to dict
        :return: the values of the config as in dict.values()
        """
        return self.get_dict(deep).values()

    def _did_you_mean(self, name: str, filter_type: Optional[type] = None, suffix: str = "") -> str:
        """ Used to propose suggestions when the user tries to access a parameter which does not exist. """
        all_params = self.get_parameter_names(True)
        close_params = []
        for parameter in all_params:
            if filter_type is None or isinstance(self[parameter], filter_type):
                if compare_string_pattern(parameter, f"*{name}*"):
                    if parameter not in close_params:
                        close_params.append(parameter)
        close_params.sort(key=len)
        for param in difflib.get_close_matches(name, all_params, n=len(all_params)):
            if filter_type is None or isinstance(self[param], filter_type):
                if param not in close_params:
                    close_params.append(param)
        if not close_params:
            return ""
        to_return = "Perhaps what you actually meant is in this list :"
        for param in close_params:
            to_return += f"\n- {param}{suffix}"
        return to_return

    def _format_metadata(self) -> str:
        """ Used to format the metadata for saving or printing. """
        return (f"Saving time : {time.ctime(self.config_metadata['saving_time'])} "
                f"({self.config_metadata['saving_time']}) ; "
                f"Regime : {self.config_metadata['overwriting_regime']}")

    def _get_yaml_dumper(self) -> Type[yaml.Dumper]:
        """ Used to get a custom YAML dumper capable of writing config tags. """

        def config_representer(yaml_dumper, class_instance):
            # pylint: disable=bad-continuation
            return yaml_dumper.represent_mapping(
                "!" + class_instance.get_name().split("_VARIATION_")[0], {
                    a[3:] if a.startswith("___") else a: self._format_metadata() if a == "config_metadata" else
                    (b if (".".join(class_instance.get_nesting_hierarchy()
                                    + [a]) not in self.get_main_config().get_pre_post_processing_values()) else
                        (self.get_main_config().get_pre_post_processing_values(
                             )[".".join(class_instance.get_nesting_hierarchy() + [a])]))
                    for (a, b) in class_instance.__dict__.items()
                    if a not in self._protected_attributes
                    and not (class_instance.get_nesting_hierarchy() and a in ["config_metadata"])
                },
            )

        dumper = yaml.Dumper
        dumper.add_representer(self.__class__, config_representer)
        return dumper
