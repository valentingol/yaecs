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
import sys
import functools
import importlib.util
import io
import logging
import os
import re
from bisect import bisect
from collections.abc import Mapping
from typing import Any, Callable, Dict, List, Union

YAECS_LOGGER = logging.getLogger(__name__)
ConfigDeclarator = Union[str, dict]
Hooks = Union[Dict[str, List[str]], List[str]]
TypeHint = Union[type, tuple, list, dict, set, int]
VariationDeclarator = Union[List[ConfigDeclarator], Dict[str, ConfigDeclarator]]


def adapt_to_type(previous_value: Any, value_to_adapt: str, force: str, param: str) -> Any:
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
                if raw_string.endswith(f"!{forced_type}") and raw_string[raw_string.rindex("!") - 1] != "\\":
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
        for i in range(len(new_list)):  # pylint: disable=consider-using-enumerate
            while new_list[i][-1] == " " and new_list[i][-2] != "\\":
                new_list[i] = new_list[i][:-1]
            new_list[i] = new_list[i].replace("\\ ", " ")
            forced = False
            for forced_type in ["int", "float", "str", "bool", "list", "dict"]:
                if (not forced and new_list[i].endswith(f"!{forced_type}")
                        and new_list[i][-2 - len(forced_type)] != "\\"):
                    forced = True
                    new_list[i] = [new_list[i][:new_list[i].rindex("!")], forced_type]
                    while new_list[i][0][-1] == " " and new_list[0][-2] != "\\":
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
            raise TypeError(f"Type of param '{param}' cannot be inferred because its "
                            "previous value was None.\n. To overwrite None values from "
                            "command line, please force their type :\n\nExample : \t\t "
                            "python main.py --none_param=0.001 !float")
        return None

    if (isinstance(previous_value, str) and force is None) or force == "str":
        return scalar_parsed

    if (isinstance(previous_value, list) and force is None) or force == "list":
        if value_to_adapt[0] == "[" and value_to_adapt[-1] == "]":
            value_to_adapt = value_to_adapt[1:-1]
        value_to_adapt = (_parse_container(value_to_adapt) if value_to_adapt else [])
        if isinstance(previous_value, list):
            if all(isinstance(i, type(previous_value[-1])) for i in previous_value[:-1]):
                return [adapt_to_type(previous_value[0], v[0], v[1], param) for v in value_to_adapt]
            if len(previous_value) == len(value_to_adapt):
                return [
                    adapt_to_type(previous_value[index], value_to_adapt[index][0], value_to_adapt[index][1], param,
                                  ) for index in range(len(value_to_adapt))
                ]
            if all(v[1] is not None or v[0].lower() in ["none", "null"] for v in value_to_adapt):
                return [adapt_to_type(None, v[0], v[1], param) for v in value_to_adapt]
            raise TypeError(f"New value for list in '{param}' is inconsistent with "
                            f"old value '{previous_value}'. If the new value is "
                            "correct, please force the type of the elements in the "
                            "list so type inference can be done.")
        if all(v[1] is not None or v[0].lower() in ["none", "null"] for v in value_to_adapt):
            return [adapt_to_type(None, v[0], v[1], param) for v in value_to_adapt]
        raise TypeError(f"Since the previous value for '{param}' was not a list, none of "
                        "its items' values can be inferred. Please force the type of all "
                        "elements in the new value's list.")

    if (isinstance(previous_value, dict) and force is None) or force == "dict":
        if value_to_adapt[0] == "{" and value_to_adapt[-1] == "}":
            value_to_adapt = value_to_adapt[1:-1]
        value_to_adapt = (_parse_container(value_to_adapt) if value_to_adapt else [])
        if any(value_to_adapt):
            value_to_adapt = {v[0].split(":", 1)[0]: (v[0].split(":", 1)[1], v[1]) for v in value_to_adapt}
        else:
            value_to_adapt = {}
        if isinstance(previous_value, dict):
            if all(key in previous_value or value_to_adapt[key][1] is not None
                   or value_to_adapt[key][0].lstrip(" ").lower() in ["none", "null"] for key in value_to_adapt):
                return {
                    k.rstrip(" "): adapt_to_type(previous_value.get(k, None), v[0].lstrip(" "), v[1], param,
                                                 )
                    for k, v in value_to_adapt.items()
                }
            raise TypeError(f"New value for dict in '{param}' is inconsistent with old "
                            f"value '{previous_value}'. If the new value is correct, "
                            "please force the type of the new elements in the dict so "
                            "type inference can be done.")
        if all(value_to_adapt[key][1] is not None or value_to_adapt[key][0].lstrip(" ").lower() in ["none", "null"]
               for key in value_to_adapt):
            return {
                k.rstrip(" "): adapt_to_type(None, v[0].lstrip(" "), v[1], param)
                for k, v in value_to_adapt.items()
            }
        raise TypeError(f"Since the previous value for '{param}' was not a dict, "
                        "none of its keys' values can be inferred. Please force the "
                        "type of all elements in the new value's dict.")

    if (isinstance(previous_value, int) and not isinstance(previous_value, bool) and force is None) or force == "int":
        try:
            parsed = int(scalar_parsed)
        except ValueError:
            parsed = float(scalar_parsed)
        return int(parsed) if force == "int" else parsed

    if (isinstance(previous_value, float) and force is None) or force == "float":
        return float(scalar_parsed)

    if (isinstance(previous_value, bool) and force is None) or force == "bool":
        if scalar_parsed.strip(" ").lower() in ["y", "yes", "true", "1"]:
            return True
        if scalar_parsed.strip(" ").lower() in ["n", "no", "false", "0"]:
            return False
        raise ValueError("Boolean parameters can only be replaced with (non case sensitive)"
                         " : \n"
                         "- to get a True value : y, yes, true, 1\n"
                         "- to get a False value : n, no, false, 0")


