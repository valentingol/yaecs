""" This file defines a library of convenient processing functions. """

import logging
import os
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from ..yaecs_utils import (Priority,
                           assign_order, assign_yaml_tag, compare_string_pattern, set_function_attribute)

if TYPE_CHECKING:
    from numbers import Number

    from .config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigProcessingFunctionsMixin:
    """ Pre- and Post-processing functions Mixin class for YAECS configurations. """

    get_main_config: Callable[[], 'Configuration']
    get_processed_param_name: Callable[[bool], str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ----- PRE-PROCESSING -----

    def check_param_in_list(self, list_of_choices: List[Any]) -> Callable:
        """
        Returns a pre-processing function that checks if a param value belongs to a list. Returned function has
        order OFTEN_FIRST (-10).
        For example in your pre-processing dict there could be a line such as this :
        "mode": self.check_param_in_list(["train", "val", "test", "infer"])

        :param list_of_choices: list of valid parameter values
        :return: checking function
        """

        def _check(param: Any, choices: List[Any], config: 'Configuration') -> Any:
            if param is None:
                return param
            if param.lower() not in choices:
                possibilities = ""
                for index, choice in range(len(choices)):
                    possibilities += f"'{choice}'"
                    if index != len(choices) - 1:
                        possibilities += ", "
                param_name = config.get_processed_param_name(full_path=True)
                raise ValueError(f"Invalid value for param '{param_name}': '{param}'."
                                 "Valid choices are [{possibilities}].")
            return param

        return_function = partial(_check, choices=list_of_choices, config=self)
        set_function_attribute(return_function, "__name__", "check_param_in_list")
        set_function_attribute(return_function, "order", Priority.OFTEN_FIRST)
        return return_function

    @assign_order(Priority.ALWAYS_LAST)  # there would most likely not be any other processing for this param
    @assign_yaml_tag("copy", "pre", "str")
    def copy_param(self, path_to_copy: str) -> str:
        """
        This pre-processing function declares a param as being an exact copy of another param. Its default value must
        be name of the param it copies. It will be protected against modifications by further config merges (only the
        param being copied can be modified), but can still pe post-processed further after its copy by post-processing
        functions with an order above OFTEN_LAST (10).
        Priority : ALWAYS_LAST (20)
        YAML tag : copy

        :param path_to_copy: path of param from which to copy the value
        :return: path_to_copy
        """

        def _copy(param: str, main: 'Configuration') -> Any:
            params = main.match_params(param)
            if len(params) == 1:
                return main[params[0]]
            if len(params) > 1:
                raise RuntimeError(f"Ambiguous replacement : param name '{param}' was matched to multiple "
                                   f"params : '{params}'.")
            return param

        if not isinstance(path_to_copy, str):
            raise TypeError(f"The default value of params declared as copies of other params must be the full path to "
                            f"the copied param. Current default value '{path_to_copy}' is not a string.")
        main = self.get_main_config()
        param_name = self.get_processed_param_name(full_path=True)
        copy_fn = partial(_copy, main=main)
        set_function_attribute(copy_fn, "__name__", "_copy")
        set_function_attribute(copy_fn, "order", Priority.OFTEN_LAST)

        current_processing = object.__getattribute__(main, "_added_post_processing")()
        if not any((compare_string_pattern(param_name, k) and v.__name__ == "_copy")
                   for k, v in current_processing.items()):
            main.add_processing_function_all(param_name, copy_fn, "post")
        elif self.get_variation_name() is None:
            YAECS_LOGGER.warning(f"WARNING : Parameter '{param_name}' was already declared as a copy of param "
                                 f"'{path_to_copy}'. Processing function will not be added again.")

        return self.protected_param(path_to_copy)

    def check_number_in_range(self, minimum: 'Number' = -float('inf'), maximum: 'Number' = float('inf')) -> Callable:
        """
        Returns a pre-processing function that checks if a numerical param value is in a range. Returned function has
        order OFTEN_FIRST (-10).
        For example in your pre-processing dict there could be a line such as this :
        "probability": self.number_in_range(minimum=0, maximum=1)

        :param minimum: minimal valid value for the parameter
        :param maximum: maximal valid value for the parameter
        :return: checking function
        """

        def _check(param: 'Number', minimum_: 'Number', maximum_: 'Number', config: 'Configuration') -> 'Number':
            if param is None:
                return param
            if not minimum_ <= param <= maximum_:
                param_name = config.get_processed_param_name(full_path=True)
                raise ValueError(f"Invalid value for param '{param_name}': '{param}'. "
                                 f"Must be in range [{minimum_} ; {maximum_}].")
            return param
        return_function = partial(_check, minimum_=minimum, maximum_=maximum, config=self)
        set_function_attribute(return_function, "__name__", "check_number_in_range")
        set_function_attribute(return_function, "order", Priority.OFTEN_FIRST)
        return return_function

    @assign_order(Priority.ALWAYS_LAST)  # there can never be any subsequent processing for this param
    @assign_yaml_tag("protected", "pre", "Any")
    def protected_param(self, param: Any) -> Any:
        """
        This pre-processing function declares a param as being protected against modifications. This means that only the
        default config can change its value, and any attempt to set it from another config will raise an error.
        Priority : ALWAYS_LAST (20)
        YAML tag : protected

        :param param: value of the param to protect
        :return: param
        """
        main = self.get_main_config()
        param_name = self.get_processed_param_name(full_path=True)
        prev = main.match_params(param_name)
        if prev:
            raise RuntimeError(f"Parameter '{param_name}' is protected, it cannot be set from configs other than the "
                               f"default config.")
        return param

    # ----- POST-PROCESSING -----

    @assign_order(Priority.OFTEN_LAST)  # should happen after register_as_experiment_path
    @assign_yaml_tag("sub_folder", "post", "Optional[str]")
    def folder_in_experiment(self, folder: Optional[str]) -> Optional[str]:
        """
        Returns a post-processing function that extends a path assuming it is located in the experiment path, then the
        corresponding folder is created. Requires an experiment_folder to have been declared.
        Priority : OFTEN_LAST (10)
        YAML tag : sub_folder

        :param folder: path of the subfolder within the experiment folder
        :return: checking function
        """
        experiment_path = self.get_main_config().get_experiment_path()
        path = os.path.join(experiment_path, folder).rstrip(os.path.sep)
        os.makedirs(path, exist_ok=True)
        return path

    def folder_in_experiment_if(self, condition_list: List[tuple] = None) -> Callable:
        """
        Returns a post-processing function that extends a path assuming it is located in the experiment path. Then, if
        the conditions listed in condition_list ar all met, the corresponding folder is created. Returned function has
        order OFTEN_LAST (10).
        condition_list is a list of conditions represented by tuples of length 2 or 3 :

        * when a condition is represented by a tuple of length 2, the first element should be the path to parameters in
          the main config and the second element should be a value for those parameters. The condition will return true
          if the corresponding parameters have the corresponding value ;
        * when a condition is represented by a tuple of length 3, the behaviour is the same except the third element is
          a function to apply to the parameters values before they are compared to the second element.
          For example in your post-processing dict there could be a line such as this :
          "save_weights_path": self.folder_in_experiment(condition_list=[("mode", "train")])

        :param condition_list: list of conditions to be met for the path to be created
        :return: checking function
        """

        def _folder_in_experiment(folder: str, config: 'Configuration', conditions: list) -> str:
            experiment_path = config.get_experiment_path()
            path = os.path.join(experiment_path, folder).rstrip(os.path.sep)
            conditions = {str(nb): [c for c in conditions if len(c) == nb] for nb in [2, 3]}
            if (all(all(c[2](config[i]) == c[1] for i in config.match_params(c[0])) for c in conditions["3"])
                    and all(all(config[i] == c[1] for i in config.match_params(c[0])) for c in conditions["2"])):
                os.makedirs(path, exist_ok=True)
            return path

        if condition_list is None:
            condition_list = []
        if not isinstance(condition_list, list):
            raise TypeError(f"Argument 'condition_list' of function 'folder_in_experiment' should be a list. "
                            f"Got {type(condition_list)}.")
        if not all(isinstance(c, tuple) for c in condition_list):
            raise TypeError("All elements of argument 'condition_list' of function 'folder_in_experiment' should be "
                            "tuples.")
        if not all(len(c) == 2 or len(c) == 3 for c in condition_list):
            raise ValueError("All elements of argument 'condition_list' of function 'folder_in_experiment' should have "
                             "2 elements (param and value) or 3 elements (param, value and conversion).")
        return_function = partial(_folder_in_experiment, config=self.get_main_config(), conditions=condition_list)
        set_function_attribute(return_function, "__name__", "folder_in_experiment_if")
        set_function_attribute(return_function, "order", Priority.OFTEN_LAST)
        return return_function
