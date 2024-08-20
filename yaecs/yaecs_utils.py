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
from functools import partial
import io
import logging
import re
import sys
from collections.abc import Mapping
from enum import Enum
from numbers import Real
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)
ConfigDeclarator = Union[str, dict]
ConfigInput = Union[List[ConfigDeclarator], ConfigDeclarator]
Hooks = Union[Dict[str, List[str]], List[str]]
ProcessingFunction = Union[Callable[[Any], Any], str]
ProcessingOrder = Union[Real, 'Priority']
ProcessingFunctions = Union[ProcessingFunction, Tuple[Union[ProcessingFunction, ProcessingOrder]]]
TypeHint = Union[type, tuple, list, dict, set, int]
VariationDeclarator = Union[List[ConfigDeclarator], Dict[str, ConfigDeclarator]]
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
TYPE_HINT_MAPPING_STARTS = {"tuple_0": "(", "tuple_1": "union[", "nonetuple": "optional[",
                            "list_0": "[", "list_1": "list[",
                            "set_0": "d", "set_1": "dict["}
TYPE_HINT_MAPPING_ENDS = {"tuple_0": ")", "tuple_1": "]", "nonetuple": "]",
                          "list_0": "]", "list_1": "]",
                          "set_0": "/d", "set_1": "]"}
TYPE_HINT_SIMPLE_TYPES = {"none": None, "int": int, "float": float, "bool": bool, "str": str, "list": list,
                          "dict": dict, "any": 0}


class NoValue:
    """ Used to represent a default value not modified by the user. """


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


def assign_order(order: ProcessingOrder = Priority.INDIFFERENT) -> Callable[[Callable], Callable]:
    """
    Decorator used to give an order to a processing function. If several processing functions would be called at a given
    step, they are called in increasing order.

    :param order: order to give the function
    :return: decorated function
    """
    def decorator_order(func: Callable) -> Callable:
        if not hasattr(func, "yaecs_metadata"):
            set_function_attribute(func, "yaecs_metadata", {})
        func.yaecs_metadata["order"] = order
        return func

    return decorator_order


def assign_yaml_tag(processor_tag: str, processor_type: str,
                    replacement_type_hint: str = "Any") -> Callable[[Callable], Callable]:
    """
    Decorator used to mark a function as a processor added automatically as pre or post processing function (as
    defined by processor_type) to parameters tagged with !<processor_tag>. Their type hint will be replaced by
    the type hint defined as replacement_type_hint if this is the first processing function to be called on the
    parameter.

    :param processor_tag: tag to use to mark a param in YAML as auto-processed by this function
    :param processor_type: 'pre' or 'post', type of processing function to add
    :param replacement_type_hint: type hint to use for any param tagged with this auto-processor
    :return: decorated function
    """
    def decorator_tag_assignment(func: Callable) -> Callable:
        if "yaecs_metadata" not in func.__dict__:
            func.__dict__["yaecs_metadata"] = {}
        func.__dict__["yaecs_metadata"].update({
            "tag": processor_tag,
            "name": func.__name__,
            "processing_type": processor_type,
            "input_type": replacement_type_hint,
        })
        return func

    return decorator_tag_assignment


def check_type(type_or_types: TypeHint, name: Optional[str] = None) -> Callable:
    """
    Returns a processing function that checks for given type. Can be used for example with the following line in a
    parameters post-processing dict:
    "parameter_that_should_be_int": check_type(int)

    * The type can be any of None, bool, int, float, str, dict, list. The value 0 instead means no type check.
    * Unions are denoted by tuples of types.
    * You can specify the type of the elements of your lists by using a list of types. This list should contain
        either one type (in which case the list is expected to only contain elements of that type) or as many types as
        there are elements in the list (in which case each element is tested with the corresponding type)
    * You can specify the type of the elements of your dicts by using a dict or a set of types. If you use a set, it
        can only contain one type (in which case the dict is expected to contain only values of that type).
        If you use a dict of types, the keys used in that dict that match the keys in the parameter will be checked
        using the values as types.

    :param type_or_types: type for which to create the function
    :param name: name of the parameter to check
    :return: the processing function
    """
    def _check_type(value: Any, type_to_check: TypeHint, original_type: TypeHint, name: str) -> Any:
        def _wrong_type() -> None:
            is_full = original_type == type_to_check
            if name is None:
                header = f"{'Value' if is_full else 'Part of value'} '{value}'"
            else:
                header = f"{'Parameter' if is_full else 'Part of parameter'} '{name}' (value : {value})"
            checked_type = type(type_to_check) if isinstance(type_to_check, (list, dict, set)) else type_to_check
            raise ValueError(f"{header} has incorrect type '{type(value)}'. Expected '{checked_type}'.")

        if isinstance(type_to_check, tuple):
            if not type_to_check:
                raise ValueError("Undefined behaviour for empty tuples. Maybe you meant to use an empty list or dict ?")
            fails = True
            for to_check in type_to_check:
                try:
                    _check_type(value, to_check, original_type, name)
                except ValueError:
                    pass
                else:
                    fails = False
            if fails:
                _wrong_type()

        elif isinstance(type_to_check, list):
            if not isinstance(value, list):
                _wrong_type()
            if len(type_to_check) > 1:
                if len(type_to_check) != len(value):
                    raise ValueError("When providing a list of types, its length must be one or match the length of"
                                     " the value.")
                for v_to_check, t_to_check in zip(value, type_to_check):
                    _check_type(v_to_check, t_to_check, original_type, name)
            else:
                types = type_to_check[0] if type_to_check else 0
                for i in value:
                    _check_type(i, types, original_type, name)

        elif isinstance(type_to_check, dict):
            if not isinstance(value, dict):
                _wrong_type()
            if not type_to_check:
                raise ValueError("Undefined behaviour for empty dicts. Maybe you meant to use an empty list or "
                                 "{\"type\": ...} ?")
            if len(type_to_check) > 1:
                raise ValueError("When providing a dict of types, its length must be 1. Maybe you meant to use a"
                                 " tuple ?")
            for i in value:
                _check_type(value[i], type_to_check[list(type_to_check.keys())[0]], original_type, name)

        elif type_to_check != 0 and type_to_check is not None and not isinstance(value, type_to_check):
            if not (type_to_check is float and isinstance(value, int)):
                _wrong_type()

        elif type_to_check is None and value is not None:
            _wrong_type()
        return value

    return partial(_check_type, type_to_check=type_or_types, original_type=type_or_types, name=name)