def add_to_csv(csv_path: str, name: str, value: Any, step: int) -> None:
    """
    Adds a logged value to the csv containing previously logged values
    :param csv_path: path to the csv containing the logged values
    :param name: name of the value to log
    :param value: value of the value to log
    :param step: step for which to log the value
    """
    if os.path.isfile(csv_path):
        with open(csv_path, encoding='utf-8') as csv_file:
            data = csv_file.readlines()
            steps = [int(d.split(",")[0]) for d in data[1:]]
            metrics = [d.strip("\n") for d in data[0].split(",")[1:]]
            values = [[d.split(",")[1 + i].strip("\n") if d.split(",")[1 + i] else ""
                       for d in data[1:]] for i in range(len(metrics))]
    else:
        steps = []
        metrics = []
        values = []
    if name not in metrics:
        metrics.append(name)
        values.append(["" for _ in range(len(steps))])
    if step not in steps:
        index = bisect(steps, step)
        steps.insert(index, step)
        for i, metric in enumerate(metrics):
            values[i].insert(index, str(value) if metric == name else "")
    else:
        values[metrics.index(name)][steps.index(step)] = str(value)

    with open(csv_path, 'w', encoding='utf-8') as csv_file:
        csv_file.write(",".join(["steps"] + metrics) + "\n")
        for index, step_to_log in enumerate(steps):
            data = [str(step_to_log)] + [v[index] for v in values]
            csv_file.write(",".join(data) + "\n")


def are_same_sub_configs(first, second) -> bool:
    """
    Checks if two sub-configs have identical nesting hierarchies.
    :param first: first sub-config to check
    :param second: second sub-config to check
    :return: result of the check
    """
    if first.get_name() != second.get_name():
        return False
    nh1, nh2 = first.get_nesting_hierarchy(), second.get_nesting_hierarchy()
    return len(nh1) == len(nh2) and all(nh1[i] == nh2[i] for i in range(len(nh1)))


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


def escape_symbols(string_to_escape: str, symbols: Union[List[str], str]) -> str:
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


def format_str(config_path_or_dictionary: ConfigDeclarator, size: int = 200) -> str:
    """
    Format helper to shorten configs to display depending on logging level.
    :param config_path_or_dictionary: config to display
    :param size: number of characters allowed to display
    :return: the formatted string
    """
    to_return = str(config_path_or_dictionary)
    if YAECS_LOGGER.level >= logging.INFO:
        return to_return if len(to_return) < size else f"{to_return[:size//2 - 3]} [...] {to_return[-size//2 - 3:]}"
    return to_return


