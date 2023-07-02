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
from decimal import Context
import functools
import importlib.util
import io
import logging
import os
import re
import sys
from bisect import bisect
from collections.abc import Mapping
from enum import Enum
from numbers import Real
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Union

YAECS_LOGGER = logging.getLogger(__name__)
ConfigDeclarator = Union[str, dict]
ConfigInput = Union[List[ConfigDeclarator], ConfigDeclarator]
Hooks = Union[Dict[str, List[str]], List[str]]
TypeHint = Union[type, tuple, list, dict, set, int]
VariationDeclarator = Union[List[ConfigDeclarator], Dict[str, ConfigDeclarator]]


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


def assign_order(order: Union[Real, 'Priority'] = 0) -> Callable[[Callable], Callable]:
    """
    Decorator used to give an order to a processing function. If several processing functions would be called at a given
    step, they are called in increasing order.

    :param order: order to give the function
    :return: decorated function
    """
    def decorator_order(func: Callable) -> Callable:
        set_function_attribute(func, "order", order)
        return func

    return decorator_order


def assign_yaml_tag(processor_tag: str, processor_type: str,
                    replacement_type_hint: str = "Any") -> Callable[[Callable], Callable]:
    """
    Decorator used to mark a function as a processor added automatically as pre or post processing function (as
    defined by processor_type) to parameters tagged with !type:<processor_tag>. Their type hint will be replaced by
    the type hint defined as replacement_type_hint.

    :param processor_tag: tag to use to mark a param in YAML as auto-processed by this function
    :param processor_type: 'pre' or 'post', type of processing function to add
    :param replacement_type_hint: type hint to use for any param tagged with this auto-processor
    :return: decorated function
    """
    def decorator_tag_assignment(func: Callable) -> Callable:
        func.__dict__["assigned_yaml_tag"] = (processor_tag, processor_type, replacement_type_hint)
        return func

    return decorator_tag_assignment


def compare_string_pattern(name: str, pattern: str) -> bool:
    """
    Returns True when string 'name' matches string 'pattern',
    with the '*' character matching any number of characters.

    :param name: name to compare
    :param pattern: pattern to match
    :return: result of comparison
    """
    pattern = pattern.strip(" ").split("*")
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


def compose(*functions: Callable) -> Callable:
    """
    Returns the composition of the functions given as argument. Functions are applied from left to right, ie :
    compose(f, g, h)(x) = h(g(f(x))).

    :param functions: all functions to compose, applied from left to right
    :return: the composed function
    """
    def compose_2(function_1, function_2):
        def composed(*args, **kwargs):
            return function_2(function_1(*args, **kwargs))
        orders = []
        for func in [function_1, function_2]:
            if hasattr(func, "order"):
                orders.append(func.order)
        if orders:
            set_function_attribute(composed, "order", max(orders))
        hooks = []
        for func in [function_1, function_2]:
            if func.__name__.startswith("yaecs_config_hook__"):
                hooks += func.__name__.split("__")[1].split(",")
        if hooks:
            composed.__name__ = f"yaecs_config_hook__{','.join(list(set(hooks)))}__composed"
        return composed
    return functools.reduce(compose_2, functions, lambda x: x)


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


def get_config_from_argv(pattern: str, fallback: Optional[ConfigInput] = None) -> List[str]:
    """
    Get a configuration from the command line arguments.

    :param pattern: pattern to detect in sys.argv
    :param fallback: fallback value if pattern is not detected in sys.argv
    :return: the configuration
    """
    if pattern not in sys.argv and fallback is None:
        raise TypeError(f"The pattern '{pattern}' was not detected in sys.argv.")
    if pattern in sys.argv:
        fallback = [cfg.strip(" ") for cfg in sys.argv[sys.argv.index(pattern) + 1].strip("[]").split(",")]
    if not isinstance(fallback, list):
        fallback = [fallback]
    return fallback


def get_order(func: Callable) -> Union[Real, 'Priority']:
    """
    If input function has an "order" attribute, returns it. Otherwise, returns Priority.INDIFFERENT.

    :param func: function to get the order of
    :return: the order value
    """
    return getattr(func, "order", Priority.INDIFFERENT)