def compare_string_pattern(name: str, pattern: str) -> bool:
    """
    Returns True when string 'name' matches string 'pattern', with the '*' character matching any number of characters.

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
    if YAECS_LOGGER.getEffectiveLevel() >= logging.INFO:
        return to_return if len(to_return) < size else f"{to_return[:size//2 - 3]} [...] {to_return[-size//2 - 3:]}"
    return to_return


def get_config_from_argv(pattern: str, fallback: Optional[ConfigInput] = None) -> List[str]:
    """
    Get paths to config files from the command line arguments.

    :param pattern: pattern to detect in sys.argv
    :param fallback: fallback value if pattern is not detected in sys.argv
    :return: the configuration
    """
    pattern_index = None
    for index, element in enumerate(sys.argv):
        if element.split("=", 1)[0] == pattern:
            pattern_index = index
    if pattern_index is not None:
        # Aggregate all CLI chunks until the next flag
        configs = []
        if "=" in sys.argv[pattern_index]:
            configs.append(sys.argv[pattern_index].split("=", 1)[1])
        for element in sys.argv[pattern_index + 1:]:
            if element.startswith("--"):
                break
            configs.append(element)
        fallback = [cfg.strip(" ") for cfg in " ".join(configs).strip().strip("[]").split(",")]
    if fallback is None:
        raise TypeError(f"The pattern '{pattern}' was not detected in sys.argv.")
    if not isinstance(fallback, list):
        fallback = [fallback]
    return [cfg for cfg in fallback if cfg]


def get_quasi_bash_sys_argv(string_to_convert: str) -> List[str]:
    """
    If a string is passed as input, process it as sys.argv would in a bash shell
    It gives exactly what sys.argv would if the script was used in a bash terminal, except that escaped '!' in quotes
    are properly escaped and the escape symbol is removed, contrary to bash (which would keep the escape for some
    obscure reason).

    :param string_to_convert: string to process
    :return: the list of strings that sys.argv would give
    """
    converted_list = [""]
    in_quotes = ""
    escaped = False
    for index, char in enumerate(string_to_convert):
        if char == "\\" and not escaped and (not in_quotes or string_to_convert[index+1] == "!"):
            escaped = True
        elif char in ['"', "'"] and not escaped:
            if not in_quotes:
                in_quotes = char
            elif in_quotes == char:
                in_quotes = ""
            else:
                converted_list[-1] += char
        elif char == " " and not in_quotes and converted_list[-1] and not escaped:
            converted_list.append("")
        elif char == "!" and not escaped:
            raise ValueError("Bash would say 'event not found', please escape the '!' character.")
        else:
            escaped = False
            converted_list[-1] += char
    if in_quotes:
        raise ValueError(f"Could not parse args : open quotations were left unclosed : {in_quotes}.")
    return converted_list


def get_order(func: Callable, default: Optional[ProcessingOrder] = Priority.INDIFFERENT) -> Optional[ProcessingOrder]:
    """
    If input function has an "order" attribute, returns it. Otherwise, returns the specified "default" value.

    :param func: function to get the order of
    :param default: default value to return if no order is found
    :return: the order value
    """
    if not hasattr(func, "yaecs_metadata") or "order" not in func.yaecs_metadata:
        return default
    return func.yaecs_metadata["order"]


def get_param_as_parsable_string(param: Any) -> str:
    """
    Gets given value as a string that can be parsed by the Configuration. The string is formatted so as to be either
    used as is in a bash shell (ie., python main.py --param_name string), or with merge_from_command_line (ie.,
    config.merge_from_command_line(f"--param_name {string}")

    :param param: parameter value to be returned as a valid string
    :raises TypeError: if the type of 'param' cannot be enforced
    :return: string usable in the command line to reproduce the value of param
    """
    container_separator = ",\\ "
    if param is None:
        return "null"
    if isinstance(param, list):
        parsable_strings = [get_param_as_parsable_string(i) for i in param]
        return f"[{container_separator.join(parsable_strings)}]"
    if isinstance(param, dict):
        parsable_strings = [f"{key}:\\ {get_param_as_parsable_string(value)}" for key, value in param.items()]
        return "{" + container_separator.join(parsable_strings) + "}"
    if isinstance(param, (int, float)) and not isinstance(param, bool):
        return format(Context(prec=20).create_decimal(repr(param)), 'f')
    if isinstance(param, str):
        string = escape_symbols(param, ['"', "'", "!", " "])
        return escape_symbols(f'"{string}"', ['"'])
    if isinstance(param, bool):
        return str(param).lower()
    raise TypeError("Provided value's type is not YAML-compatible (None, str, bool, int, float, list and dict work).")


def hook(hook_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator used to keep track of registered params.

    :param hook_name: name of the hook to store
    :return: decorated function
    """
    def decorator_hook(func: Callable) -> Callable:
        if not hasattr(func, "yaecs_metadata"):
            set_function_attribute(func, "yaecs_metadata", {})
        existing_hooks = func.yaecs_metadata["hooks"] if "hooks" in func.yaecs_metadata else []
        existing_hooks += [hook_name] if hook_name not in existing_hooks else []
        func.yaecs_metadata["hooks"] = existing_hooks

        @functools.wraps(func)
        def wrapper_hook(self, *args, **kwargs):
            value = func(self, *args, **kwargs)
            self.add_currently_processed_param_as_hook(hook_name=hook_name)
            return value

        if hasattr(func, "yaecs_metadata"):
            set_function_attribute(wrapper_hook, "yaecs_metadata", func.yaecs_metadata)
        return wrapper_hook
    return decorator_hook


def is_dict_type_hint(type_hint_representer: str) -> bool:
    """
    Returns True if the type hint is a dict.

    :param type_hint_representer: type hint to check
    :return: result of the test
    """
    hint = type_hint_representer.lower().strip(" ")
    if hint == "dict":
        return True
    for fragment, pattern in TYPE_HINT_MAPPING_STARTS.items():
        if fragment.startswith("set") and hint.startswith(pattern):
            if hint.endswith(TYPE_HINT_MAPPING_ENDS[fragment]):
                return True
    return False


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


def is_config_in_argv(pattern: str) -> bool:
    """
    Returns True if the pattern is found in sys.argv.

    :param pattern: pattern to detect in sys.argv
    :return: result of the test
    """
    try:
        _ = get_config_from_argv(pattern)
        return True
    except TypeError:
        return False


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
        for type_name, fragment in TYPE_HINT_MAPPING_STARTS.items():
            if to_find and string[i:i+len(fragment)] == fragment:
                if not (fragment == "d" and string[i:i+len("dict")] == "dict"):
                    to_find = False
                    _increment(to_return, current, [], type_name)
                    _enter_list(to_return, current, current_types, type_name)
                    i += len(fragment)
        # Try to detect simple types
        for fragment, type_name in TYPE_HINT_SIMPLE_TYPES.items():
            if to_find and string[i:i+len(fragment)] == fragment:
                to_find = False
                _increment(to_return, current, type_name, "type")
                i += len(fragment)
        # Try to detect commas
        if to_find and string[i] == ",":
            to_find = False
            i += 1
        # Try to detect ends of mappings
        for type_name, fragment in TYPE_HINT_MAPPING_ENDS.items():
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


def set_function_attribute(func: Callable, attribute_name: str, value: Any) -> None:
    """
    Adds an attribute to a function or method object.

    :param func: function to add the attribute to
    :param attribute_name: name of the attribute to add
    :param value: value of the attribute
    """
    try:
        setattr(func, attribute_name, value)
    except AttributeError:  # used if func is a method, to modify the underlying function
        setattr(func.__func__, attribute_name, value)


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
            with UpdateState(state_to_append + f";arg0={first_arg}", self):
                value = func(self, *args, **kwargs)
            return value

        return wrapper_update_state

    return decorator_update_state


class UpdateState:
    """
    Context manager used to update the state of a Configuration object.
    """

    def __init__(self, state_descriptor: str, config_object: 'Configuration'):
        self._state_descriptor = state_descriptor
        self._config_object = config_object

    def __enter__(self):
        self._config_object._state.append(  # pylint: disable=protected-access
            self._state_descriptor)  # first arg of function call

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._config_object._state.pop(-1)  # pylint: disable=protected-access