def get_param_as_parsable_string(param: Any, in_iterable: bool = False, ignore_unknown_types: bool = False) -> str:
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
    if param is None:
        return "none"
    if isinstance(param, list):
        to_ret = [get_param_as_parsable_string(i, True) for i in param]
        return f"[{','.join(to_ret)}] !list"
    if isinstance(param, dict):
        to_ret = [f"{k}:{get_param_as_parsable_string(v, True)}" for k, v in param.items()]
        return "{" + ",".join(to_ret) + "} !dict"
    if isinstance(param, (int, float)) and not isinstance(param, bool):
        type_forcing = "float"
    elif isinstance(param, str):
        type_forcing = "str"
    elif isinstance(param, bool):
        type_forcing = "bool"
    elif ignore_unknown_types:
        YAECS_LOGGER.warning(f"WARNING: parameter value '{param}' will not have its type enforced because it is not in "
                             f"[int, float, str, bool].")
        type_forcing = ""
    else:
        raise TypeError(f"Parameter value '{param}' will not have its type enforced "
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


def hook(hook_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator used to keep track of registered params.
    :param hook_name: name of the hook to store
    :return: decorated function
    """
    def decorator_hook(func: Callable) -> Callable:
        func.__name__ = f"yaecs_config_hook__{hook_name}__{func.__name__}"

        @functools.wraps(func)
        def wrapper_hook(self, *args, **kwargs):
            value = func(self, *args, **kwargs)
            self.add_currently_processed_param_as_hook(hook_name=hook_name)
            return value

        return wrapper_hook
    if "__" in hook_name:
        raise RuntimeError(f"Invalid hook name {hook_name} : '__' is not allowed in hook names.")
    return decorator_hook


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


def lazy_import(name):
    """
    Imports a module in such a way that it is only loaded in memory when it is actually used.
    Implementation from https://docs.python.org/3/library/importlib.html#implementing-lazy-imports.
    :param name: name of the module to load
    :return: the loaded module
    """
    spec = importlib.util.find_spec(name)
    if not spec:
        return None
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def new_print(*args, sep=" ", end="", file=None, **keywords):
    """
    Replaces the builtin print function during an experiment run such that printed messages are also logged. Please note
    that the default file (None) logs to logging's root logger which will always go to the next line after each message.
    Therefore, the "end" param does not replace '\n' as usual, but adds a suffix after the message and before the '\n'.
    :param args: objects to print
    :param sep: how to separate the different objects
    :param end: suffix to add after the message
    :param file: file to print to, defaults to a logging to logging's root logger with level logging.INFO
    :param keywords: might contain 'flush', in which case raise an error
    :raises TypeError: when the keyword arguments contain 'flush'
    """
    if not os.getenv('NODE_RANK'):  # do not print if in a pytorch-lightning spawned process
        if "flush" in keywords:
            raise TypeError("Because yaecs uses logging.info to log messages logged via the print function, the 'flush'"
                            " parameter is not supported for the print function within your main.")
        message = sep.join([str(a) for a in args]) + end.strip()
        if message.strip():
            if file is not None and file is not sys.stdout:
                file.write(message)
            logging.getLogger("yaecs.print_catcher").info(message)


def parse_type(string_to_process: str) -> TypeHint:
    """
    Parses an input string containing the type info for a parameter into a complex type as understood by the
    Configuration.check_type function.
    :param string_to_process: string to parse for type
    :return: complex type
    """
    if not string_to_process:
        raise ValueError("Invalid type hint : empty type hint.")
    string = string_to_process.lower()
    types = {"none": None, "int": int, "float": float, "bool": bool, "str": str, "list": list, "dict": dict}
    mapping_starts = {"(": "tuple", "[": "list", "d": "set"}
    mapping_ends = {")": "tuple", "]": "list", "/d": "set"}
    to_return = ("root", [])
    current = []
    current_types = []
    i = 0

    def _get_sub_list(lists, path):
        list_to_get = lists
        for element in path:
            list_to_get = list_to_get[1][element]
        return list_to_get[1]

    def _increment(lists, path, value_to_add, value_type):
        list_to_incr = _get_sub_list(lists, path)
        list_to_incr.append((value_type, value_to_add))

    def _enter_list(lists, path, path_types, path_type):
        list_to_enter = _get_sub_list(lists, path)
        path.append(len(list_to_enter)-1)
        path_types.append(path_type)

    while i < len(string):
        to_find = True
        for key, value in types.items():
            if to_find and string[i] == key[0]:
                if string[i:i+len(key)] == key:
                    to_find = False
                    _increment(to_return, current, value, "type")
                    i += len(key)
                elif string[i] == "d":
                    pass
                else:
                    raise ValueError(f"Parsing error : unknown type starting from position {i} : "
                                     f"{string_to_process}.")
        if to_find and string[i] == ",":
            to_find = False
            i += 1
        for key, value in mapping_starts.items():
            if to_find and string[i] == key[0]:
                if string[i:i+len(key)] == key:
                    to_find = False
                    _increment(to_return, current, [], value)
                    _enter_list(to_return, current, current_types, value)
                    i += len(key)
                else:
                    raise ValueError(f"Parsing error : unknown mapping type starting from position {i} : "
                                     f"{string_to_process}.")
        for key, value in mapping_ends.items():
            if to_find and string[i] == key[0]:
                if string[i:i+len(key)] == key:
                    if current_types[-1] != value:
                        raise ValueError(f"Parsing error : did not expect symbol '{key}' at position {i} : "
                                         f"{string_to_process}")
                    to_find = False
                    current = current[:-1]
                    current_types = current_types[:-1]
                    i += len(key)
                else:
                    raise ValueError(f"Parsing error : unknown mapping type ending at position {i} : "
                                     f"{string_to_process}.")
        if to_find:
            raise ValueError(f"Unknown token at position {i} : {string_to_process}")

    if current:
        raise ValueError(f"Parsing error : unclosed brackets : {string_to_process}")

    def _struc_to_type(structured_list):
        list_to_consider = structured_list[1]
        if len(list_to_consider) != 1:
            raise ValueError("Parsing error : a source type must contain exactly 1 type (simple or complex) : "
                             f"{string_to_process}")
        if list_to_consider[0][0] == "type":
            return list_to_consider[0][1]
        if list_to_consider[0][0] == "tuple":
            if not list_to_consider[0][1]:
                raise ValueError(f"Parsing error : empty tuples are not allowed : {string_to_process}")
            return tuple(_struc_to_type(("", [j])) for j in list_to_consider[0][1])
        if list_to_consider[0][0] == "list":
            if not list_to_consider[0][1]:
                raise ValueError(f"Parsing error : empty lists are not allowed : {string_to_process}")
            return list(_struc_to_type(("", [j])) for j in list_to_consider[0][1])
        if list_to_consider[0][0] == "set":
            return {_struc_to_type(("", list_to_consider[0][1]))}
        return None

    return _struc_to_type(to_return)


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


def update_state(state_descriptor: str) -> Callable[[Callable], Callable]:
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
            first_arg = (args[0] if args else (kwargs[list(kwargs.keys())[0]] if kwargs else None))
            self._state.append(  # pylint: disable=protected-access
                state_to_append + f";arg0={first_arg}")  # first arg of function call
            value = func(self, *args, **kwargs)
            self._state.pop(-1)  # pylint: disable=protected-access
            return value

        return wrapper_update_state

    return decorator_update_state


class TqdmLogFormatter:
    """
    Context setting formatters used in logging handlers for tqdm bars. See https://github.com/tqdm/tqdm/issues/313
    """

    def __init__(self, logger):
        self._logger = logger
        self.__original_formatters = None

    def __enter__(self):
        self.__original_formatters = list()

        for handler in self._logger.handlers:
            self.__original_formatters.append(handler.formatter)

            handler.terminator = ''
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)

        return self._logger

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for handler, formatter in zip(self._logger.handlers, self.__original_formatters):
            handler.terminator = '\n'
            handler.setFormatter(formatter)


class TqdmLogger(io.StringIO):
    """File to use in tqdm to make it log its bars to a logger. See https://github.com/tqdm/tqdm/issues/313"""

    def __init__(self, logger):
        super().__init__()

        self._logger = logger

    def write(self, buffer):
        with TqdmLogFormatter(self._logger) as logger:
            logger.info(buffer)

    def flush(self):
        pass


YAML_EXPRESSIONS = {
    "null": re.compile(r'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
    "bool": re.compile(r'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
    "int": re.compile(r'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
    "float": re.compile(r'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X)
}