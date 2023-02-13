"""
Reactive Reality Machine Learning Config System - ConfigHooksMixin object
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
import os
from typing import Any, Callable, List, Optional, Tuple, Union

from ..yaecs_utils import ConfigDeclarator, hook, Hooks, VariationDeclarator

YAECS_LOGGER = logging.getLogger(__name__)


class ConfigHooksMixin:
    """ Hooks Mixin class for YAECS configurations. Implements processing functions whose name start with "register_as_"
    and are decorated by the yaecs_utils.hook decorator. Users can use those processing either as pre- or
    post-processing functions, which will have the added effect of tagging the processed parameters as playing a certain
    pre-defined role in the config """

    __getattribute__: Callable[[str], Any]
    get_variation_name: Callable[[], str]
    init_from_config: Callable[[ConfigDeclarator], None]
    _configuration_variations: List[Tuple[str, List[ConfigDeclarator]]]
    _configuration_variations_names: List[Tuple[str, List[str]]]
    _get_processed_param_name: Callable[[], str]
    _grids: List[List[str]]
    _nesting_hierarchy: List[str]

    def __init__(self):
        self._hooks = {}

    def add_currently_processed_param_as_hook(self, hook_name: str) -> None:
        """
        Used within _ConfigurationBase._process_parameter to add the param currently being processed as a hook with
        given name. Instead of using this directly, users should consider decorating their hooking function with the
        yaecs_utils.hook decorator.
        :param hook_name: name of the hook to add.
        :return: None
        """
        name = self._get_processed_param_name()
        parameter = ".".join(self._nesting_hierarchy + [name])
        if hook_name not in self.get_hook():
            self._hooks[hook_name] = []
        if parameter not in self._hooks[hook_name]:
            self._hooks[hook_name].append(parameter)

    def get_experiment_path(self) -> str:
        """
        Returns the value of the parameter registered as the experiment path.
        :raises RuntimeError: when no experiment path has been registered in the config
        :raises RuntimeError: when more than one experiment path has been registered in the config
        :return: experiment path
        """
        path = self.get_hook("experiment_path")
        if not path:
            raise RuntimeError("No experiment path was registered. Please use self.register_as_experiment_path as a "
                               "post-processing on a parameter.")
        if len(path) > 1:
            raise RuntimeError("The self.register_as_experiment_path post-processing was used on more than one "
                               f"parameter : {path}.")
        return self[path[0]]

    def get_hook(self, hook_name: Optional[str] = None) -> Hooks:
        """
        Returns the parameters registered with given hook.
        :param hook_name: name of the hook, or None to get the dict of all hooked parameters
        :return: list of hooked parameter names
        """
        if hook_name is None:
            return self._hooks
        return self._hooks[hook_name] if hook_name in self._hooks else []

    @hook("additional_config_file")
    def register_as_additional_config_file(self, path: Union[str, List[str]]) -> Union[str, List[str]]:
        """
        Pre-processing function used to register the corresponding parameter as a path to another config file. The new
        config file will then also be used to build the config currently being built.
        :param path: config's path or list of paths
        :return: the same path as the input once the parameters from the new config have been added
        """
        if isinstance(path, list):
            for individual_path in path:
                self.init_from_config(individual_path)
        else:
            self.init_from_config(path)
        return path

    @hook("config_variations")
    def register_as_config_variations(
            self, variation_to_register: Optional[VariationDeclarator]) -> Optional[VariationDeclarator]:
        """
        Pre-processing function used to register the corresponding parameter as a variation for the current config.
        Please note that config variations need to be declared in the root config.
        :param variation_to_register: list of configs
        :return: the same list of configs once the configs have been added to the internal variation tracker
        :raises RuntimeError: register_as_config_variations is called outside _pre_process_parameter
        :raises RuntimeError: variation name invalid in sub-config
        :raises TypeError: type of variation is not list or dict of configs
        """
        name = self._get_processed_param_name()

        def _is_single_var(single):
            return isinstance(single, (str, dict))

        def _add_to_variations(variations, names=None):
            if variations:
                for index, variation in enumerate(self._configuration_variations):
                    if variation[0] == name:
                        self._configuration_variations.pop(index)
                        break
                self._configuration_variations.append((name, variations))
                if names is None:
                    self._configuration_variations_names.append((name, [str(i) for i in list(range(len(variations)))],))
                else:
                    self._configuration_variations_names.append((name, names))

        if self._nesting_hierarchy:
            raise RuntimeError(f"Variations declared in sub-configs are invalid ({name}).\n"
                               "Please declare all your variations in the main config.")
        if (isinstance(variation_to_register, dict)
                and all(_is_single_var(potential_single) for potential_single in variation_to_register.values())):
            _add_to_variations(list(variation_to_register.values()), names=list(variation_to_register.keys()),)
        elif (isinstance(variation_to_register, list)
              and all(_is_single_var(potential_single) for potential_single in variation_to_register)):
            _add_to_variations(variation_to_register)
        elif variation_to_register is not None:
            raise TypeError("Variations parsing failed : variations parameters must "
                            "be a list of configs or a dict containing only configs. "
                            f"Instead, got : {variation_to_register}")

        return variation_to_register

    @hook("experiment_path")
    def register_as_experiment_path(self, path: str) -> str:
        """
        Pre-processing function used to register the corresponding parameter as the folder used for the current
        experiment. This will automatically create the relevant folder structure and append an experiment index at the
        end of the folder name to avoid any overwriting. The path needs to be either None or an empty string (in which
        case the pre-processing does not happen), or an absolute path, or a path relative to the current working
        directory.
        :param path: None, '', absolute path or path relative to the current working directory
        :return: the actual created path with its appended index
        """
        if not path:
            return path
        folder, experiment = (os.path.dirname(path), os.path.basename(path))
        if not folder:
            folder = "."
        os.makedirs(folder, exist_ok=True)
        experiments = [i for i in os.listdir(folder) if i.startswith(experiment)]
        run_ids = [-1]
        for exp_name in experiments:
            try:
                run_ids.append(int(exp_name.split("_")[-1]))
            except ValueError:
                pass
        new_folder = not os.getenv('PICKUP') and not os.getenv('NODE_RANK')
        if self.get_variation_name() is None:
            path = os.path.join(folder, f"{experiment}_{max(run_ids) + int(new_folder)}")
        else:
            path = os.path.join(folder, f"{experiment}_{max(run_ids)}", self.get_variation_name())
        if new_folder:
            os.makedirs(path, exist_ok=True)
        return path

    @hook("grid")
    def register_as_grid(self, list_to_register: Optional[List[str]]) -> Optional[List[str]]:
        """
        Pre-processing function used to register the corresponding parameter as a grid for the current config. Grids are
        made of several parameters registered as variations. Instead of adding the variations in those parameters to the
        list of variations for this config, a grid will be created and all its components will be added instead.
        :param list_to_register: list of parameters composing the grid
        :raises TypeError: list_to_register is not recognised as a valid grid
        :return: the same list of parameters once the grid has been added to the internal grid tracker
        """
        if isinstance(list_to_register, list) and all(isinstance(param, str) for param in list_to_register):
            self._grids.append(list_to_register)
        elif list_to_register is not None:
            raise TypeError("Grid parsing failed : unrecognised grid declaration : "
                            f"{list_to_register}")
        return list_to_register

    @hook("tracker_config")
    def register_as_tracker_config(self, tracker_config: dict) -> dict:  # pylint: disable=no-self-use
        """
        Pre-processing function used to register the corresponding parameter as the tracker config. The tracker config
        is a dict that contains at least one key : 'type'. Valid types are given by the 'ACCEPTED_TRACKERS' variable in
        experiment.py and refer to the type of tracker used. Other keys in the dict depend on the parameters required by
        corresponding tracker type.
        :param tracker_config: dict corresponding to the tracker config
        :raises: ValueError: if the tracker config is not a dict or does not contain at least a parameter called 'type'
        which is a string
        :raises: ValueError: if the 'type' is not recognised
        :raises: ValueError: if there are missing required keys for this 'type'
        :return: the same dict
        """
        if os.getenv('NODE_RANK'):  # do not track if in a pytorch-lightning spawned process
            return {"type": []}
        required_keys = {
            "basic": [],
            "sacred": ["db_url", "db_name"],
            "mlflow": ["tracking_uri"],
            "tensorboard": ["logdir"],
            "clearml": ["project_name"],
        }
        possible_keys = list(required_keys.values()) + [["basic_logdir", "sub_loggers", "type"]]
        if not isinstance(tracker_config, dict):
            raise ValueError(f"{tracker_config} is not a valid tracker config : it is not a dict.")
        if "type" not in tracker_config:
            raise ValueError(f"{tracker_config} is not a valid tracker config : it has no 'type' key.")
        if tracker_config["type"] is not None and not isinstance(tracker_config["type"], str) and not (
                isinstance(tracker_config["type"], list) and all(isinstance(i, str) for i in tracker_config["type"])):
            raise ValueError(f"{tracker_config} is not a valid tracker config : 'type' should be None, a string or a"
                             " list of strings.")
        if isinstance(tracker_config["type"], str):
            tracker_list = [t.strip(" ") for t in tracker_config["type"].split(",")]
        elif tracker_config["type"] is not None:
            tracker_list = []
            for string in tracker_config["type"]:
                tracker_list += [t.strip(" ") for t in string.split(",")]
        else:
            tracker_list = []
        if any(tracker not in required_keys for tracker in tracker_list):
            raise ValueError(f"Unknown tracker among {tracker_list}. "
                             f"Accepted values are {list(required_keys.keys())}.")
        for tracker in tracker_list:
            for key in required_keys[tracker]:
                if key not in tracker_config:
                    raise ValueError(f"Missing key in {tracker}-type tracker config : '{key}'.")
        for key in tracker_config:
            if not any(key in key_list for key_list in possible_keys):
                YAECS_LOGGER.warning(f"WARNING : Unknown key '{key}' in tracker config. It might be ignored.")
        tracker_config["type"] = tracker_list
        return tracker_config
