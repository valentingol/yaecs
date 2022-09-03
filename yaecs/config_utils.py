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
import functools
from collections.abc import Mapping
from typing import Any, Callable, List, Union


def adapt_to_type(previous_value: Any, value_to_adapt: str, force: str,
                  param: str) -> Any:
    """
    Uses the previous value (more specifically, its type) of a parameter
    to parse a string containing its new value. Takes into account
    attempts from the user to force the new value to take a new type.
    :param previous_value: previous value taken by the parameter
    :param value_to_adapt: string corresponding to the new value of the
    parameter
    :param force: previously-detected type-forcing tag
    :param param: name of the param for error logging
    :raises TypeError: if the new value type cannot be adapted
    :raises ValueError: the boolean value cannot be interpreted
    :return: new value for the param
    """

    def _parse_scalar(raw_string, force_):
        if force_ is None:
            for forced_type in ["int", "float", "str", "bool", "list", "dict"]:
                if (raw_string.endswith(f"!{forced_type}")
                        and raw_string[raw_string.rindex("!") - 1] != "\\"):
                    force_ = forced_type
                    raw_string = raw_string[:-1 - len(forced_type)]
        raw_string.lstrip(" ")
        while raw_string[-1] == " " and raw_string[-2] != "\\":
            raw_string = raw_string[:-1]
        to_return = ""
        esc = False
        for character in raw_string:
            if esc or character != "\\":
                esc = False
                to_return += character
            else:
                esc = True
        return raw_string, force_

    def _parse_container(container_string):
        new_list = [""]
        in_brackets = []
        esc = False
        for character in container_string:
            if esc:
                esc = False
                if character == " ":
                    new_list[-1] += "\\" + character
                else:
                    new_list[-1] += character
            else:
                if character == "\\":
                    esc = True
                elif character == "," and not in_brackets:
                    new_list.append("")
                elif character != " " or new_list[-1]:
                    new_list[-1] += character
                    if character in ["[", "{"]:
                        in_brackets.append(character)
                    if character == "]" and in_brackets[-1] == "[":
                        in_brackets.pop(-1)
                    if character == "}" and in_brackets[-1] == "{":
                        in_brackets.pop(-1)
        for i, val in enumerate(new_list):
            while val[-1] == " " and val[-2] != "\\":
                val = val[:-1]
            val = val.replace("\\ ", " ")
            forced = False
            for forced_type in ["int", "float", "str", "bool", "list", "dict"]:
                if (not forced and val.endswith(f"!{forced_type}")
                        and val[-2 - len(forced_type)] != "\\"):
                    forced = True
                    new_list[i] = [val[:val.rindex("!")], forced_type]
                    while (new_list[i][0][-1] == " "
                           and new_list[0][-2] != "\\"):
                        new_list[i][0] = new_list[i][0][:-1]
            if not forced:
                new_list[i] = [new_list[i], None]
        return new_list

    if value_to_adapt is None:
        return True

    if value_to_adapt.lower() in ["none", "null"] and force is None:
        return None

    scalar_parsed, force = _parse_scalar(value_to_adapt, force)

    if previous_value is None and force is None:
        if scalar_parsed.lower() not in ["none", "null"]:
            raise TypeError(
                f"Type of param '{param}' cannot be inferred because its "
                "previous value was None.\n. To overwrite None values from "
                "command line, please force their type :\n\nExample : \t\t "
                "python main.py --none_param=0.001 !float")
        return None

    if (isinstance(previous_value, str) and force is None) or force == "str":
        return scalar_parsed

    if (isinstance(previous_value, list) and force is None) or force == "list":
        if value_to_adapt[0] == "[" and value_to_adapt[-1] == "]":
            value_to_adapt = value_to_adapt[1:-1]
        value_to_adapt = (_parse_container(value_to_adapt)
                          if value_to_adapt else [])
        if isinstance(previous_value, list):
            if all(
                    isinstance(i, type(previous_value[-1]))
                    for i in previous_value[:-1]):
                return [
                    adapt_to_type(previous_value[0], v[0], v[1], param)
                    for v in value_to_adapt
                ]
            if len(previous_value) == len(value_to_adapt):
                return [
                    adapt_to_type(previous_value[index],
                                  value_to_adapt[index][0],
                                  value_to_adapt[index][1], param,
                                  ) for index in range(len(value_to_adapt))
                ]
            if all(v[1] is not None or v[0].lower() in ["none", "null"]
                   for v in value_to_adapt):
                return [
                    adapt_to_type(None, v[0], v[1], param)
                    for v in value_to_adapt
                ]
            raise TypeError(
                f"New value for list in '{param}' is inconsistent with "
                f"old value '{previous_value}'. If the new value is "
                "correct, please force the type of the elements in the "
                "list so type inference can be done.")
        if all(v[1] is not None or v[0].lower() in ["none", "null"]
               for v in value_to_adapt):
            return [
                adapt_to_type(None, v[0], v[1], param) for v in value_to_adapt
            ]
        raise TypeError(
            f"Since the previous value for '{param}' was not a list, none of "
            "its items' values can be inferred. Please force the type of all "
            "elements in the new value's list.")

    if (isinstance(previous_value, dict) and force is None) or force == "dict":
        if value_to_adapt[0] == "{" and value_to_adapt[-1] == "}":
            value_to_adapt = value_to_adapt[1:-1]
        value_to_adapt = (_parse_container(value_to_adapt)
                          if value_to_adapt else [])
        if any(value_to_adapt):
            value_to_adapt = {
                v[0].split(":", 1)[0]: (v[0].split(":", 1)[1], v[1])
                for v in value_to_adapt
            }
        else:
            value_to_adapt = {}
        if isinstance(previous_value, dict):
            if all(key in previous_value or value_to_adapt[key][1] is not None
                   or value_to_adapt[key][0].lstrip(
                       " ").lower() in ["none", "null"]
                   for key in value_to_adapt):
                return {
                    k.rstrip(" "): adapt_to_type(previous_value.get(k, None),
                                                 v[0].lstrip(" "), v[1], param,
                                                 )
                    for k, v in value_to_adapt.items()
                }
            raise TypeError(
                f"New value for dict in '{param}' is inconsistent with old "
                f"value '{previous_value}'. If the new value is correct, "
                "please force the type of the new elements in the dict so "
                "type inference can be done.")
        if all(value_to_adapt[key][1] is not None or value_to_adapt[key]
               [0].lstrip(" ").lower() in ["none", "null"]
               for key in value_to_adapt):
            return {
                k.rstrip(" "): adapt_to_type(None, v[0].lstrip(" "), v[1],
                                             param)
                for k, v in value_to_adapt.items()
            }
        raise TypeError(
            f"Since the previous value for '{param}' was not a dict, "
            "none of its keys' values can be inferred. Please force the "
            "type of all elements in the new value's dict.")

    if (isinstance(previous_value, int)
            and not isinstance(previous_value, bool)
            and force is None) or force == "int":
        return int(scalar_parsed)

    if ((isinstance(previous_value, float) and force is None)
            or force == "float"):
        return float(scalar_parsed)

    if ((isinstance(previous_value, bool) and force is None)
            or force == "bool"):
        if scalar_parsed.strip(" ").lower() in ["y", "yes", "true", "1"]:
            return True
        if scalar_parsed.strip(" ").lower() in ["n", "no", "false", "0"]:
            return False
        raise ValueError(
            "Boolean parameters can only be replaced with (non case sensitive)"
            " : \n"
            "- to get a True value : y, yes, true, 1\n"
            "- to get a False value : n, no, false, 0")