def get_param_as_parsable_string(param: Any) -> str:
    """
    Gets given value as a string that can be parsed by the Configuration.

    :param param: parameter value to be returned as a valid string
    :param in_iterable: used only for bookkeeping in recursive calls
    :param ignore_unknown_types: how to treat types that cannot be parsed by the Configuration
    :raises TypeError: if the type of 'param' cannot be enforced
    :return: string usable in the command line to reproduce the value of param
    """
    if param is None:
        return "null"
    if isinstance(param, list):
        parsable_strings = [get_param_as_parsable_string(i) for i in param]
        return f"[{','.join(parsable_strings)}]"
    if isinstance(param, dict):
        parsable_strings = [f"{key}:{get_param_as_parsable_string(value)}" for key, value in param.items()]
        return "{" + ",".join(parsable_strings) + "}"
    if isinstance(param, (int, float)) and not isinstance(param, bool):
        return format(Context(prec=20).create_decimal(repr(param)), 'f')
    elif isinstance(param, str):
        return f"\"{param}\""
    elif isinstance(param, bool):
        return str(param).lower()
    else:
        raise TypeError(f"Provided value's type is not YAML-compatible (None, str, bool, int, float, list and dict work).")


def hook(hook_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator used to keep track of registered params.

    :param hook_name: name of the hook to store
    :return: decorated function
    """
    def decorator_hook(func: Callable) -> Callable:
        if func.__name__.startswith("yaecs_config_hook__"):
            hooks = func.__name__.split("__")[1].split(",")
            if hook_name in hooks:
                hook_name_in_func_name = ",".join(hooks)
            else:
                hook_name_in_func_name = ",".join(hooks + [hook_name])
            original_name = "__".join(func.__name__.split("__")[2:])
        else:
            hook_name_in_func_name = hook_name
            original_name = func.__name__
        func.__name__ = f"yaecs_config_hook__{hook_name_in_func_name}__{original_name}"

        @functools.wraps(func)
        def wrapper_hook(self, *args, **kwargs):
            value = func(self, *args, **kwargs)
            self.add_currently_processed_param_as_hook(hook_name=hook_name)
            return value

        for function_attribute in ["order", "assigned_yaml_tag"]:
            if hasattr(func, function_attribute):
                set_function_attribute(wrapper_hook, function_attribute, getattr(func, function_attribute))
        return wrapper_hook
    for invalid_pattern in ["__", ","]:
        if invalid_pattern in hook_name:
            raise RuntimeError(f"Invalid hook name {hook_name} : '{invalid_pattern}' is not allowed in hook names.")
    return decorator_hook


def is_type_valid(value: Any, config_class: type) -> bool:
    """
    Checks whether input 'value' can be saved in a YAML file by Configuration's YAML Dumper.

    :param value: value to check the type of
    :param config_class: Configuration class, which must be passed as argument to avoid circular imports :(
    :return: result of the test
    """
    if isinstance(value, list):
        return all(is_type_valid(i, config_class) for i in value)
    if isinstance(value, (Mapping, config_class)):
        return all(is_type_valid(i, config_class) for i in value.values())
    return isinstance(value, (int, float, str)) or value is None


def lazy_import(name: str) -> ModuleType:
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


def new_print(*args, sep: str = " ", end: str = "", file: io.TextIOWrapper = None, **keywords) -> None:
    """
    Replaces the builtin print function during an experiment run such that printed messages are also logged. Please note
    that the default file (None) logs to logging's root logger which will always go to the next line after each message.
    Therefore, the 'end' param does not replace \\n as usual, but adds a suffix after the message and before the \\n.

    :param args: objects to print
    :param sep: how to separate the different objects
    :param end: suffix to add after the message
    :param file: file to print to, defaults to a logging to logging's root logger with level logging.INFO
    :param keywords: might contain 'flush', in which case raise an error
    :raises TypeError: when the keyword arguments contain 'flush'
    """
    if not os.getenv('NODE_RANK'):  # do not print if in a pytorch-lightning spawned process
        if "flush" in keywords:
            raise TypeError("Because YAECS uses logging.info to log messages logged via the print function, the 'flush'"
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
    mapping_starts = {"tuple_0": "(", "tuple_1": "union[", "nonetuple": "optional[",
                      "list_0": "[", "list_1": "list[",
                      "set_0": "d", "set_1": "dict["}
    types = {"none": None, "int": int, "float": float, "bool": bool, "str": str, "list": list, "dict": dict, "any": 0}
    mapping_ends = {"tuple_0": ")", "tuple_1": "]", "nonetuple": "]",
                    "list_0": "]", "list_1": "]",
                    "set_0": "/d", "set_1": "]"}
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
        # Try to detect starts of mappings
        for type_name, fragment in mapping_starts.items():
            if to_find and string[i:i+len(fragment)] == fragment:
                if not (fragment == "d" and string[i:i+len("dict")] == "dict"):
                    to_find = False
                    _increment(to_return, current, [], type_name)
                    _enter_list(to_return, current, current_types, type_name)
                    i += len(fragment)
        # Try to detect simple types
        for fragment, type_name in types.items():
            if to_find and string[i:i+len(fragment)] == fragment:
                to_find = False
                _increment(to_return, current, type_name, "type")
                i += len(fragment)
        # Try to detect commas
        if to_find and string[i] == ",":
            to_find = False
            i += 1
        # Try to detect ends of mappings
        for type_name, fragment in mapping_ends.items():
            if to_find and string[i:i+len(fragment)] == fragment and current_types[-1] == type_name:
                to_find = False
                current = current[:-1]
                current_types = current_types[:-1]
                i += len(fragment)
        if to_find:
            raise ValueError(f"Unexpected token at position {i} : {string_to_process}")

    if current:
        raise ValueError(f"Parsing error : unclosed brackets : {string_to_process}")

    def _struc_to_type(structured_list):
        list_to_consider = structured_list[1]
        if len(list_to_consider) != 1:
            raise ValueError("Parsing error : a source type must contain exactly 1 type (simple or complex) : "
                             f"{string_to_process}")
        if list_to_consider[0][0].startswith("type"):
            return list_to_consider[0][1]
        if list_to_consider[0][0].startswith("tuple"):
            if not list_to_consider[0][1]:
                raise ValueError(f"Parsing error : empty tuples are not allowed : {string_to_process}")
            return tuple(_struc_to_type(("", [j])) for j in list_to_consider[0][1])
        if list_to_consider[0][0].startswith("nonetuple"):
            if not list_to_consider[0][1]:
                raise ValueError(f"Parsing error : empty tuples are not allowed : {string_to_process}")
            return (None,) + tuple(_struc_to_type(("", [j])) for j in list_to_consider[0][1])
        if list_to_consider[0][0].startswith("list"):
            if not list_to_consider[0][1]:
                raise ValueError(f"Parsing error : empty lists are not allowed : {string_to_process}")
            return list(_struc_to_type(("", [j])) for j in list_to_consider[0][1])
        if list_to_consider[0][0].startswith("set"):
            return {"type": _struc_to_type(("", list_to_consider[0][1]))}
        return None

    return _struc_to_type(to_return)


class Priority(Enum):
    """ Define priority levels which can be used to qualify when a processing function should be performed. """
    ALWAYS_FIRST = -20
    OFTEN_FIRST = -10
    INDIFFERENT = 0
    SITUATIONAL = 0
    OFTEN_LAST = 10
    ALWAYS_LAST = 20

    def __hash__(self):
        return hash(self.value)

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        if isinstance(other, Real):
            return self.value > other
        if isinstance(other, str):
            return self.value > getattr(self.__class__, other)
        return NotImplemented

    def __rgt__(self, other):
        return self < other

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        if isinstance(other, Real):
            return self.value < other
        if isinstance(other, str):
            return self.value < getattr(self.__class__, other)
        return NotImplemented

    def __rlt__(self, other):
        return self > other

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        if isinstance(other, Real):
            return self.value >= other
        if isinstance(other, str):
            return self.value >= getattr(self.__class__, other)
        return NotImplemented

    def __rge__(self, other):
        return self <= other

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        if isinstance(other, Real):
            return self.value <= other
        if isinstance(other, str):
            return self.value <= getattr(self.__class__, other)
        return NotImplemented

    def __rle__(self, other):
        return self >= other

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        if isinstance(other, Real):
            return self.value == other
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __req__(self, other):
        return self == other


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


def set_function_attribute(func: Callable, attribute_name: str, value: Any) -> None:
    """
    Adds an attribute to a function object.

    :param func: function to add the attribute to
    :param attribute_name: name of the attribute to add
    :param value: value of the attribute
    """
    if attribute_name == "__name__":
        func.__name__ = value
    else:
        try:
            func.__dict__[attribute_name] = value
        except AttributeError:
            setattr(func, attribute_name, value)


def update_state(state_descriptor: str) -> Callable[[Callable], Callable]:
    """
    Decorator used to store useful information in Configuration._state when using some recursive functions. Kind of a
    hack, but very useful to keep track of the loading state and also to debug.

    :param state_descriptor: string indicating what to store in Configuration._state
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