def are_same_sub_configs(first: Any, second: Any) -> bool:
    """
    Checks if two sub-configs have identical nesting hierarchies.
    :param first: first sub-config to check
    :param second: second sub-config to check
    :return: result of the check
    """
    if first.get_name() != second.get_name():
        return False
    nh1, nh2 = first.get_nesting_hierarchy(), second.get_nesting_hierarchy()
    return (len(nh1) == len(nh2)
            and all(nh1[i] == nh2[i] for i in range(len(nh1))))


def compare_string_pattern(name: str, pattern: str) -> bool:
    """
    Returns True when string 'name' matches string 'pattern',
    with the '*' character matching any number of characters.
    :param name: name to compare
    :param pattern: pattern to match
    :return: result of comparison
    """
    pattern = pattern.split("*")
    if len(pattern) == 1:
        return pattern[0] == name
    if not (name.startswith(pattern[0]) and name.endswith(pattern[-1])):
        return False
    for fragment in pattern:
        index = name.find(fragment)
        if index == -1:
            return False
        name = name[index + len(fragment):]
    return True


def dict_apply(dictionary: dict, function: Callable) -> dict:
    """
    Returns a copy of dict 'dictionary' where function 'function'
    was applied to all values.
    :param dictionary: dictionary to copy
    :param function: function to map
    :return: copied dictionary
    """
    return {k: function(v) for k, v in dictionary.items()}


def escape_symbols(string_to_escape: str, symbols: Union[List[str],
                                                         str]) -> str:
    """
    Take a string 'string_to_escape' as input and escapes characters
    as defined in 'symbols'.
    :param string_to_escape: string where the escaping operation takes
    place
    :param symbols: list of strings to escape or string containing
    the characters to escape
    :return: escaped string
    """
    for symbol in symbols:
        string_to_escape = string_to_escape.replace(symbol, f"\\{symbol}")
    return string_to_escape


def is_type_valid(value: Any, config_class: type) -> bool:
    """
    Checks whether input 'value' can be saved in a YAML file by
    Configuration's YAML Dumper.
    :param value: value to check the type of
    :param config_class: Configuration class, which must be passed as
    argument to avoid circular imports :(
    :return: result of the test
    """
    if isinstance(value, list):
        return all(is_type_valid(i, config_class) for i in value)
    if isinstance(value, (Mapping, config_class)):
        return all(is_type_valid(i, config_class) for i in value.values())
    return isinstance(value, (int, float, str)) or value is None


def get_param_as_parsable_string(param: Any, in_iterable: bool = False,
                                 ignore_unknown_types: bool = False) -> str:
    """
    Gets given value as a string that can be parsed by
    the Configuration.
    :param param:
    :param in_iterable: used only for bookkeeping in recursive calls
    :param ignore_unknown_types: how to treat types that cannot be
    parsed by the Configuration
    :raises TypeError: if the type of 'param' cannot be enforced
    :return: string usable in the command line to reproduce the value
    of param
    """
    # TODO after postprocessing is introduced change the behavior
    # of ignore_unknown_types
    if param is None:
        return "none"
    if isinstance(param, list):
        return (
            "["
            + ','.join([get_param_as_parsable_string(i, True)
                        for i in param]) + "] !list")
    if isinstance(param, dict):
        return ("{" + ",".join([
            f"{k}:{get_param_as_parsable_string(v, True)}"
            for k, v in param.items()
        ]) + "} !dict")
    if isinstance(param, int):
        type_forcing = "int"
    elif isinstance(param, float):
        type_forcing = "float"
    elif isinstance(param, str):
        type_forcing = "str"
    elif isinstance(param, bool):
        type_forcing = "bool"
    elif ignore_unknown_types:
        print(f"WARNING: parameter value '{param}' will not have its type "
              "enforced because it is not in [int, float, str, bool].")
        type_forcing = ""
    else:
        raise TypeError(
            f"Parameter value '{param}' will not have its type enforced "
            "because it is not in [int, float, str, bool]. Pass "
            "ignore_unknown_types=True to avoid enforcing type when type "
            "is unknown.")
    value = str(param)
    value = escape_symbols(value, ["\\"])
    if in_iterable:
        value = escape_symbols(value, ["{", "}", "[", "]", ","])
        value = escape_symbols(value, ["{", "}", "[", "]", ","])
    value = escape_symbols(value, ["'", '"', " "])
    return value + (f" !{type_forcing}" if type_forcing else "")


def recursive_set_attribute(obj: Any, key: str, value: Any) -> None:
    """
    Recursively gets attributes of 'obj' until object.__setattr__
    can be used to force-set parameter 'key' to value 'value'.
    :param obj: object where to set the key to the value
    :param key: attribute of the object to set recursively
    :param value: value to set
    """
    if "." in key:
        subconfig, key = key.split(".", 1)
        recursive_set_attribute(obj[subconfig], key, value)
    else:
        object.__setattr__(obj, key, value)


def update_state(state_descriptor: str) -> Callable:
    """
    Decorator used to store useful information in Configuration._state
    when using some recursive functions. Kind of a hack, but very useful
    to keep track of the loading state and also
    to debug.
    :param state_descriptor: string indicating what to store in
    Configuration._state
    :return: decorated function
    """

    def decorator_update_state(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapper_update_state(self, *args, **kwargs):
            # State name:
            state_to_append = state_descriptor.split(";")[0]
            for i in state_descriptor.split(";")[1:]:
                # Additional information:
                state_to_append += f";{getattr(self, i)}"
            first_arg = (args[0] if args else
                         (kwargs[list(kwargs.keys())[0]] if kwargs else None))
            self._state.append(  # pylint: disable=protected-access
                state_to_append
                + f";arg0={first_arg}")  # first arg of function call
            value = func(self, *args, **kwargs)
            self._state.pop(-1)  # pylint: disable=protected-access
            return value

        return wrapper_update_state

    return decorator_update_state
